import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest

PLUGIN = pathlib.Path(__file__).resolve().parents[1]
SCRIPTS = PLUGIN / "scripts"
sys.path.insert(0, str(SCRIPTS))
import lint_common

HAND_SWITCH = 'constexpr auto f(E e) {\n  switch (e) {\n    case E::a: return "a";\n    case E::b: return "b";\n    case E::c: return "c";\n  }\n}\n'
UNREADABLE = "The project config .claude/cpp26-guard.json could not be read; defaults are used."
BROKEN_FILES = ("{not json", "", "[1, 2]", "5", "null", '"text"', "\xff\xfe", "[" * 100000, b"\xff\xfe\x00")


class Project:
    def __init__(self, config_text=None):
        self.root = pathlib.Path(tempfile.mkdtemp()).resolve()
        (self.root / "src").mkdir()
        (self.root / "src/probe.cpp").write_text(HAND_SWITCH)
        if config_text is not None:
            (self.root / ".claude").mkdir()
            (self.root / ".claude/cpp26-guard.json").write_bytes(config_text.encode("utf-8", "surrogateescape") if isinstance(config_text, str) else config_text)

    def hook(self, script):
        payload = {"cwd": str(self.root), "tool_input": {"file_path": str(self.root / "src/probe.cpp"), "content": HAND_SWITCH}}
        env = {k: v for k, v in os.environ.items() if k != "CLAUDE_PROJECT_DIR"}
        done = subprocess.run([sys.executable, str(SCRIPTS / script)], input=json.dumps(payload), capture_output=True, text=True, env=env)
        context = json.loads(done.stdout)["hookSpecificOutput"]["additionalContext"] if done.stdout else ""
        return done.returncode, context, done.stdout

    def cli(self, script, *args):
        done = subprocess.run([sys.executable, str(SCRIPTS / script), "--root", str(self.root), *args], capture_output=True, text=True)
        return done.returncode, done.stdout


class ConfigTestCase(unittest.TestCase):
    def project(self, config_text=None):
        made = Project(config_text)
        self.addCleanup(shutil.rmtree, made.root, True)
        return made


class UnreadableConfigTest(ConfigTestCase):
    def test_an_unreadable_config_still_scans_with_defaults_and_says_so_once(self):
        for text in BROKEN_FILES:
            for script in ("precheck.py", "postcheck.py"):
                with self.subTest(text=text[:12], script=script):
                    code, context, raw = self.project(text).hook(script)
                    self.assertEqual(code, 0)
                    self.assertIn("enum-name-switch", context)
                    self.assertEqual(context.count(UNREADABLE), 1)
                    self.assertNotIn("Expecting", raw)
                    self.assertNotIn("not json", raw)

    def test_a_config_that_is_a_directory_is_unreadable_not_fatal(self):
        made = self.project()
        (made.root / ".claude/cpp26-guard.json").mkdir(parents=True)
        self.assertEqual(lint_common.load_config(made.root).ignored, ())

    def test_the_cli_prints_the_same_notice_and_still_scans(self):
        code, out = self.project("{not json").cli("reflection_lint.py", "--strict")
        self.assertEqual(code, 1)
        self.assertIn(UNREADABLE, out)
        self.assertIn("[enum-name-switch]", out)

    def test_load_config_returns_defaults_flagged_config(self):
        config = lint_common.load_config(self.project("[1]").root)
        self.assertEqual(config.ignored, ("config",))
        self.assertEqual(config.roots, lint_common.DEFAULT_ROOTS)


class WrongTypedValueTest(ConfigTestCase):
    CASES = {
        "roots": 5,
        "exclude": "src/gen",
        "suffixes": [1],
        "modules": "yes",
        "allowance_file": 7,
        "rules": {"comment": "yes"},
        "helpers": ["x"],
    }

    def test_each_wrong_typed_key_is_ignored_and_named(self):
        for key, value in self.CASES.items():
            with self.subTest(key=key):
                config = lint_common.parse_config({key: value})
                self.assertEqual(config.ignored, (key,))
                self.assertEqual(config, lint_common.Config(ignored=(key,)))

    def test_the_notice_names_the_keys_and_not_the_values(self):
        raw = {"roots": 5, "rules": {"comment": "SECRET-VALUE"}, "modules": True}
        config = lint_common.parse_config(raw)
        self.assertEqual(lint_common.ignored_notice(config), "A config value was ignored (roots, rules); the default is used.")
        self.assertTrue(config.modules)

    def test_good_keys_survive_a_bad_neighbour(self):
        config = lint_common.parse_config({"roots": 5, "exclude": ["gen/"], "helpers": {"enum_name": "ns::name", "enum_count": "a b"}})
        self.assertEqual(config.exclude, ("gen/",))
        self.assertEqual(config.helpers, (("enum_name", "ns::name"),))
        self.assertEqual(config.ignored, ("roots", "helpers"))

    def test_the_hook_continues_and_reports_the_key_only(self):
        made = self.project(json.dumps({"roots": 5, "modules": "SECRET-VALUE"}))
        code, context, raw = made.hook("postcheck.py")
        self.assertEqual(code, 0)
        self.assertIn("enum-name-switch", context)
        self.assertIn("A config value was ignored (roots, modules)", context)
        self.assertNotIn("SECRET-VALUE", raw)

    def test_unknown_keys_are_ignored_silently(self):
        config = lint_common.parse_config({"nonsense": 1})
        self.assertEqual(config, lint_common.Config())


class RootsMatchingNothingTest(ConfigTestCase):
    def test_roots_that_match_no_file_mean_silence(self):
        made = self.project(json.dumps({"roots": ["lib"]}))
        self.assertEqual(made.hook("postcheck.py"), (0, "", ""))
        code, out = made.cli("reflection_lint.py", "--strict")
        self.assertEqual(code, 0)
        self.assertIn("0 hand-written mirrors", out)

    def test_an_empty_root_list_turns_the_scan_off(self):
        made = self.project(json.dumps({"roots": []}))
        self.assertEqual(made.hook("precheck.py"), (0, "", ""))


if __name__ == "__main__":
    unittest.main()
