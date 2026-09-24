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

    def test_environment_audit_is_routed_through_application_and_update(self) -> None:
        skill_root = ROOT / "skills" / "works-on-my-codex"
        skill = (skill_root / "SKILL.md").read_text(encoding="utf-8")
        update = (skill_root / "references" / "plugin-update.md").read_text(encoding="utf-8")
        audit = skill_root / "references" / "project-environment-audit.md"

        self.assertTrue(audit.is_file())
        self.assertIn("[프로젝트 환경 감사](references/project-environment-audit.md)", skill)
        self.assertIn("WOMC 최초 적용", skill)
        self.assertIn("일반 작업에 따른 하네스 동기화는 이 전체 감사의 실행 조건이 아니다", skill)
        self.assertIn("새 스킬의 [프로젝트 환경 감사](project-environment-audit.md)", update)
        self.assertIn("현재 프로젝트가 WOMC 저장소여도 예외가 아닙니다", update)
        self.assertIn("하네스 수정 후 전체 감사를 다시 시작하지 않습니다", update)
        self.assertIn(
            "WOMC 설치·온보딩·수동 갱신: `skills/works-on-my-codex/SKILL.md`",
            (ROOT / "AGENTS.md").read_text(encoding="utf-8"),
        )


if __name__ == "__main__":
    unittest.main()
