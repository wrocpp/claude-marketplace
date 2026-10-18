import atexit
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
PRECHECK = SCRIPTS / "precheck.py"
POSTCHECK = SCRIPTS / "postcheck.py"
REFLECTION_SKILL = "reflect-dont-hand-write"
IDIOMS_SKILL = "cpp26-idioms"

HAND_SWITCH = 'constexpr auto f(E e) {\n  switch (e) {\n    case E::a: return "a";\n    case E::b: return "b";\n    case E::c: return "c";\n  }\n}\n'
BARE_TEMPLATE = "template <class Sink>\nvoid drain(Sink& out) {\n  out.write(1);\n}\n"
STD_INCLUDE = "module;\n#include <vector>\nexport module m;\n"
STRAY_COMMENT = "int value = 1;  // the answer\n"
CLEAN = "template <std::invocable F>\nauto run(F fn) { return fn(); }\n"


class Project:
    def __init__(self, config=None, allow=None):
        self.root = pathlib.Path(tempfile.mkdtemp()).resolve()
        atexit.register(shutil.rmtree, self.root, True)
        (self.root / "src").mkdir()
        (self.root / ".claude").mkdir()
        if config is not None:
            (self.root / ".claude/cpp26-guard.json").write_text(json.dumps(config))
        if allow is not None:
            (self.root / ".claude/cpp26-guard-allow.txt").write_text(allow)

    def run(self, script, tool_input, event_cwd=None):
        payload = {"cwd": str(event_cwd or self.root), "tool_input": tool_input}
        env = {key: value for key, value in os.environ.items() if key != "CLAUDE_PROJECT_DIR"}
        done = subprocess.run([sys.executable, str(script)], input=json.dumps(payload), capture_output=True, text=True, env=env, cwd=self.root)
        return done.returncode, done.stdout

    def write(self, path, content, script=PRECHECK):
        return self.run(script, {"file_path": str(self.root / path), "content": content})


def context_of(stdout):
    return json.loads(stdout)["hookSpecificOutput"]["additionalContext"]


class PrecheckTest(unittest.TestCase):
    def test_a_hand_written_switch_names_the_reflection_skill(self):
        code, out = Project().write("src/probe.cpp", HAND_SWITCH)
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)["hookSpecificOutput"]["hookEventName"], "PreToolUse")
        self.assertIn(REFLECTION_SKILL, context_of(out))
        self.assertIn("enum-name-switch", context_of(out))

    def test_a_bare_called_template_names_the_idioms_skill(self):
        code, out = Project().write("src/probe.cpp", BARE_TEMPLATE)
        self.assertEqual(code, 0)
        self.assertIn(IDIOMS_SKILL, context_of(out))
        self.assertIn("unconstrained-template", context_of(out))

    def test_a_standard_include_is_named_in_a_modules_project(self):
        _, out = Project({"modules": True}).write("src/probe.cppm", STD_INCLUDE)
        self.assertIn("std-include", context_of(out))

    def test_a_standard_include_is_quiet_without_modules(self):
        self.assertEqual(Project().write("src/probe.cppm", STD_INCLUDE), (0, ""))

    def test_a_stray_comment_is_named_only_under_the_comment_policy(self):
        self.assertEqual(Project().write("src/probe.cpp", STRAY_COMMENT), (0, ""))
        _, out = Project({"rules": {"comment": True}}).write("src/probe.cpp", STRAY_COMMENT)
        self.assertIn("[comment]", context_of(out))

    def test_clean_text_prints_nothing(self):
        self.assertEqual(Project().write("src/probe.cpp", CLEAN), (0, ""))

    def test_the_helper_map_names_the_project_helper(self):
        _, out = Project({"helpers": {"enum_name": "reflect::enum_name"}}).write("src/probe.cpp", HAND_SWITCH)
        self.assertIn("reflect::enum_name", context_of(out))

    def test_an_edit_scans_only_the_new_string(self):
        project = Project()
        quiet = {"file_path": str(project.root / "src/probe.cpp"), "old_string": HAND_SWITCH, "new_string": CLEAN}
        self.assertEqual(project.run(PRECHECK, quiet), (0, ""))

    def test_a_multi_edit_scans_every_new_string(self):
        project = Project()
        edits = [{"old_string": "x", "new_string": CLEAN}, {"old_string": "y", "new_string": HAND_SWITCH}]
        _, out = project.run(PRECHECK, {"file_path": str(project.root / "src/probe.cpp"), "edits": edits})
        self.assertIn(REFLECTION_SKILL, context_of(out))

    def test_other_files_and_directories_pass_untouched(self):
        project = Project()
        for path in ("README.md", "tools/probe.cpp", "src/probe.txt"):
            self.assertEqual(project.write(path, HAND_SWITCH), (0, ""), path)

    def test_configured_roots_and_excludes_apply(self):
        project = Project({"roots": ["lib"], "exclude": ["lib/gen/"]})
        self.assertEqual(project.write("src/probe.cpp", HAND_SWITCH), (0, ""))
        self.assertEqual(project.write("lib/gen/probe.cpp", HAND_SWITCH), (0, ""))
        self.assertIn(REFLECTION_SKILL, context_of(project.write("lib/probe.cpp", HAND_SWITCH)[1]))

    def test_a_path_outside_the_project_is_ignored(self):
        project = Project()
        self.assertEqual(project.write("../elsewhere/src/probe.cpp", HAND_SWITCH), (0, ""))

    def test_an_allowance_keeps_a_finding_quiet(self):
        project = Project(allow="src/probe.cpp|enum-name-switch|case E::a|wire words differ from the enumerators\n")
        self.assertEqual(project.write("src/probe.cpp", HAND_SWITCH), (0, ""))


class NeverBlockTest(unittest.TestCase):
    def run_raw(self, script, stdin, project=None):
        done = subprocess.run([sys.executable, str(script)], input=stdin, capture_output=True, text=True, cwd=project.root if project else None)
        return done.returncode, done.stdout

    def test_a_broken_payload_never_blocks(self):
        for script in (PRECHECK, POSTCHECK):
            self.assertEqual(self.run_raw(script, "not json"), (0, ""), script.name)


    def test_a_malformed_allowance_file_never_blocks(self):
        self.assertEqual(Project(allow="bad line\n").write("src/probe.cpp", HAND_SWITCH), (0, ""))

    def test_an_empty_payload_never_blocks(self):
        self.assertEqual(self.run_raw(PRECHECK, "{}"), (0, ""))


class PostcheckTest(unittest.TestCase):
    def test_the_whole_file_report_covers_both_lints(self):
        project = Project()
        (project.root / "src/probe.cpp").write_text(HAND_SWITCH + BARE_TEMPLATE)
        code, out = project.run(POSTCHECK, {"file_path": str(project.root / "src/probe.cpp")})
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)["hookSpecificOutput"]["hookEventName"], "PostToolUse")
        self.assertIn(REFLECTION_SKILL, context_of(out))
        self.assertIn(IDIOMS_SKILL, context_of(out))

    def test_a_clean_file_prints_nothing(self):
        project = Project()
        (project.root / "src/probe.cpp").write_text(CLEAN)
        self.assertEqual(project.run(POSTCHECK, {"file_path": str(project.root / "src/probe.cpp")}), (0, ""))

    def test_a_missing_file_prints_nothing(self):
        project = Project()
        self.assertEqual(project.run(POSTCHECK, {"file_path": str(project.root / "src/none.cpp")}), (0, ""))

    def test_the_project_dir_variable_beats_a_subdirectory_cwd(self):
        project = Project()
        (project.root / "src/probe.cpp").write_text(HAND_SWITCH)
        payload = {"cwd": str(project.root / "src"), "tool_input": {"file_path": str(project.root / "src/probe.cpp")}}
        env = {**os.environ, "CLAUDE_PROJECT_DIR": str(project.root)}
        done = subprocess.run([sys.executable, str(POSTCHECK)], input=json.dumps(payload), capture_output=True, text=True, env=env)
        self.assertIn(REFLECTION_SKILL, context_of(done.stdout))


class ManifestTest(unittest.TestCase):
    def test_hooks_json_points_at_scripts_that_exist(self):
        data = json.loads((PLUGIN / "hooks/hooks.json").read_text())
        for event, entries in data["hooks"].items():
            for entry in entries:
                self.assertEqual(entry["matcher"], "Edit|Write|MultiEdit")
                for hook in entry["hooks"]:
                    script = hook["command"].split("${CLAUDE_PLUGIN_ROOT}/")[1].rstrip('"')
                    self.assertTrue((PLUGIN / script).is_file(), script)


if __name__ == "__main__":
    unittest.main()
