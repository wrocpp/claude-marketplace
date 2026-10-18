import json
import pathlib
import subprocess
import sys
import tempfile
import unittest

PLUGIN = pathlib.Path(__file__).resolve().parents[1]
SCRIPTS = PLUGIN / "scripts"
sys.path.insert(0, str(SCRIPTS))
import cpp26_lint
import lint_common
import reflection_lint
from lint_common import Config

HAND_SWITCH = reflection_lint.FIXTURES["enum-name-switch"]
LEGACY = cpp26_lint.FIXTURES["legacy-io"]


def project(files, config=None):
    directory = tempfile.TemporaryDirectory()
    root = pathlib.Path(directory.name)
    for name, text in files.items():
        target = root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text)
    if config is not None:
        (root / ".claude").mkdir(exist_ok=True)
        (root / ".claude/cpp26-guard.json").write_text(json.dumps(config))
    return directory, root


def cli(script, root, *args):
    done = subprocess.run([sys.executable, str(SCRIPTS / script), "--root", str(root), *args], capture_output=True, text=True)
    return done.returncode, done.stdout


class SelfTest(unittest.TestCase):
    def test_the_reflection_lint_self_test_passes(self):
        self.assertEqual(reflection_lint.self_test(), 0)

    def test_the_cpp26_lint_self_test_passes(self):
        self.assertEqual(cpp26_lint.self_test(), 0)

    def test_every_rule_has_advice_and_a_fixture(self):
        for rule in reflection_lint.OWN_RULES | cpp26_lint.OWN_RULES | {lint_common.STALE}:
            self.assertIn(rule, lint_common.ADVICE)
        fixtures = set(reflection_lint.FIXTURES) | set(cpp26_lint.FIXTURES) | {"enum-word-list"}
        self.assertEqual(fixtures, reflection_lint.OWN_RULES | cpp26_lint.OWN_RULES)

    def test_the_command_line_self_tests_exit_zero(self):
        for script in ("reflection_lint.py", "cpp26_lint.py"):
            code, out = cli(script, ".", "--self-test")
            self.assertEqual((code, out.strip().endswith("ok")), (0, True), script)


class ConfigTest(unittest.TestCase):
    def test_defaults_when_the_file_is_absent(self):
        directory, root = project({})
        with directory:
            config = lint_common.load_config(root)
        self.assertEqual(config, Config())
        self.assertFalse(config.enabled("comment"))
        self.assertFalse(config.enabled("std-include"))
        self.assertTrue(config.enabled("enum-name-switch"))

    def test_modules_turn_the_std_include_rule_on(self):
        directory, root = project({}, {"modules": True})
        with directory:
            self.assertTrue(lint_common.load_config(root).enabled("std-include"))

    def test_an_explicit_rule_entry_beats_the_default(self):
        directory, root = project({}, {"modules": True, "rules": {"std-include": False, "comment": True}})
        with directory:
            config = lint_common.load_config(root)
        self.assertFalse(config.enabled("std-include"))
        self.assertTrue(config.enabled("comment"))

    def test_a_helper_name_replaces_the_default_advice(self):
        finding = reflection_lint.scan_text("a.cpp", HAND_SWITCH, Config(helpers=(("enum_name", "reflect::enum_name"),)))[0]
        self.assertIn("reflect::enum_name", finding.render(Config(helpers=(("enum_name", "reflect::enum_name"),))))
        self.assertIn("std::meta::enumerators_of", finding.render())

    def test_a_malformed_config_is_an_error(self):
        for bad in ({"roots": "src"}, {"rules": {"comment": "yes"}}, {"helpers": ["x"]}):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    lint_common.parse_config(bad)

    def test_an_unknown_helper_is_ignored_and_flagged(self):
        config = lint_common.parse_config({"helpers": {"nonsense": "x"}})
        self.assertEqual((config.helpers, config.ignored), ((), True))

    def test_roots_exclude_and_suffixes_decide_what_is_covered(self):
        config = Config(roots=("lib",), exclude=("lib/gen/",))
        self.assertTrue(config.covers("lib/a.cpp"))
        self.assertFalse(config.covers("lib/gen/a.cpp"))
        self.assertFalse(config.covers("src/a.cpp"))
        self.assertFalse(config.covers("lib/a.txt"))
        self.assertFalse(config.covers("library/a.cpp"))


class AllowanceTest(unittest.TestCase):
    def scan(self, files, allow, config=None):
        directory, root = project({**files, ".claude/cpp26-guard-allow.txt": allow}, config)
        with directory:
            cfg = lint_common.load_config(root)
            return cpp26_lint.scan_paths(root, ["src"], cfg), lint_common.project_allowances(root, cfg)

    def test_an_allowance_silences_its_finding(self):
        found, _ = self.scan({"src/a.cpp": LEGACY}, "src/a.cpp|legacy-io|std::cout|wire log stays\n")
        self.assertEqual(found, [])

    def test_a_directory_allowance_covers_the_files_below(self):
        found, _ = self.scan({"src/gen/a.cpp": LEGACY}, "src/gen/|legacy-io|std::cout|generated\n")
        self.assertEqual(found, [])

    def test_a_stale_allowance_is_reported(self):
        found, _ = self.scan({"src/a.cpp": "int a;\n"}, "src/a.cpp|legacy-io|std::cout|pending: tier 9\n")
        self.assertEqual([f.rule for f in found], [lint_common.STALE])

    def test_an_allowance_for_a_deleted_file_is_stale(self):
        found, _ = self.scan({"src/a.cpp": "int a;\n"}, "src/gone.cpp|legacy-io|std::cout|pending: tier 9\n")
        self.assertEqual([f.rule for f in found], [lint_common.STALE])

    def test_an_allowance_outside_the_scanned_paths_is_not_judged(self):
        directory, root = project({"src/a.cpp": "int a;\n", "app/b.cpp": LEGACY, ".claude/cpp26-guard-allow.txt": "app/b.cpp|legacy-io|std::cout|ok\n"})
        with directory:
            self.assertEqual(cpp26_lint.scan_paths(root, ["src"], Config()), [])

    def test_a_disabled_rule_does_not_make_its_allowance_stale(self):
        found, _ = self.scan({"src/a.cpp": "int a;\n"}, "src/a.cpp|legacy-io|std::cout|ok\n", {"rules": {"legacy-io": False}})
        self.assertEqual(found, [])

    def test_a_line_without_a_reason_is_refused(self):
        with self.assertRaises(SystemExit):
            self.scan({"src/a.cpp": LEGACY}, "src/a.cpp|legacy-io|std::cout\n")

    def test_debt_is_counted_by_kind(self):
        _, allowances = self.scan({"src/a.cpp": LEGACY}, "# note\nsrc/a.cpp|legacy-io|std::cout|pending: tier 2\nsrc/b.cpp|comment|x|wire name\n")
        self.assertEqual(lint_common.debt_counts(allowances), {"pending:": 1, "exception": 1})


class CommandLineTest(unittest.TestCase):
    def test_strict_fails_on_a_finding_and_plain_does_not(self):
        directory, root = project({"src/a.cpp": HAND_SWITCH})
        with directory:
            plain = cli("reflection_lint.py", root)
            strict = cli("reflection_lint.py", root, "--strict")
        self.assertEqual(plain[0], 0)
        self.assertEqual(strict[0], 1)
        self.assertIn("src/a.cpp:", plain[1])
        self.assertIn("[enum-name-switch]", plain[1])
        self.assertIn("allowances: 0 exceptions, 0 pending", plain[1])

    def test_a_clean_tree_passes_strict(self):
        directory, root = project({"src/a.cpp": "int a;\n"})
        with directory:
            self.assertEqual(cli("cpp26_lint.py", root, "--strict")[0], 0)

    def test_explicit_paths_limit_the_scan(self):
        directory, root = project({"src/a.cpp": HAND_SWITCH, "src/b.cpp": "int b;\n"})
        with directory:
            self.assertEqual(cli("reflection_lint.py", root, "--strict", "src/b.cpp")[0], 0)

    def test_the_enum_word_list_needs_the_enum_somewhere_in_the_scan(self):
        files = {"src/e.hpp": reflection_lint.ENUM_SOURCE, "src/a.cpp": reflection_lint.WORD_LIST}
        directory, root = project(files)
        with directory:
            code, out = cli("reflection_lint.py", root, "--strict")
        self.assertEqual(code, 1)
        self.assertIn("[enum-word-list]", out)


if __name__ == "__main__":
    unittest.main()
