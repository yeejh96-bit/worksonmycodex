from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills" / "works-on-my-codex" / "scripts" / "womc_check.py"
PHILOSOPHY = (
    "> **WOMC 철학:** 사람은 원하는 것과 되돌릴 수 없는 결정만 맡고, 나머지는 모델이 맡는다. "
    "AGENTS.md에는 변하지 않는 제품 원칙, 보안·승인 경계, 작업별 문서·스킬 경로, 공통 검증 방법만 둔다."
)


def run(project: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--project", str(project)],
        capture_output=True,
        text=True,
        check=False,
    )


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
        (self.project / "AGENTS.md").write_text(
            f"{PHILOSOPHY}\n<!-- womc:skeleton-version=0.9.0 -->\n"
            "<!-- womc:project-harness:start -->\n",
            encoding="utf-8",
        )
        result = run(self.project)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("v0.9.0", result.stdout)
        self.assertIn("갱신", result.stdout)

    def test_current_or_newer_harness_is_silent(self) -> None:
        for version in ("1.0.0", "1.1.0"):
            with self.subTest(version=version):
                (self.project / "AGENTS.md").write_text(
                    f"{PHILOSOPHY}\n<!-- womc:skeleton-version={version} -->\n"
                    "<!-- womc:project-harness:start -->\n",
                    encoding="utf-8",
                )
                result = run(self.project)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stdout, "")

    def test_nonempty_override_reports_shadowing(self) -> None:
        (self.project / "AGENTS.md").write_text("<!-- womc:skeleton-version=1.0.0 -->\n", encoding="utf-8")
        (self.project / "AGENTS.override.md").write_text("# Override\n", encoding="utf-8")
        result = run(self.project)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("AGENTS.override.md", result.stdout)
        self.assertIn("충돌", result.stdout)

    def test_incomplete_current_harness_requests_refresh(self) -> None:
        (self.project / "AGENTS.md").write_text("<!-- womc:skeleton-version=1.0.0 -->\n", encoding="utf-8")
        result = run(self.project)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("불완전", result.stdout)


if __name__ == "__main__":
    unittest.main()
