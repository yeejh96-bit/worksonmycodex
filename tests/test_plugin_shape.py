from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class PluginShapeTest(unittest.TestCase):
    def test_plugin_version_is_plain_semver(self) -> None:
        manifest = json.loads(
            (ROOT / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8")
        )
        self.assertRegex(manifest["version"], r"^\d+\.\d+\.\d+$")

    def test_plugin_does_not_bundle_session_hooks(self) -> None:
        self.assertFalse((ROOT / "hooks" / "hooks.json").exists())
        self.assertFalse(
            (
                ROOT
                / "skills"
                / "works-on-my-codex"
                / "scripts"
                / "womc_check.py"
            ).exists()
        )


if __name__ == "__main__":
    unittest.main()
