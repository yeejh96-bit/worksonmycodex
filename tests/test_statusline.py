from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import tomllib
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills" / "works-on-my-codex-statusline" / "scripts" / "configure_statusline.py"
HOOKS = ROOT / "hooks" / "hooks.json"
EXPECTED = ["model", "project-name", "context-used", "five-hour-limit", "weekly-limit"]


def run(config: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--config", str(config), *args],
        capture_output=True,
        text=True,
        check=False,
    )


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class StatusLineTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.config = Path(self.temp.name) / "config.toml"

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_preview_does_not_create_config(self) -> None:
        result = run(self.config)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Preview only", result.stdout)
        self.assertFalse(self.config.exists())

    def test_apply_creates_config_and_is_idempotent(self) -> None:
        first = run(self.config, "--apply")
        self.assertEqual(first.returncode, 0, first.stderr)
        parsed = tomllib.loads(self.config.read_text(encoding="utf-8"))
        self.assertEqual(parsed["tui"]["status_line"], EXPECTED)
        before = digest(self.config)

        second = run(self.config, "--apply")
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertIn("unchanged", second.stdout)
        self.assertEqual(digest(self.config), before)

    def test_quiet_apply_is_silent_for_session_start_hook(self) -> None:
        first = run(self.config, "--apply", "--quiet")
        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertEqual(first.stdout, "")
        parsed = tomllib.loads(self.config.read_text(encoding="utf-8"))
        self.assertEqual(parsed["tui"]["status_line"], EXPECTED)

        second = run(self.config, "--apply", "--quiet")
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertEqual(second.stdout, "")

    def test_once_state_does_not_overwrite_later_user_customization(self) -> None:
        state = Path(self.temp.name) / "plugin-data" / "statusline-v1.applied"
        first = run(self.config, "--apply", "--quiet", "--once-state", str(state))
        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertTrue(state.is_file())

        self.config.write_text('[tui]\nstatus_line = ["model"]\n', encoding="utf-8")
        second = run(self.config, "--apply", "--quiet", "--once-state", str(state))
        self.assertEqual(second.returncode, 0, second.stderr)
        parsed = tomllib.loads(self.config.read_text(encoding="utf-8"))
        self.assertEqual(parsed["tui"]["status_line"], ["model"])

    def test_replaces_thread_name_and_preserves_other_settings(self) -> None:
        original = (
            'model = "gpt-example"\n\n'
            "[tui]\n"
            'status_line = ["model-with-reasoning", "current-dir", "thread-name"]  # my footer\n'
            "status_line_use_colors = false\n\n"
            "[features]\nplugins = true\n"
        )
        self.config.write_text(original, encoding="utf-8")
        result = run(self.config, "--apply")
        self.assertEqual(result.returncode, 0, result.stderr)
        updated = self.config.read_text(encoding="utf-8")
        parsed = tomllib.loads(updated)
        self.assertEqual(parsed["tui"]["status_line"], EXPECTED)
        self.assertFalse(parsed["tui"]["status_line_use_colors"])
        self.assertEqual(parsed["model"], "gpt-example")
        self.assertTrue(parsed["features"]["plugins"])
        self.assertNotIn("thread-name", updated)
        self.assertNotIn("current-dir", updated)
        self.assertNotIn("model-with-reasoning", updated)
        self.assertIn("# my footer", updated)

    def test_ambiguous_multiline_value_is_preserved(self) -> None:
        original = '[tui]\nstatus_line = [\n  "thread-name",\n]\n'
        self.config.write_text(original, encoding="utf-8")
        before = digest(self.config)
        result = run(self.config, "--apply")
        self.assertEqual(result.returncode, 2)
        self.assertIn("multiline", result.stderr)
        self.assertEqual(digest(self.config), before)

    def test_check_reports_drift_without_writing(self) -> None:
        result = run(self.config, "--check")
        self.assertEqual(result.returncode, 1)
        self.assertFalse(self.config.exists())

    def test_plugin_session_start_hook_applies_statusline_quietly(self) -> None:
        hooks = json.loads(HOOKS.read_text(encoding="utf-8"))
        session_start = hooks["hooks"]["SessionStart"]
        self.assertEqual(len(session_start), 1)
        self.assertEqual(session_start[0]["matcher"], "startup|resume|clear")
        command = session_start[0]["hooks"][0]
        self.assertEqual(command["type"], "command")
        self.assertIn("$PLUGIN_ROOT/skills/works-on-my-codex-statusline", command["command"])
        self.assertIn("--apply --quiet", command["command"])
        self.assertIn("$PLUGIN_DATA/statusline-v1.applied", command["command"])
        self.assertIn("%PLUGIN_ROOT%", command["commandWindows"])


if __name__ == "__main__":
    unittest.main()
