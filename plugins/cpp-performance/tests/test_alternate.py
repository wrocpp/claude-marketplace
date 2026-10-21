#!/usr/bin/env python3
"""Tests of scripts/alternate.py: parsing, alternation order, statistics, table. No timing is asserted."""
import importlib.util
import pathlib
import shlex
import subprocess
import sys
import unittest

HERE = pathlib.Path(__file__).resolve().parent
SCRIPT = HERE.parent / "scripts" / "alternate.py"
spec = importlib.util.spec_from_file_location("alternate", SCRIPT)
alternate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(alternate)

EVEN_SAMPLE = [100.0, 1.0, 3.0, 2.0]  # median 2.5, mean 26.5
ODD_SAMPLE = [30.0, 1.0, 2.0]  # median 2.0, mean 11.0


class Parsing(unittest.TestCase):
    def test_last_field_is_the_value_and_the_rest_the_key(self):
        self.assertEqual(alternate.parse_measurements("QHash,1000,drain,285.5\n"), {("QHash", "1000", "drain"): 285.5})

    def test_comments_blank_lines_and_text_values_are_ignored(self):
        text = "# load 0.5\n\nSKIP: not here\nname,header,value\nok,1\n"
        self.assertEqual(alternate.parse_measurements(text), {("ok",): 1.0})

    def test_ignore_field_drops_the_variant_from_the_key(self):
        text = "e2e,qvariant,QList,1000,fill,146.3\n"
        self.assertEqual(alternate.parse_measurements(text, ignore_field=1), {("e2e", "QList", "1000", "fill"): 146.3})

    def test_ignore_field_past_the_end_changes_nothing(self):
        self.assertEqual(alternate.parse_measurements("a,2\n", ignore_field=5), {("a",): 2.0})

    def test_a_line_with_only_a_value_has_an_empty_key(self):
        self.assertEqual(alternate.parse_measurements("7\n"), {(): 7.0})


class Order(unittest.TestCase):
    def test_runs_alternate_a_b_a_b(self):
        _, order = alternate.collect({"A": ["a"], "B": ["b"]}, 3, False, None, runner=lambda argv: "k,1\n")
        self.assertEqual(order, ["A", "B", "A", "B", "A", "B"])

    def test_balance_reverses_every_second_run(self):
        _, order = alternate.collect({"A": ["a"], "B": ["b"]}, 4, True, None, runner=lambda argv: "k,1\n")
        self.assertEqual(order, ["A", "B", "B", "A", "A", "B", "B", "A"])

    def test_three_designs_keep_their_order_within_a_run(self):
        self.assertEqual(alternate.run_order(["A", "B", "C"], 0, True), ["A", "B", "C"])
        self.assertEqual(alternate.run_order(["A", "B", "C"], 1, True), ["C", "B", "A"])

    def test_every_run_calls_the_command_of_its_label(self):
        seen = []
        alternate.collect({"A": ["a"], "B": ["b"]}, 2, False, None, runner=lambda argv: seen.append(argv[0]) or "k,1\n")
        self.assertEqual(seen, ["a", "b", "a", "b"])


class Statistics(unittest.TestCase):
    def test_median_of_an_even_count_is_the_mean_of_the_middle_two(self):
        self.assertEqual(alternate.summary(EVEN_SAMPLE), (2.5, 1.0, 100.0))

    def test_median_of_an_odd_count_is_the_middle_value(self):
        self.assertEqual(alternate.summary(ODD_SAMPLE), (2.0, 1.0, 30.0))

    def test_cell_prints_median_then_min_and_max(self):
        self.assertEqual(alternate.cell(ODD_SAMPLE), "2.0 (1.0-30.0)")

    def test_ratio_is_the_ratio_of_medians_not_of_means(self):
        self.assertEqual(alternate.ratio([2.0, 2.0, 100.0], [1.0, 1.0, 1.0]), 2.0)

    def test_values_are_collected_per_label_and_key_across_runs(self):
        outputs = iter(["k,1\n", "k,10\n", "k,3\n", "k,30\n", "k,2\n", "k,20\n"])
        samples, _ = alternate.collect({"A": ["a"], "B": ["b"]}, 3, False, None, runner=lambda argv: next(outputs))
        self.assertEqual(samples["A"][("k",)], [1.0, 3.0, 2.0])
        self.assertEqual(samples["B"][("k",)], [10.0, 30.0, 20.0])


class Table(unittest.TestCase):
    def samples(self):
        return {
            "A": {("k",): [1.0, 2.0, 3.0], ("only-a",): [1.0, 1.0, 1.0], ("late",): [1.0, 1.0, 1.0]},
            "B": {("k",): [2.0, 4.0, 6.0], ("short",): [1.0], ("late",): [1.0]},
        }

    def test_a_key_missing_from_a_design_or_a_run_is_not_reported(self):
        self.assertEqual(alternate.common_keys(self.samples(), 3), [("k",)])

    def test_render_has_one_row_per_common_key_and_the_ratio_to_the_first_design(self):
        lines = alternate.render(self.samples(), 3).splitlines()
        self.assertEqual(lines[0], "| key | A | B | B/A |")
        self.assertEqual(lines[2], "| k | 2.0 (1.0-3.0) | 4.0 (2.0-6.0) | 2.00 |")
        self.assertEqual(len(lines), 3)


class Designs(unittest.TestCase):
    def test_command_is_split_without_a_shell(self):
        self.assertEqual(alternate.parse_designs(["a=./bench --size 10", "b=./bench2"]), {"a": ["./bench", "--size", "10"], "b": ["./bench2"]})

    def test_a_metacharacter_stays_an_argument(self):
        self.assertEqual(alternate.parse_designs(["a=echo ; rm -rf x", "b=true"])["a"], ["echo", ";", "rm", "-rf", "x"])

    def test_bad_designs_are_refused(self):
        for specs in (["a=x"], ["a=x", "a=y"], ["a=x", "b="], ["a=x", "=y"], ["a=x", "noequals"]):
            with self.assertRaises(ValueError, msg=specs):
                alternate.parse_designs(specs)


class CommandLine(unittest.TestCase):
    def py(self, code):
        return shlex.join([sys.executable, "-c", code])

    def run_cli(self, *args):
        return subprocess.run([sys.executable, str(SCRIPT), *args], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    def test_end_to_end_with_two_commands(self):
        done = self.run_cli("--runs", "3", "--balance", "a=" + self.py("print('k,2')"), "b=" + self.py("print('k,4')"))
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertIn("| k | 2.0 (2.0-2.0) | 4.0 (4.0-4.0) | 2.00 |", done.stdout)
        self.assertIn("load before", done.stdout)
        self.assertIn("order a b b a a b", done.stdout)

    def test_a_failing_command_fails_the_run(self):
        done = self.run_cli("--runs", "1", "a=" + self.py("raise SystemExit(3)"), "b=" + self.py("print('k,1')"))
        self.assertNotEqual(done.returncode, 0)

    def test_one_design_is_a_usage_error(self):
        done = self.run_cli("a=true")
        self.assertEqual(done.returncode, 2)

    def test_zero_runs_is_a_usage_error(self):
        done = self.run_cli("--runs", "0", "a=true", "b=true")
        self.assertEqual(done.returncode, 2)


if __name__ == "__main__":
    unittest.main(verbosity=1)
