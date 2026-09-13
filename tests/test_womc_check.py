from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills" / "works-on-my-codex" / "scripts" / "womc_check.py"
SETUP = ROOT / "skills" / "works-on-my-codex" / "scripts" / "setup_harness.py"
PHILOSOPHY = (
    "> **WOMC 철학:** 사람은 원하는 것과 되돌릴 수 없는 결정만 맡고, 나머지는 모델이 맡는다. "
    "AGENTS.md에는 자율 실행 원칙, 프로젝트 목적·지속 제약·완료 기준, 작업별 읽기 경로, 공통 검증 방법만 둔다."
)
PLUGIN_VERSION = json.loads((ROOT / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8"))["version"]
VERSION_MARKER = f"<!-- womc:version={PLUGIN_VERSION} -->"


def run(project: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--project", str(project)],
        capture_output=True,
        text=True,
        check=False,
    )


def setup(project: Path) -> None:
    result = subprocess.run(
        [sys.executable, str(SETUP), "--project", str(project)],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise AssertionError(result.stderr)


class WomcCheckTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.project = Path(self.temp.name)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_missing_harness_requests_setup(self) -> None:
        result = run(self.project)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("하네스가 없다", result.stdout)
        self.assertIn("$works-on-my-codex", result.stdout)

    def test_stale_harness_requests_refresh(self) -> None:
        setup(self.project)
        agents = self.project / "AGENTS.md"
        agents.write_text(
            agents.read_text(encoding="utf-8").replace(
                VERSION_MARKER,
                "<!-- womc:skeleton-version=1.0.0 -->",
            ),
            encoding="utf-8",
        )
        result = run(self.project)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("v1.0.0", result.stdout)
        self.assertIn("갱신", result.stdout)

    def test_current_or_newer_harness_is_silent(self) -> None:
        for version in (PLUGIN_VERSION, "1.2.0+codex.20990101000000"):
            with self.subTest(version=version):
                setup(self.project)
                agents = self.project / "AGENTS.md"
                content = agents.read_text(encoding="utf-8")
                agents.write_text(
                    content.replace(
                        VERSION_MARKER,
                        f"<!-- womc:version={version} -->",
                    ),
                    encoding="utf-8",
                )
                result = run(self.project)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stdout, "")

    def test_plugin_cachebuster_update_requests_harness_refresh(self) -> None:
        setup(self.project)
        agents = self.project / "AGENTS.md"
        agents.write_text(
            agents.read_text(encoding="utf-8").replace(
                VERSION_MARKER,
                "<!-- womc:version=1.1.0+codex.20260101000000 -->",
            ),
            encoding="utf-8",
        )

        result = run(self.project)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("설치된 WOMC", result.stdout)
        self.assertIn("갱신", result.stdout)

    def test_project_structure_drift_requests_automatic_refresh(self) -> None:
        setup(self.project)
        docs = self.project / "docs"
        docs.mkdir()
        (docs / "architecture.md").write_text("# Architecture\n", encoding="utf-8")

        result = run(self.project)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("시작 문서", result.stdout)
        self.assertIn("$works-on-my-codex", result.stdout)
        self.assertIn("되묻지 말고", result.stdout)

    def test_ordinary_source_changes_do_not_request_refresh(self) -> None:
        setup(self.project)
        (self.project / "app.py").write_text("value = 1\n", encoding="utf-8")

        result = run(self.project)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "")

    def test_context_document_content_change_requests_semantic_review(self) -> None:
        docs = self.project / "docs"
        docs.mkdir()
        context = docs / "context.md"
        context.write_text("# Context\n\nInitial rule.\n", encoding="utf-8")
        setup(self.project)
        context.write_text("# Context\n\nRead this before every implementation task.\n", encoding="utf-8")

        result = run(self.project)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("시작 문서", result.stdout)
        self.assertIn("하네스를 갱신", result.stdout)

    def test_nonempty_override_reports_shadowing(self) -> None:
        (self.project / "AGENTS.md").write_text("<!-- womc:skeleton-version=1.0.0 -->\n", encoding="utf-8")
        (self.project / "AGENTS.override.md").write_text("# Override\n", encoding="utf-8")
        result = run(self.project)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("AGENTS.override.md", result.stdout)
        self.assertIn("충돌", result.stdout)

    def test_incomplete_current_harness_requests_refresh(self) -> None:
        (self.project / "AGENTS.md").write_text(f"{VERSION_MARKER}\n", encoding="utf-8")
        result = run(self.project)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("불완전", result.stdout)


if __name__ == "__main__":
    unittest.main()
