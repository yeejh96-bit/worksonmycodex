from __future__ import annotations

import hashlib
import json
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
COMMUNICATION_PREFACE = (
    "나는 코딩을 모른다. 전문 용어는 쉽고 간결하게 설명한다.\n"
    "모든 설명·보고는 한국어로 하며, 쉽고 간결하게 한다.\n\n"
)
PHILOSOPHY = (
    "> **WOMC 철학:** 사람은 원하는 것과 되돌릴 수 없는 결정만 맡고, 나머지는 모델이 맡는다. "
    "AGENTS.md에는 자율 실행 원칙, 프로젝트 목적·지속 제약·완료 기준, 작업별 읽기 경로, 공통 검증 방법만 둔다."
)
PLUGIN_VERSION = json.loads((ROOT / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8"))["version"]
VERSION_MARKER = f"<!-- womc:version={PLUGIN_VERSION} -->"


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
        self.assertTrue(content.startswith(COMMUNICATION_PREFACE + PHILOSOPHY))
        self.assertEqual(content.splitlines()[4], VERSION_MARKER)
        self.assertIn("User notes remain local by default", content)
        self.assertEqual(content.count(START), 1)
        self.assertNotIn("Working contract", content)
        self.assertNotIn("No additional project-specific guardrails", content)
        policy = (SCRIPT.parents[1] / "assets" / "delegation-policy.md").read_text(encoding="utf-8").strip()
        self.assertEqual(content.count(policy), 1)
        before = digest(agents)

        second = run(self.project, "--principle", "User notes remain local by default")
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertIn("unchanged", second.stdout)
        self.assertEqual(digest(agents), before)

    def test_harness_refresh_does_not_persist_audit_findings_or_change_tools(self) -> None:
        skill = self.project / ".agents" / "skills" / "review" / "SKILL.md"
        skill.parent.mkdir(parents=True)
        skill.write_text(
            "---\nname: review\ndescription: 프로젝트 검토에서 사용합니다.\n---\n"
            "# 검토\n모든 작업에 전체 테스트를 실행한다.\n",
            encoding="utf-8",
        )
        connection = self.project / ".codex" / "mcp.toml"
        connection.parent.mkdir(parents=True)
        connection.write_text("[mcp_servers.example]\nenabled = true\n", encoding="utf-8")
        agents = self.project / "AGENTS.md"
        agents.write_text("# 사용자 작성 지침\n이 문장을 보존한다.\n", encoding="utf-8")
        skill_digest, connection_digest = digest(skill), digest(connection)

        self.assertEqual(run(self.project).returncode, 0)
        refreshed = agents.read_text(encoding="utf-8")
        self.assertIn("# 사용자 작성 지침\n이 문장을 보존한다.", refreshed)
        self.assertNotIn("전체 테스트를 실행한다", refreshed)
        self.assertNotIn("제거 후보", refreshed)
        self.assertNotIn("mcp_servers.example", refreshed)
        self.assertEqual(digest(skill), skill_digest)
        self.assertEqual(digest(connection), connection_digest)
        self.assertEqual(run(self.project, "--check").returncode, 0)
        self.assertEqual(run(self.project).returncode, 0)
        self.assertEqual(agents.read_text(encoding="utf-8"), refreshed)

    def test_generated_delegation_policy_is_short_and_keeps_only_durable_principles(self) -> None:
        policy = (SCRIPT.parents[1] / "assets" / "delegation-policy.md").read_text(encoding="utf-8")
        self.assertLessEqual(len(policy.splitlines()), 8)
        for principle in ("조사·구현·검토", "복잡도·위험·검증 난도", "메인이 직접 처리", "최종 검증", "모델·예산·위임 제한"):
            self.assertIn(principle, policy)
        for detail in ("GPT-N", "번호가 가장 높은", "low", "medium", "high", "fallback", "| --- |"):
            self.assertNotIn(detail, policy)

        result = run(self.project)
        self.assertEqual(result.returncode, 0, result.stderr)
        content = (self.project / "AGENTS.md").read_text(encoding="utf-8")
        self.assertEqual(content.count(policy.strip()), 1)
        self.assertNotIn("위임할 때 확인할 점", content)
        self.assertNotIn("GPT-N", content)

    def test_default_approval_boundary_is_based_on_impact_and_reversibility(self) -> None:
        result = run(self.project)
        self.assertEqual(result.returncode, 0, result.stderr)
        content = (self.project / "AGENTS.md").read_text(encoding="utf-8")
        for phrase in ("되돌리기 쉬운 로컬 코드·문서·테스트·안전한 설정 변경", "금전 비용 발생", "운영 환경·외부 사용자", "사용자 데이터 손실·공개", "자격 증명 노출", "되돌리기 어려운 외부 변경", "Codex 플랫폼과 프로젝트의 상위 보안·승인 정책"):
            self.assertIn(phrase, content)
        self.assertNotIn("외부 서비스 변경, 원격 저장소 변경 전", content)

    def test_refresh_replaces_legacy_default_approval_without_losing_custom_rule(self) -> None:
        initial = run(self.project)
        self.assertEqual(initial.returncode, 0, initial.stderr)
        agents = self.project / "AGENTS.md"
        content = agents.read_text(encoding="utf-8")
        start = content.index("### 보안·승인 경계\n")
        end = content.index("\n### 작업별 문서·스킬 경로", start)
        legacy = (
            "### 보안·승인 경계\n"
            "- 비밀 정보 열람·노출, 데이터 삭제, 운영 데이터 변경, 실제 결제, 배포, 외부 서비스 변경, 원격 저장소 변경 전에는 명시적 승인을 받는다.\n"
            "- 되돌릴 수 있는 일반 프로젝트 수정과 안전한 로컬 검증은 별도 승인 없이 진행할 수 있다.\n"
            "- 민감한 고객 기록의 외부 전송은 담당자 승인을 받는다.\n"
        )
        agents.write_text(content[:start] + legacy + content[end:], encoding="utf-8")

        refreshed = run(self.project)
        self.assertEqual(refreshed.returncode, 0, refreshed.stderr)
        updated = agents.read_text(encoding="utf-8")
        self.assertIn("금전 비용 발생", updated)
        self.assertIn("민감한 고객 기록의 외부 전송은 담당자 승인을 받는다.", updated)
        self.assertNotIn("비밀 정보 열람·노출, 데이터 삭제", updated)
        self.assertNotIn("되돌릴 수 있는 일반 프로젝트 수정", updated)
        self.assertEqual(run(self.project, "--check").returncode, 0)
        self.assertEqual(run(self.project).returncode, 0)
        self.assertEqual(agents.read_text(encoding="utf-8"), updated)

    def test_existing_project_refreshes_previous_delegation_policy(self) -> None:
        agents = self.project / "AGENTS.md"
        agents.write_text(
            f"{PHILOSOPHY}\n<!-- womc:version=1.5.2 -->\n{START}\n"
            "### 서브에이전트 위임\n"
            "- 번호가 가장 높은 세대(GPT-N)를 고른다.\n"
            "| 위임 작업 | 추론 수준 |\n| --- | --- |\n| 탐색 | low |\n"
            "### 프로젝트 목적\n기존 프로젝트의 목적을 유지한다.\n"
            "### 보안·승인 경계\n"
            "- 비밀 정보 열람·노출, 데이터 삭제, 운영 데이터 변경, 실제 결제, 배포, 외부 서비스 변경, 원격 저장소 변경 전에는 명시적 승인을 받는다.\n"
            f"{END}\n\n# 사용자 작성 지침\n이 문장을 보존한다.\n",
            encoding="utf-8",
        )

        self.assertEqual(run(self.project, "--check").returncode, 1)
        result = run(self.project)
        self.assertEqual(result.returncode, 0, result.stderr)
        updated = agents.read_text(encoding="utf-8")
        self.assertIn(VERSION_MARKER, updated)
        self.assertIn("분리 가능한 조사·구현·검토는 서브에이전트에 위임할 수 있다.", updated)
        self.assertIn("금전 비용 발생", updated)
        self.assertIn("기존 프로젝트의 목적을 유지한다.", updated)
        self.assertIn("# 사용자 작성 지침\n이 문장을 보존한다.", updated)
        self.assertNotIn("GPT-N", updated)
        self.assertNotIn("위임 작업 | 추론 수준", updated)
        self.assertEqual(run(self.project, "--check").returncode, 0)
        self.assertEqual(run(self.project).returncode, 0)
        self.assertEqual(agents.read_text(encoding="utf-8"), updated)

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
        self.assertTrue(content.startswith(COMMUNICATION_PREFACE + PHILOSOPHY))
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

    def test_delegation_refresh_preserves_user_policy_and_model_settings(self) -> None:
        codex_dir = self.project / ".codex"
        (codex_dir / "agents").mkdir(parents=True)
        config = codex_dir / "config.toml"
        config.write_text(
            'model = "user-selected-model"\nmodel_reasoning_effort = "high"\n'
            '[agents]\nenabled = false\n', encoding="utf-8"
        )
        role = codex_dir / "agents" / "reviewer.toml"
        role.write_text('name = "reviewer"\nmodel = "user-review-model"\n', encoding="utf-8")
        skill = self.project / ".agents" / "skills" / "project-review" / "SKILL.md"
        skill.parent.mkdir(parents=True)
        skill.write_text("---\nname: project-review\ndescription: 문서 검토용\n---\n", encoding="utf-8")
        original_files = {path: digest(path) for path in (config, role, skill)}
        agents = self.project / "AGENTS.md"
        user_content = "# 사용자 규칙\n\nLuna를 쓰지 않는다.\n"
        agents.write_text(
            f"{PHILOSOPHY}\n<!-- womc:version=1.3.1 -->\n{START}\n"
            "### 프로젝트 목적\n기존 프로젝트\n"
            "### 변하지 않는 제품 원칙\n- 서브에이전트는 읽기 전용으로 사용한다.\n"
            "### 지속적인 완료 기준\n- 실제 결과 확인\n"
            "### 보안·승인 경계\n- 외부 전송 승인 필요\n"
            "### 작업별 문서·스킬 경로\n"
            "- 문서 검토: `docs/review.md`를 읽는다. <!-- womc:manual-route -->\n"
            "### 공통 검증 방법\n  - `local-check` (프로젝트 검증)\n"
            f"{END}\n\n{user_content}", encoding="utf-8"
        )
        old_digest = digest(agents)
        preview = run(self.project, "--dry-run")
        self.assertEqual(preview.returncode, 0, preview.stderr)
        self.assertEqual(digest(agents), old_digest)
        self.assertEqual(run(self.project, "--check").returncode, 1)
        self.assertEqual(digest(agents), old_digest)

        result = run(self.project)
        self.assertEqual(result.returncode, 0, result.stderr)
        content = agents.read_text(encoding="utf-8")
        # Verify the shipped policy is embedded once, not just linked to a cache path.
        policy = (SCRIPT.parents[1] / "assets" / "delegation-policy.md").read_text(encoding="utf-8").strip()
        self.assertEqual(content.count(policy), 1)
        for value in ("기존 프로젝트", "서브에이전트는 읽기 전용으로 사용한다.", "실제 결과 확인",
                      "외부 전송 승인 필요", "docs/review.md", "`local-check`"):
            self.assertIn(value, content)
        self.assertTrue(content.endswith(user_content))
        self.assertEqual(run(self.project).returncode, 0)
        self.assertEqual(agents.read_text(encoding="utf-8"), content)
        self.assertEqual(run(self.project, "--check").returncode, 0)
        self.assertEqual({path: digest(path) for path in original_files}, original_files)
        # The harness must not install role files or change user configuration.
        actual_files = {path.relative_to(self.project) for path in self.project.rglob("*")
                        if path.is_file() and ".git" not in path.relative_to(self.project).parts}
        self.assertEqual(actual_files, {Path("AGENTS.md"), *(path.relative_to(self.project) for path in original_files)})

    def test_missing_policy_asset_fails_without_modifying_project(self) -> None:
        # Simulate an incomplete plugin package, not a user project error.
        with tempfile.TemporaryDirectory() as package_name:
            packaged_script = Path(package_name) / "skills" / "works-on-my-codex" / "scripts" / SCRIPT.name
            packaged_script.parent.mkdir(parents=True)
            shutil.copyfile(SCRIPT, packaged_script)
            agents = self.project / "AGENTS.md"
            agents.write_text("# 기존 지침\n", encoding="utf-8")
            before = digest(agents)
            for mode in ([], ["--dry-run"], ["--check"]):
                with self.subTest(mode=mode):
                    result = subprocess.run(
                        [sys.executable, str(packaged_script), "--project", str(self.project), *mode],
                        capture_output=True, text=True, check=False,
                    )
                    self.assertEqual(result.returncode, 2)
                    self.assertIn("delegation-policy.md", result.stderr)
                    self.assertEqual(digest(agents), before)

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
        self.assertNotIn(".codex/skills/release-helper/SKILL.md", content)

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
        self.assertNotIn("다음 설명에 해당하는 작업", content)
        self.assertIn("끝내기 전에 `$works-on-my-codex`", content)

    def test_plugin_skills_are_not_duplicated_in_agents_routes(self) -> None:
        (self.project / ".codex-plugin").mkdir()
        (self.project / ".codex-plugin" / "plugin.json").write_text(
            '{"name":"sample","skills":"./skills/"}\n', encoding="utf-8"
        )
        skill = self.project / "skills" / "release-helper"
        skill.mkdir(parents=True)
        (skill / "SKILL.md").write_text(
            "---\nname: release-helper\ndescription: 릴리스를 준비할 때 사용합니다.\n---\n",
            encoding="utf-8",
        )

        result = run(self.project)

        self.assertEqual(result.returncode, 0, result.stderr)
        content = (self.project / "AGENTS.md").read_text(encoding="utf-8")
        self.assertNotIn("skills/release-helper/SKILL.md", content)

    def test_overlong_skill_description_is_not_copied_into_agents(self) -> None:
        skill = self.project / "skills" / "release-helper"
        skill.mkdir(parents=True)
        description = "A" * 161
        (skill / "SKILL.md").write_text(
            f"---\nname: release-helper\ndescription: {description}\n---\n",
            encoding="utf-8",
        )

        result = run(self.project)

        self.assertEqual(result.returncode, 0, result.stderr)
        content = (self.project / "AGENTS.md").read_text(encoding="utf-8")
        self.assertNotIn(description, content)
        self.assertIn("`release-helper` 스킬 작업", content)

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
        self.assertTrue(content.startswith(COMMUNICATION_PREFACE + PHILOSOPHY))
        self.assertEqual(content.count(PHILOSOPHY), 1)
        self.assertIn("# User rules\n\nKeep this.", content)

    def test_refresh_adds_preface_to_existing_harness_without_duplication(self) -> None:
        agents = self.project / "AGENTS.md"
        user_content = "# 사용자 지침\n\n원래 내용을 보존한다.\n"
        agents.write_text(
            f"{PHILOSOPHY}\n{VERSION_MARKER}\n{START}\n"
            f"### 변하지 않는 제품 원칙\n- 기존 원칙 유지\n{END}\n\n{user_content}",
            encoding="utf-8",
        )
        result = run(self.project)
        self.assertEqual(result.returncode, 0, result.stderr)
        content = agents.read_text(encoding="utf-8")
        self.assertTrue(content.startswith(COMMUNICATION_PREFACE + PHILOSOPHY))
        self.assertEqual(content.count(COMMUNICATION_PREFACE), 1)
        self.assertEqual(content.count(PHILOSOPHY), 1)
        self.assertEqual(content.count(VERSION_MARKER), 1)
        self.assertIn("- 기존 원칙 유지", content)
        self.assertTrue(content.endswith(user_content))
        result = run(self.project)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(agents.read_text(encoding="utf-8"), content)
        self.assertEqual(run(self.project, "--check").returncode, 0)


if __name__ == "__main__":
    unittest.main()
