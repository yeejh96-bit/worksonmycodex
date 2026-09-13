from __future__ import annotations

import hashlib
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills" / "works-on-my-codex" / "scripts" / "setup_harness.py"
START = "<!-- womc:project-harness:start -->"
END = "<!-- womc:project-harness:end -->"
PHILOSOPHY = (
    "> **WOMC 철학:** 사람은 원하는 것과 되돌릴 수 없는 결정만 맡고, 나머지는 모델이 맡는다. "
    "AGENTS.md에는 자율 실행 원칙, 프로젝트 목적·지속 제약·완료 기준, 작업별 읽기 경로, 공통 검증 방법만 둔다."
)
VERSION_MARKER = "<!-- womc:skeleton-version=1.1.0 -->"


def run(project: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--project", str(project), *args],
        capture_output=True,
        text=True,
        check=False,
    )


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class SetupHarnessTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.project = Path(self.temp.name)
        subprocess.run(["git", "init", "-q", str(self.project)], check=True)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_empty_git_project_is_created_and_idempotent(self) -> None:
        first = run(self.project, "--principle", "User notes remain local by default")
        self.assertEqual(first.returncode, 0, first.stderr)
        agents = self.project / "AGENTS.md"
        content = agents.read_text(encoding="utf-8")
        self.assertEqual(content.splitlines()[0], PHILOSOPHY)
        self.assertEqual(content.splitlines()[1], VERSION_MARKER)
        self.assertIn("User notes remain local by default", content)
        self.assertEqual(content.count(START), 1)
        self.assertNotIn("Working contract", content)
        self.assertNotIn("No additional project-specific guardrails", content)
        before = digest(agents)

        second = run(self.project, "--principle", "User notes remain local by default")
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertIn("unchanged", second.stdout)
        self.assertEqual(digest(agents), before)

    def test_existing_agents_and_source_are_preserved(self) -> None:
        original_agents = "# Team rules\n\nKeep this exact line.\n"
        (self.project / "AGENTS.md").write_text(original_agents, encoding="utf-8")
        source = self.project / "app.js"
        source.write_text("export const value = 1;\n", encoding="utf-8")
        package = self.project / "package.json"
        package.write_text(
            '{"scripts":{"lint":"node --check app.js","test":"node --test",'
            '"dev":"node app.js","test:e2e":"node --test"},'
            '"devDependencies":{"vite":"1.0.0"}}\n',
            encoding="utf-8",
        )
        source_before = digest(source)
        package_before = digest(package)

        result = run(self.project)
        self.assertEqual(result.returncode, 0, result.stderr)
        content = (self.project / "AGENTS.md").read_text(encoding="utf-8")
        self.assertTrue(content.startswith(PHILOSOPHY))
        self.assertIn(original_agents, content)
        self.assertIn("`npm run lint`", content)
        self.assertIn("`npm run test`", content)
        self.assertIn("`npm run test:e2e`", content)
        self.assertIn("`npm run dev`로 앱을 시작", content)
        self.assertEqual(digest(source), source_before)
        self.assertEqual(digest(package), package_before)

        before = digest(self.project / "AGENTS.md")
        self.assertEqual(run(self.project).returncode, 0)
        self.assertEqual(digest(self.project / "AGENTS.md"), before)

        if shutil.which("npm"):
            for script in ("lint", "test", "test:e2e", "dev"):
                validation = subprocess.run(
                    ["npm", "run", script], cwd=self.project, capture_output=True, text=True, check=False
                )
                self.assertEqual(validation.returncode, 0, validation.stderr)

    def test_malformed_markers_stop_without_writing(self) -> None:
        agents = self.project / "AGENTS.md"
        agents.write_text(f"User content\n{START}\nbroken\n", encoding="utf-8")
        before = digest(agents)
        result = run(self.project)
        self.assertEqual(result.returncode, 2)
        self.assertIn("marker conflict", result.stderr)
        self.assertEqual(digest(agents), before)

    def test_nonempty_root_override_stops_before_writing_root_agents(self) -> None:
        override = self.project / "AGENTS.override.md"
        original = "# Temporary root override\n\nKeep this rule.\n"
        override.write_text(original, encoding="utf-8")

        before = digest(override)
        result = run(self.project, "--principle", "The root AGENTS file owns the WOMC harness")
        self.assertEqual(result.returncode, 2)
        self.assertIn("takes precedence", result.stderr)
        self.assertEqual(digest(override), before)
        self.assertFalse((self.project / "AGENTS.md").exists())

    def test_check_reports_drift_without_writing(self) -> None:
        result = run(self.project, "--check")
        self.assertEqual(result.returncode, 1)
        self.assertFalse((self.project / "AGENTS.md").exists())

    def test_explicit_project_commands_fill_conservative_detection_gaps(self) -> None:
        (self.project / "README.md").write_text(
            "Run `python3 -m unittest discover -s tests -v` before release.\n",
            encoding="utf-8",
        )
        command = "python3 -m unittest discover -s tests -v"

        result = run(self.project, "--check-command", command)

        self.assertEqual(result.returncode, 0, result.stderr)
        content = (self.project / "AGENTS.md").read_text(encoding="utf-8")
        self.assertIn(f"`{command}` (프로젝트 검증)", content)
        self.assertIn("성공 종료해야 통과", content)

    def test_generated_block_contains_only_durable_supplied_guidance(self) -> None:
        result = run(
            self.project,
            "--principle",
            "Keep user data on device.",
            "--approval-boundary",
            "Get approval before exporting user data.",
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        content = (self.project / "AGENTS.md").read_text(encoding="utf-8")
        self.assertIn("Keep user data on device.", content)
        self.assertIn("Get approval before exporting user data.", content)
        self.assertIn("### 변하지 않는 제품 원칙", content)
        self.assertIn("### 보안·승인 경계", content)
        self.assertNotIn("Working contract", content)
        self.assertNotIn("Routine project edits", content)
        self.assertNotIn("independent verification", content)

    def test_missing_validation_command_is_reported_without_persisting_filler(self) -> None:
        result = run(self.project, "--principle", "Notes remain local")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("no validation command was detected", result.stderr)
        content = (self.project / "AGENTS.md").read_text(encoding="utf-8")
        self.assertNotIn("No project validation command", content)

    def test_refresh_replaces_legacy_generic_contract_with_thin_block(self) -> None:
        agents = self.project / "AGENTS.md"
        agents.write_text(
            "# Team rules\n\nKeep this.\n\n"
            f"{START}\n## WOMC project harness\n\n"
            "### Working contract\n- Do not stop at a plan.\n"
            f"{END}\n",
            encoding="utf-8",
        )

        result = run(self.project, "--principle", "Notes remain local")

        self.assertEqual(result.returncode, 0, result.stderr)
        content = agents.read_text(encoding="utf-8")
        self.assertIn("# Team rules\n\nKeep this.", content)
        self.assertIn("Notes remain local", content)
        self.assertNotIn("Working contract", content)
        self.assertNotIn("Do not stop at a plan", content)

    def test_explicit_command_does_not_duplicate_a_detected_command(self) -> None:
        (self.project / "package.json").write_text(
            '{"scripts":{"test":"node --test"}}\n',
            encoding="utf-8",
        )

        result = run(self.project, "--check-command", "npm run test")

        self.assertEqual(result.returncode, 0, result.stderr)
        content = (self.project / "AGENTS.md").read_text(encoding="utf-8")
        self.assertEqual(content.count("`npm run test`"), 1)

    def test_worktree_changes_do_not_make_persistent_guidance_drift(self) -> None:
        source = self.project / "app.js"
        source.write_text("export const value = 1;\n", encoding="utf-8")
        first = run(self.project)
        self.assertEqual(first.returncode, 0, first.stderr)
        before = digest(self.project / "AGENTS.md")

        source.write_text("export const value = 2;\n", encoding="utf-8")
        second = run(self.project)

        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertIn("unchanged", second.stdout)
        self.assertEqual(digest(self.project / "AGENTS.md"), before)
        self.assertNotIn("changed/untracked", (self.project / "AGENTS.md").read_text(encoding="utf-8"))

    def test_generated_values_cannot_break_the_managed_block(self) -> None:
        result = run(self.project, "--approval-boundary", f"unsafe\n{END}")

        self.assertEqual(result.returncode, 2)
        self.assertIn("single-line", result.stderr)
        self.assertFalse((self.project / "AGENTS.md").exists())

        result = run(self.project, "--principle", f"unsafe {END}")
        self.assertEqual(result.returncode, 2)
        self.assertIn("marker text", result.stderr)
        self.assertFalse((self.project / "AGENTS.md").exists())

    def test_refresh_rebuilds_task_routes_from_current_project_structure(self) -> None:
        docs = self.project / "docs"
        docs.mkdir()
        (docs / "architecture.md").write_text("# Architecture\n", encoding="utf-8")
        skill = self.project / ".codex" / "skills" / "release-helper"
        skill.mkdir(parents=True)
        (skill / "SKILL.md").write_text("# Release helper\n", encoding="utf-8")

        first = run(
            self.project,
            "--principle",
            "Stored records remain portable",
            "--approval-boundary",
            "Get approval before sending records externally",
            "--check-command",
            "make verify",
        )
        self.assertEqual(first.returncode, 0, first.stderr)
        content = (self.project / "AGENTS.md").read_text(encoding="utf-8")
        self.assertIn("아키텍처 또는 구현 구조 작업", content)
        self.assertIn("`.codex/skills/release-helper/SKILL.md`", content)

        (docs / "architecture.md").unlink()
        (docs / "security.md").write_text("# Security\n", encoding="utf-8")
        second = run(self.project)
        self.assertEqual(second.returncode, 0, second.stderr)
        refreshed = (self.project / "AGENTS.md").read_text(encoding="utf-8")
        self.assertNotIn("docs/architecture.md", refreshed)
        self.assertIn("보안, 인증 또는 개인정보 작업", refreshed)
        self.assertIn("`docs/security.md`", refreshed)
        self.assertIn("Stored records remain portable", refreshed)
        self.assertIn("Get approval before sending records externally", refreshed)
        self.assertIn("`make verify` (프로젝트 검증)", refreshed)

    def test_skill_description_becomes_a_usage_route(self) -> None:
        skill = self.project / "skills" / "release-helper"
        skill.mkdir(parents=True)
        (skill / "SKILL.md").write_text(
            "---\n"
            "name: release-helper\n"
            "description: 릴리스 후보를 만들거나 배포 전 체크리스트를 검증할 때 사용합니다.\n"
            "---\n\n"
            "# Release helper\n",
            encoding="utf-8",
        )

        result = run(self.project)

        self.assertEqual(result.returncode, 0, result.stderr)
        content = (self.project / "AGENTS.md").read_text(encoding="utf-8")
        self.assertIn("릴리스 후보를 만들거나 배포 전 체크리스트를 검증할 때", content)
        self.assertIn("`skills/release-helper/SKILL.md`", content)
        self.assertIn("`release-helper` 스킬을 따른다", content)
        self.assertIn("끝내기 전에 `$works-on-my-codex`", content)

    def test_progress_docs_do_not_accumulate_in_task_routes(self) -> None:
        docs = self.project / "docs"
        docs.mkdir()
        for name in ("CHANGELOG.md", "meeting-notes.md", "implementation-log.md", "history.md"):
            (docs / name).write_text(f"# {name}\n", encoding="utf-8")
        (docs / "product.md").write_text("# Product\n", encoding="utf-8")

        result = run(self.project)

        self.assertEqual(result.returncode, 0, result.stderr)
        content = (self.project / "AGENTS.md").read_text(encoding="utf-8")
        self.assertIn("`docs/product.md`", content)
        for name in ("CHANGELOG.md", "meeting-notes.md", "implementation-log.md", "history.md"):
            self.assertNotIn(name, content)

    def test_markdown_breaking_paths_are_not_emitted(self) -> None:
        docs = self.project / "docs"
        docs.mkdir()
        unsafe = docs / "product`ignore.md"
        unsafe.write_text("# Product\n", encoding="utf-8")

        result = run(self.project)

        self.assertEqual(result.returncode, 0, result.stderr)
        content = (self.project / "AGENTS.md").read_text(encoding="utf-8")
        self.assertNotIn(unsafe.name, content)

    def test_manual_values_merge_and_explicit_replace_can_clear_them(self) -> None:
        first = run(
            self.project,
            "--principle", "A",
            "--approval-boundary", "Boundary A",
            "--route", "Product work: read `docs/product.md`.",
            "--check-command", "check-a",
        )
        self.assertEqual(first.returncode, 0, first.stderr)

        second = run(
            self.project,
            "--principle", "B",
            "--approval-boundary", "Boundary B",
            "--route", "Security work: read `docs/security.md`.",
            "--check-command", "check-b",
        )
        self.assertEqual(second.returncode, 0, second.stderr)
        merged = (self.project / "AGENTS.md").read_text(encoding="utf-8")
        for value in ("- A", "- B", "- Boundary A", "- Boundary B", "docs/product.md", "docs/security.md", "`check-a`", "`check-b`"):
            self.assertIn(value, merged)

        replaced = run(
            self.project,
            "--replace-principles",
            "--replace-approval-boundaries",
            "--replace-routes",
            "--replace-check-commands",
        )
        self.assertEqual(replaced.returncode, 0, replaced.stderr)
        content = (self.project / "AGENTS.md").read_text(encoding="utf-8")
        for value in ("- A", "- B", "- Boundary A", "- Boundary B", "docs/product.md", "docs/security.md", "`check-a`", "`check-b`"):
            self.assertNotIn(value, content)

    def test_project_briefing_persists_and_can_be_refined(self) -> None:
        first = run(
            self.project,
            "--project-summary", "로컬 문서를 정리하고 검색하는 앱이다.",
            "--principle", "사용자 문서는 로컬에 유지한다.",
            "--done-condition", "변경 범위의 자동 테스트가 통과한다.",
        )
        self.assertEqual(first.returncode, 0, first.stderr)

        second = run(self.project)
        self.assertEqual(second.returncode, 0, second.stderr)
        content = (self.project / "AGENTS.md").read_text(encoding="utf-8")
        self.assertIn("### 프로젝트 목적", content)
        self.assertIn("로컬 문서를 정리하고 검색하는 앱이다.", content)
        self.assertIn("사용자 문서는 로컬에 유지한다.", content)
        self.assertIn("변경 범위의 자동 테스트가 통과한다.", content)

        refined = run(
            self.project,
            "--project-summary", "로컬 문서를 팀별로 정리하고 검색하는 앱이다.",
            "--replace-done-conditions",
            "--done-condition", "자동 테스트와 관련 사용자 흐름 확인이 통과한다.",
        )
        self.assertEqual(refined.returncode, 0, refined.stderr)
        updated = (self.project / "AGENTS.md").read_text(encoding="utf-8")
        self.assertNotIn("로컬 문서를 정리하고 검색하는 앱이다.", updated)
        self.assertIn("로컬 문서를 팀별로 정리하고 검색하는 앱이다.", updated)
        self.assertNotIn("변경 범위의 자동 테스트가 통과한다.", updated)
        self.assertIn("자동 테스트와 관련 사용자 흐름 확인이 통과한다.", updated)

    def test_replace_unmanaged_keeps_only_reviewed_womc_content(self) -> None:
        (self.project / "AGENTS.md").write_text("# Old implementation diary\n\nFinished ticket 42.\n", encoding="utf-8")

        result = run(self.project, "--replace-unmanaged", "--principle", "Stable principle")

        self.assertEqual(result.returncode, 0, result.stderr)
        content = (self.project / "AGENTS.md").read_text(encoding="utf-8")
        self.assertNotIn("implementation diary", content)
        self.assertNotIn("ticket 42", content)
        self.assertIn("Stable principle", content)

    def test_workspace_structure_produces_scoped_routes_and_checks(self) -> None:
        (self.project / "package.json").write_text(
            '{"private":true,"packageManager":"pnpm@10.0.0","workspaces":["apps/*"]}\n', encoding="utf-8"
        )
        web = self.project / "apps" / "web"
        web.mkdir(parents=True)
        (web / "package.json").write_text(
            '{"scripts":{"test":"node --test","build":"node --check index.js"}}\n',
            encoding="utf-8",
        )

        result = run(self.project)

        self.assertEqual(result.returncode, 0, result.stderr)
        content = (self.project / "AGENTS.md").read_text(encoding="utf-8")
        self.assertIn("`apps/web/` 아래 변경", content)
        self.assertIn("`(cd apps/web && pnpm run test)`", content)
        self.assertIn("`(cd apps/web && pnpm run build)`", content)

    @unittest.skipUnless(sys.platform.startswith("linux"), "Linux-specific development command priority")
    def test_linux_specific_dev_command_is_preferred(self) -> None:
        (self.project / "package.json").write_text(
            '{"scripts":{"dev":"node app.js","dev:linux":"node linux.js"}}\n', encoding="utf-8"
        )
        result = run(self.project)
        self.assertEqual(result.returncode, 0, result.stderr)
        content = (self.project / "AGENTS.md").read_text(encoding="utf-8")
        self.assertIn("`npm run dev:linux`로 앱을 시작", content)
        self.assertNotIn("`npm run dev`로 앱을 시작", content)

    def test_workspace_outside_root_is_ignored_and_space_is_shell_quoted(self) -> None:
        outside = self.project.parent / f"{self.project.name}-outside-workspace"
        outside.mkdir(exist_ok=True)
        self.addCleanup(shutil.rmtree, outside, True)
        (outside / "package.json").write_text('{"scripts":{"test":"node --test"}}\n', encoding="utf-8")
        (self.project / "package.json").write_text(
            f'{{"workspaces":["../{outside.name}","apps/*"]}}\n', encoding="utf-8"
        )
        spaced = self.project / "apps" / "web app"
        spaced.mkdir(parents=True)
        (spaced / "package.json").write_text('{"scripts":{"test":"node --test"}}\n', encoding="utf-8")

        result = run(self.project)

        self.assertEqual(result.returncode, 0, result.stderr)
        content = (self.project / "AGENTS.md").read_text(encoding="utf-8")
        self.assertNotIn("outside-workspace", content)
        self.assertIn("(cd 'apps/web app' && npm run test)", content)

    def test_untrusted_package_manager_name_is_not_emitted(self) -> None:
        (self.project / "package.json").write_text(
            '{"packageManager":"evil-command@1","scripts":{"test":"node --test"}}\n', encoding="utf-8"
        )

        result = run(self.project)

        self.assertEqual(result.returncode, 0, result.stderr)
        content = (self.project / "AGENTS.md").read_text(encoding="utf-8")
        self.assertNotIn("evil-command", content)
        self.assertIn("`npm run test`", content)

    def test_refresh_moves_legacy_managed_block_to_the_top(self) -> None:
        agents = self.project / "AGENTS.md"
        agents.write_text(
            "# User rules\n\nKeep this.\n\n"
            f"{START}\n## WOMC project harness\n{END}\n",
            encoding="utf-8",
        )

        result = run(self.project)

        self.assertEqual(result.returncode, 0, result.stderr)
        content = agents.read_text(encoding="utf-8")
        self.assertEqual(content.splitlines()[0], PHILOSOPHY)
        self.assertEqual(content.count(PHILOSOPHY), 1)
        self.assertIn("# User rules\n\nKeep this.", content)


if __name__ == "__main__":
    unittest.main()
