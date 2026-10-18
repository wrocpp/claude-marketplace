import pathlib
import re
import subprocess
import sys
import unittest

TESTS = pathlib.Path(__file__).resolve().parent
SCRIPTS = TESTS.parent / "scripts"
FIXTURES = TESTS / "fixtures"
REFERENCES = TESTS.parent / "skills" / "reflect-dont-hand-write" / "references"
RULE_TAG = re.compile(r"\[([a-z-]+)\]")
DIRTY_RULES = {
    "mirrors": {"enum-name-switch", "name-enum-table", "word-chain", "key-member-block", "enum-modulo", "stale-allowance"},
    "idioms": {"unconstrained-template", "std-include", "legacy-io", "append-chain", "string-temporary", "comment"},
}


def lint(script, root, *args):
    done = subprocess.run([sys.executable, str(SCRIPTS / script), "--root", str(root), *args], capture_output=True, text=True)
    return done.returncode, done.stdout


def rules_in(output):
    return set(RULE_TAG.findall(output))


class CleanFixtureTest(unittest.TestCase):
    def test_both_lints_pass_strict_on_the_clean_project(self):
        for script in ("reflection_lint.py", "cpp26_lint.py"):
            code, out = lint(script, FIXTURES / "clean", "--strict")
            self.assertEqual(code, 0, out)
            self.assertIn("allowances: 1 exceptions, 1 pending", out)

    def test_the_reference_implementation_is_clean_under_both_lints(self):
        for script in ("reflection_lint.py", "cpp26_lint.py"):
            code, out = lint(script, REFERENCES, "--strict", ".")
            self.assertEqual(code, 0, out)


class DirtyFixtureTest(unittest.TestCase):
    def test_the_reflection_lint_reports_exactly_the_mirror_rules(self):
        code, out = lint("reflection_lint.py", FIXTURES / "dirty", "--strict")
        self.assertEqual(code, 1)
        self.assertEqual(rules_in(out), DIRTY_RULES["mirrors"])

    def test_the_idiom_lint_reports_exactly_the_idiom_rules(self):
        code, out = lint("cpp26_lint.py", FIXTURES / "dirty", "--strict")
        self.assertEqual(code, 1)
        self.assertEqual(rules_in(out), DIRTY_RULES["idioms"])

    def test_findings_name_file_and_line(self):
        _, out = lint("cpp26_lint.py", FIXTURES / "dirty", "src/idioms.cpp")
        self.assertIn("src/idioms.cpp:5: [unconstrained-template]", out)
        self.assertIn("src/idioms.cpp:26: [comment]", out)


if __name__ == "__main__":
    unittest.main()
