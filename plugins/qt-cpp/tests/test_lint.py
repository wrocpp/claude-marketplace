#!/usr/bin/env python3
"""The lint, in both directions: every `// FINDING <rule>` line in lint-fixtures is reported and nothing else is."""
import ast
import pathlib
import re
import subprocess
import sys
import unittest

HERE = pathlib.Path(__file__).resolve().parent
PLUGIN = HERE.parent
FIXTURES = HERE / "lint-fixtures"
LINT = PLUGIN / "scripts" / "qt_model_lint.py"
sys.path.insert(0, str(PLUGIN / "scripts"))

import cpp_text  # noqa: E402
import qt_model_lint  # noqa: E402

EXPECTED = re.compile(r"//.*\bFINDING ([a-z-]+)")
MAX_COMPLEXITY = 8
TIMEOUT_SECONDS = 60
CLEAN_FIXTURES = ("begin_end_paired", "begin_end_split_with_marker", "connect_resolved", "key_role_stable", "fromvalue_elsewhere")
BAD_FIXTURES = ("begin_without_end", "dependent_base_connect_unqualified", "row_as_key", "fromvalue_in_template")


def expected_findings(text):
    return {(number, found.group(1)) for number, line in enumerate(text.split("\n"), 1) if (found := EXPECTED.search(line))}


def reported(text, rules=None):
    return {(f.line, f.rule) for f in qt_model_lint.scan(text, rules)}


class Fixtures(unittest.TestCase):
    def test_every_marked_line_is_reported_and_nothing_else(self):
        for name in BAD_FIXTURES + CLEAN_FIXTURES:
            with self.subTest(name):
                text = (FIXTURES / f"{name}.cpp").read_text(encoding="utf-8")
                self.assertEqual(reported(text), expected_findings(text))

    def test_the_bad_fixtures_expect_something_and_the_clean_ones_nothing(self):
        for name in BAD_FIXTURES:
            self.assertTrue(expected_findings((FIXTURES / f"{name}.cpp").read_text(encoding="utf-8")), name)
        for name in CLEAN_FIXTURES:
            self.assertFalse(expected_findings((FIXTURES / f"{name}.cpp").read_text(encoding="utf-8")), name)

    def test_every_fixture_file_is_listed(self):
        listed = {f"{n}.cpp" for n in BAD_FIXTURES + CLEAN_FIXTURES}
        self.assertEqual({p.name for p in FIXTURES.glob("*.cpp")}, listed)

    def test_every_rule_has_a_bad_fixture(self):
        seen = set()
        for name in BAD_FIXTURES:
            seen |= {rule for _, rule in expected_findings((FIXTURES / f"{name}.cpp").read_text(encoding="utf-8"))}
        self.assertEqual(seen, set(qt_model_lint.CHECKS))


class Behaviour(unittest.TestCase):
    def test_a_marker_needs_a_reason(self):
        silenced = "void f() {\n  // qt-model-ok: ended in the slot\n  beginResetModel();\n}\n"
        bare = "void f() {\n  // qt-model-ok:\n  beginResetModel();\n}\n"
        self.assertEqual(reported(silenced), set())
        self.assertEqual(reported(bare), {(3, "begin-end-pairing")})

    def test_rule_filter(self):
        text = (FIXTURES / "begin_without_end.cpp").read_text(encoding="utf-8")
        self.assertEqual(reported(text, {"row-as-key"}), set())
        self.assertTrue(reported(text, {"begin-end-pairing"}))

    def test_one_end_does_not_pay_for_two_begins(self):
        text = "void f() {\n  beginInsertRows(a, 0, 0);\n  beginInsertRows(a, 1, 1);\n  endInsertRows();\n}\n"
        self.assertEqual(reported(text), {(3, "begin-end-pairing")})

    def test_comments_strings_and_preprocessor_are_not_code(self):
        text = '#define X beginResetModel()\nvoid f() {\n  // beginResetModel();\n  const char* s = "beginResetModel(";\n}\n'
        self.assertEqual(reported(text), set())

    def test_row_as_key_for_a_local_named_other_than_row(self):
        text = "QVariant M::data(const QModelIndex& i, int role) const {\n  const int position = i.row();\n  if (role == KeyRole) return position;\n  return {};\n}\n"
        self.assertEqual(reported(text), {(3, "row-as-key")})

    def test_a_role_that_only_mentions_a_key_word_inside_a_longer_word(self):
        text = "QVariant M::data(const QModelIndex& i, int role) const {\n  if (role == MonkeyRole) return i.row();\n  return {};\n}\n"
        self.assertEqual(reported(text), set())

    def test_an_unterminated_block_does_not_crash(self):
        self.assertEqual(reported("void f() { beginResetModel();"), {(1, "begin-end-pairing")})
        self.assertEqual(reported("template <class T struct X : T { connect("), set())


class Mask(unittest.TestCase):
    def test_length_and_newlines_are_kept(self):
        text = '#define A 1 /* c */\nint a = 1\'000; // x "y"\nconst char* s = R"d(a "q" ) text)d"; /* two\nlines */ int b;\n'
        for drop in (False, True):
            masked = cpp_text.mask(text, drop_preprocessor=drop)
            self.assertEqual(len(masked), len(text))
            self.assertEqual(masked.count("\n"), text.count("\n"))

    def test_what_is_blanked_and_what_is_not(self):
        masked = cpp_text.mask("int a = 1'000; char c = '{'; auto s = \"}\"; // {\n#define B {\nint b;\n", drop_preprocessor=True)
        self.assertNotIn("{", masked)
        self.assertNotIn("}", masked)
        self.assertIn("1'000", masked)  # a digit separator is not a character literal
        self.assertIn("int b;", masked)
        self.assertIn("#define B {", cpp_text.mask("#define B {\n"))  # kept unless asked

    def test_a_raw_string_hides_quotes_and_braces(self):
        masked = cpp_text.mask('auto s = R"d(a " { ) text)d"; int x;')
        self.assertNotIn("{", masked)
        self.assertIn("int x;", masked)


class CommandLine(unittest.TestCase):
    def run_lint(self, *args):
        return subprocess.run([sys.executable, str(LINT), *map(str, args)], capture_output=True, text=True, timeout=TIMEOUT_SECONDS)

    def test_exit_codes_and_report(self):
        bad = self.run_lint(FIXTURES / "begin_without_end.cpp")
        self.assertEqual(bad.returncode, 1)
        self.assertIn("begin_without_end.cpp:6: [begin-end-pairing]", bad.stdout)
        good = self.run_lint(FIXTURES / "begin_end_paired.cpp")
        self.assertEqual((good.returncode, good.stdout), (0, ""))

    def test_a_directory_is_scanned_recursively(self):
        result = self.run_lint(FIXTURES, "--rule", "row-as-key")
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout.count("[row-as-key]"), 4)

    def test_the_plugins_own_code_is_clean(self):
        # The flawed model, and the trap that shows the dependent-base connect, carry a marker with the reason.
        result = self.run_lint(PLUGIN / "include", HERE / "cpp")
        self.assertEqual((result.returncode, result.stdout), (0, ""))


def complexity(function):
    count = 1
    for node in ast.walk(function):
        if isinstance(node, (ast.If, ast.For, ast.While, ast.ExceptHandler, ast.IfExp, ast.comprehension)):
            count += 1 + (len(node.ifs) if isinstance(node, ast.comprehension) else 0)
        elif isinstance(node, ast.BoolOp):
            count += len(node.values) - 1
    return count


class Complexity(unittest.TestCase):
    def test_every_function_is_at_or_under_the_limit(self):
        files = [PLUGIN / "scripts" / "qt_model_lint.py", PLUGIN / "scripts" / "cpp_text.py", PLUGIN / "hooks" / "lint_hook.py"]
        for path in (f for f in files if f.exists()):
            for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    with self.subTest(f"{path.name}:{node.name}"):
                        self.assertLessEqual(complexity(node), MAX_COMPLEXITY)


if __name__ == "__main__":
    unittest.main(verbosity=1)
