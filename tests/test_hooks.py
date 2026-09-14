from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HOOKS = ROOT / "hooks" / "hooks.json"


def session_start_command(platform: str = "linux") -> str:
    hooks = json.loads(HOOKS.read_text(encoding="utf-8"))
    entry = hooks["hooks"]["SessionStart"]
    command = entry[0]["hooks"][0]
    return command["commandWindows" if platform == "windows" else "command"]


class SessionStartHookTest(unittest.TestCase):
    def test_only_read_only_harness_check_remains(self) -> None:
        hooks = json.loads(HOOKS.read_text(encoding="utf-8"))
        session_start = hooks["hooks"]["SessionStart"]
        self.assertEqual(len(session_start), 1)
        self.assertEqual(session_start[0]["matcher"], "startup|resume|clear")
        commands = session_start[0]["hooks"]
        self.assertEqual(len(commands), 1)
        self.assertEqual(commands[0]["type"], "command")
        serialized = json.dumps(commands, ensure_ascii=False).lower()
        self.assertIn("womc_check.py", serialized)
        self.assertNotIn("statusline", serialized)
        self.assertNotIn("status_line", serialized)
        self.assertNotIn("plugin_data", serialized)

    def test_linux_command_uses_actual_codex_plugin_root(self) -> None:
        command = session_start_command()
        self.assertIn("$CLAUDE_PLUGIN_ROOT/skills/works-on-my-codex/scripts/womc_check.py", command)
        self.assertNotIn("$PLUGIN_ROOT", command)

    def test_windows_command_uses_actual_codex_plugin_root(self) -> None:
        command = session_start_command("windows")
        self.assertIn(
            r"%CLAUDE_PLUGIN_ROOT%\skills\works-on-my-codex\scripts\womc_check.py",
            command,
        )
        self.assertNotIn("%PLUGIN_ROOT%", command)

    def test_linux_command_runs_with_only_actual_hook_environment(self) -> None:
        with tempfile.TemporaryDirectory() as project:
            env = os.environ.copy()
            env.pop("PLUGIN_ROOT", None)
            env.pop("PLUGIN_DATA", None)
            env["CLAUDE_PLUGIN_ROOT"] = str(ROOT)
            result = subprocess.run(
                session_start_command(),
                shell=True,
                cwd=project,
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("하네스가 없다", result.stdout)
        self.assertNotIn("can't open file", result.stderr)

    def test_missing_plugin_root_warns_but_does_not_fail_session(self) -> None:
        env = os.environ.copy()
        env.pop("CLAUDE_PLUGIN_ROOT", None)
        env.pop("PLUGIN_ROOT", None)
        result = subprocess.run(
            session_start_command(),
            shell=True,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("CLAUDE_PLUGIN_ROOT is not set", result.stderr)

    def test_duplicate_linux_execution_is_read_only_and_stable(self) -> None:
        with tempfile.TemporaryDirectory() as project:
            env = os.environ.copy()
            env["CLAUDE_PLUGIN_ROOT"] = str(ROOT)
            command = session_start_command()
            first = subprocess.run(
                command,
                shell=True,
                cwd=project,
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )
            before = list(Path(project).iterdir())
            second = subprocess.run(
                command,
                shell=True,
                cwd=project,
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )
            after = list(Path(project).iterdir())
        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertEqual(first.stdout, second.stdout)
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
