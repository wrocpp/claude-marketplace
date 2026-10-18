#!/usr/bin/env python3
"""Confirm a C++ rule against cppreference.com and print the page and anchor to cite.

  cppreference.py topics [WORD]                    list the built-in topic index
  cppreference.py lookup TOPIC [--grep RE] [--section NAME] [--max-matches N] [--json]
                                                   TOPIC is an index word, a path like cpp/container/span,
                                                   or a cppreference.com URL

Pages are cached under $WROCPP_CACHE_DIR (default ~/.cache/wrocpp/cppreference). The network is
used only for a page that is not cached, and never with --offline or WROCPP_OFFLINE=1.
Exit status: 0 matches found, 1 page loaded but nothing matched, 2 page unavailable.
The printed excerpts are cut short on purpose: cite the page, then write the rule in your words.
"""
import argparse
import html.parser
import json
import os
import pathlib
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

BASE_URL = "https://en.cppreference.com/"
USER_AGENT = "wrocpp-cpp-conventions/0.1 (+https://github.com/wrocpp/claude-marketplace)"
FETCH_TIMEOUT_SECONDS = 20
EXCERPT_CHARS = 120
ALLOWED_HOSTS = ('en.cppreference.com',)
SEGMENT = re.compile(r"[A-Za-z0-9_+:-][A-Za-z0-9_.+:-]*")
SECTION_ID = re.compile(r"[A-Za-z0-9_.:-]{1,64}")
MAX_ARGUMENT_CHARS = 200
DEFAULT_MAX_MATCHES = 6
MAX_MATCHES_CAP = 25
MAX_PAGE_BYTES = 8 * 1024 * 1024
HEADING_TAGS = {"h1", "h2", "h3", "h4", "h5"}
TEXT_TAGS = {"p", "li", "tr", "pre", "dd", "dt"}
SKIPPED_TAGS = {"script", "style", "nav", "head"}
ANCHOR_ID = re.compile(r"[A-Z][A-Za-z0-9_]*")

TOPICS = {
    "aggregate initialization": "cpp/language/aggregate_initialization",
    "designated initializer": "cpp/language/aggregate_initialization",
    "list initialization": "cpp/language/list_initialization",
    "initialization": "cpp/language/initialization",
    "constructor": "cpp/language/constructor",
    "string_view": "cpp/string/basic_string_view",
    "basic_string": "cpp/string/basic_string",
    "span": "cpp/container/span",
    "vector": "cpp/container/vector",
    "borrowed_range": "cpp/ranges/borrowed_range",
    "ranges::to": "cpp/ranges/to",
    "range-for": "cpp/language/range-for",
    "copy elision": "cpp/language/copy_elision",
    "std::move": "cpp/utility/move",
    "value category": "cpp/language/value_category",
    "lifetime": "cpp/language/lifetime",
    "reference initialization": "cpp/language/reference_initialization",
    "storage duration": "cpp/language/storage_duration",
    "shared_ptr": "cpp/memory/shared_ptr",
    "move_only_function": "cpp/utility/functional/move_only_function",
    "function_ref": "cpp/utility/functional/function_ref",
    "lambda": "cpp/language/lambda",
    "thread": "cpp/thread/thread",
    "jthread": "cpp/thread/jthread",
    "async": "cpp/thread/async",
    "feature test": "cpp/feature_test",
    "optional": "cpp/utility/optional",
    "variant": "cpp/utility/variant",
    "constexpr": "cpp/language/constexpr",
    "static_assert": "cpp/language/static_assert",
    "enum": "cpp/language/enum",
    "default arguments": "cpp/language/default_arguments",
    "duration": "cpp/chrono/duration",
    "time_point": "cpp/chrono/time_point",
    "system_clock": "cpp/chrono/system_clock",
    "steady_clock": "cpp/chrono/steady_clock",
    "fundamental types": "cpp/language/types",
    "arithmetic operators": "cpp/language/operator_arithmetic",
}


class Page(html.parser.HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.sections = []
        self.blocks = []
        self._skip = 0
        self._heading = None
        self._heading_id = None
        self._buffer = None
        self._current = ""

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if tag in SKIPPED_TAGS:
            self._skip += 1
        if self._skip:
            return
        if tag in HEADING_TAGS:
            self._heading = []
        if self._heading is not None and attributes.get("id"):
            self._heading_id = attributes["id"]
        elif attributes.get("id") and ANCHOR_ID.fullmatch(attributes["id"]):
            self._add_anchor(attributes["id"], attributes["id"].replace("_", " "))
        if tag in TEXT_TAGS and self._buffer is None:
            self._buffer = []

    def handle_endtag(self, tag):
        if tag in SKIPPED_TAGS and self._skip:
            self._skip -= 1
            return
        if self._skip:
            return
        if tag in HEADING_TAGS and self._heading is not None:
            title = " ".join("".join(self._heading).split())
            if title and self._heading_id:
                self._add_anchor(self._heading_id, title)
            self._heading, self._heading_id = None, None
        if tag in TEXT_TAGS and self._buffer is not None:
            text = " ".join("".join(self._buffer).split())
            if text:
                self.blocks.append({"section": self._current, "text": text})
            self._buffer = None

    def _add_anchor(self, anchor, title):
        if not SECTION_ID.fullmatch(anchor):
            return
        self._current = anchor
        if not any(known["id"] == anchor for known in self.sections):
            self.sections.append({"id": anchor, "title": title})

    def handle_data(self, data):
        if self._skip:
            return
        if self._heading is not None:
            self._heading.append(data)
        if self._buffer is not None:
            self._buffer.append(data)


def cache_dir():
    explicit = os.environ.get("WROCPP_CACHE_DIR")
    if explicit:
        return pathlib.Path(explicit)
    base = os.environ.get("XDG_CACHE_HOME") or str(pathlib.Path.home() / ".cache")
    return pathlib.Path(base) / "wrocpp" / "cppreference"


def normalise_path(topic):
    """Turn a topic word, path or URL into a cppreference page path, or None when it is not acceptable."""
    if not topic or topic.startswith("-") or len(topic) > MAX_ARGUMENT_CHARS or any(not c.isprintable() for c in topic):
        return None
    key = " ".join(topic.lower().replace("_", " ").split())
    for name, path in TOPICS.items():
        if key == " ".join(name.lower().replace("_", " ").split()):
            return path
    parsed = urllib.parse.urlparse(topic)
    if parsed.scheme:
        if parsed.scheme != "https" or parsed.hostname not in ALLOWED_HOSTS or parsed.username or parsed.password:
            return None
        path = parsed.path
    else:
        path = topic
    path = re.sub(r"\.html$", "", path.strip("/"))
    if path.startswith("w/"):
        path = path[2:]
    parts = path.split("/")
    if len(parts) < 2 or parts[0] not in ("cpp", "c") or not all(SEGMENT.fullmatch(p) and p not in (".", "..") and ".." not in p for p in parts):
        return None
    return path


def cache_file(path):
    directory = cache_dir().resolve()
    target = (directory / (path.replace("/", "__") + ".html")).resolve()
    if target.parent != directory:
        raise ValueError("cache path escapes the cache directory")
    return target


def load(path, offline, refresh):
    try:
        cached = cache_file(path)
    except ValueError:
        return None, "cache path rejected"
    if cached.is_file() and not refresh:
        return cached.read_text(encoding="utf-8", errors="replace"), "cache"
    if offline:
        return None, "offline: not in the cache"
    request = urllib.request.Request(BASE_URL + path, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=FETCH_TIMEOUT_SECONDS) as response:
            if urllib.parse.urlparse(response.geturl()).hostname not in ALLOWED_HOSTS:
                return None, "network: redirected to a host that is not allowed"
            body = response.read(MAX_PAGE_BYTES + 1).decode("utf-8", errors="replace")
    except (urllib.error.URLError, OSError, ValueError):
        return None, "network: the request failed"
    if len(body) > MAX_PAGE_BYTES:
        return None, "network: the page is larger than expected"
    cached.parent.mkdir(parents=True, exist_ok=True)
    cached.write_text(body, encoding="utf-8")
    return body, "network"


def anchor_for(page, section_query):
    wanted = re.sub(r"\W+", "", section_query).lower()
    for section in page.sections:
        if wanted in (re.sub(r"\W+", "", section["id"]).lower(), re.sub(r"\W+", "", section["title"]).lower()):
            return section
    for section in page.sections:
        if wanted and wanted in re.sub(r"\W+", "", section["title"]).lower():
            return section
    return None


def select(page, grep, section, limit):
    blocks = page.blocks
    if section is not None:
        blocks = [b for b in blocks if b["section"] == section["id"]]
    if grep:
        pattern = re.compile(grep, re.IGNORECASE)
        blocks = [b for b in blocks if pattern.search(b["text"])]
    return blocks[:limit]


def clean_excerpt(text):
    flat = "".join(c if c.isprintable() else " " for c in text)
    return " ".join(flat.split())[:EXCERPT_CHARS]


def cmd_topics(args):
    word = (args.word or "").lower()
    for name, path in sorted(TOPICS.items()):
        if word in name.lower() or word in path:
            print(f"{name:26} {BASE_URL}{path}")
    return 0


def cmd_lookup(args):
    path = normalise_path(args.topic)
    if path is None:
        print(f"unacceptable topic: run `topics`, or pass a path such as cpp/container/span (https://en.cppreference.com URLs are accepted, other hosts are not)", file=sys.stderr)
        return 2
    offline = args.offline or os.environ.get("WROCPP_OFFLINE") == "1"
    body, origin = load(path, offline, args.refresh)
    if body is None:
        print(f"{BASE_URL}{path}: unavailable ({origin})", file=sys.stderr)
        return 2
    page = Page()
    page.feed(body)
    section = None
    if args.section:
        section = anchor_for(page, args.section)
        if section is None:
            known = ", ".join(s["id"] for s in page.sections) or "none"
            print(f"no section with that name on {BASE_URL}{path}; sections: {known}", file=sys.stderr)
            return 1
    try:
        matches = select(page, args.grep, section, max(1, min(args.max_matches, MAX_MATCHES_CAP)))
    except re.error:
        print("the --grep pattern is not a valid regular expression", file=sys.stderr)
        return 2
    result = {
        "page": BASE_URL + path,
        "source": origin,
        "sections": page.sections,
        "matches": [
            {"cite": f"{BASE_URL}{path}#{b['section']}" if b["section"] else BASE_URL + path, "section": b["section"], "text": clean_excerpt(b["text"])}
            for b in matches
        ],
    }
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"page: {result['page']} ({origin})")
        print("sections: " + ", ".join(s["id"] for s in page.sections))
        for match in result["matches"]:
            print(f'cite: {match["cite"]}\n  quoted data: "{match["text"]}"')
    return 0 if matches else 1


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    topics = sub.add_parser("topics")
    topics.add_argument("word", nargs="?")
    topics.set_defaults(run=cmd_topics)
    lookup = sub.add_parser("lookup")
    lookup.add_argument("topic")
    lookup.add_argument("--grep", help="regular expression to find in the page text")
    lookup.add_argument("--section", help="section title or anchor id")
    lookup.add_argument("--max-matches", type=int, default=DEFAULT_MAX_MATCHES)
    lookup.add_argument("--offline", action="store_true")
    lookup.add_argument("--refresh", action="store_true", help="fetch again even when cached")
    lookup.add_argument("--json", action="store_true")
    lookup.set_defaults(run=cmd_lookup)
    args = parser.parse_args(argv)
    return args.run(args)


if __name__ == "__main__":
    sys.exit(main())
