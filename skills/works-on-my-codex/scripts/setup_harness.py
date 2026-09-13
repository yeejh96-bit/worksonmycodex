#!/usr/bin/env python3
"""Create or refresh the WOMC-managed block in a project's root AGENTS.md."""

from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import sys
import tempfile
from pathlib import Path
from typing import Iterable

START = "<!-- womc:project-harness:start -->"
END = "<!-- womc:project-harness:end -->"
SKELETON_VERSION = "1.0.0"
VERSION_MARKER = f"<!-- womc:skeleton-version={SKELETON_VERSION} -->"
MANUAL_ROUTE_MARKER = "<!-- womc:manual-route -->"
PHILOSOPHY = (
    "> **WOMC 철학:** 사람은 원하는 것과 되돌릴 수 없는 결정만 맡고, 나머지는 모델이 맡는다. "
    "AGENTS.md에는 변하지 않는 제품 원칙, 보안·승인 경계, 작업별 문서·스킬 경로, 공통 검증 방법만 둔다."
)
DEFAULT_APPROVAL_BOUNDARIES = (
    "비밀 정보 열람·노출, 데이터 삭제, 운영 데이터 변경, 실제 결제, 배포, 외부 서비스 변경, 원격 저장소 변경 전에는 명시적 승인을 받는다.",
    "되돌릴 수 있는 일반 프로젝트 수정과 안전한 로컬 검증은 별도 승인 없이 진행할 수 있다.",
)


class HarnessError(Exception):
    pass


def read_utf8(path: Path) -> str:
    try:
        return path.read_bytes().decode("utf-8")
    except UnicodeDecodeError as exc:
        raise HarnessError(f"cannot safely merge non-UTF-8 file: {path}") from exc


def json_file(path: Path) -> dict:
    try:
        value = json.loads(read_utf8(path))
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError, HarnessError):
        return {}


def relative_files(root: Path, patterns: Iterable[str], limit: int = 40) -> list[str]:
    found: list[str] = []
    for pattern in patterns:
        for path in sorted(root.glob(pattern)):
            if path.is_file() and not any(part in {".git", "node_modules", "vendor"} for part in path.parts):
                relative = path.relative_to(root).as_posix()
                if relative not in found:
                    found.append(relative)
                if len(found) >= limit:
                    return found
    return found


def existing_docs(root: Path) -> list[str]:
    candidates = [
        "README.md",
        "README.rst",
        "README.txt",
        "CONTRIBUTING.md",
        "DEVELOPING.md",
        "ARCHITECTURE.md",
        "SECURITY.md",
        "docs/README.md",
        "docs/architecture.md",
        "docs/product.md",
        "docs/requirements.md",
        "docs/security.md",
        "docs/testing.md",
        "docs/deployment.md",
    ]
    fixed = [item for item in candidates if (root / item).is_file()]
    durable_tokens = (
        "readme", "product", "requirement", "spec", "architecture", "design", "adr",
        "security", "auth", "privacy", "threat", "test", "contribut",
        "api", "integration", "deploy", "release", "runbook",
        "제품", "요구", "아키텍처", "설계", "보안", "인증", "개인정보", "테스트", "기여", "연동", "배포", "릴리스",
    )
    transient_tokens = (
        "/archive/", "changelog", "meeting", "minutes", "implementation-log", "progress", "history", "journal",
        "변경기록", "회의록", "구현일지", "진행상황", "작업일지",
    )
    discovered = [
        item for item in relative_files(root, ("docs/**/*.md",), limit=60)
        if any(token in item.lower() for token in durable_tokens)
        and not any(token in item.lower() for token in transient_tokens)
    ]
    return list(dict.fromkeys(fixed + discovered))[:24]


def existing_skills(root: Path) -> list[str]:
    return relative_files(
        root,
        (
            ".codex/skills/*/SKILL.md",
            ".agents/skills/*/SKILL.md",
            "skills/*/SKILL.md",
        ),
        limit=24,
    )


def package_manager(root: Path, fallback: str | None = None) -> str | None:
    package = json_file(root / "package.json")
    declared = package.get("packageManager")
    allowed = {"npm", "pnpm", "yarn", "bun"}
    if isinstance(declared, str) and declared:
        selected = declared.split("@", 1)[0]
        if selected in allowed:
            return selected
    for filename, manager in (
        ("pnpm-lock.yaml", "pnpm"),
        ("yarn.lock", "yarn"),
        ("bun.lockb", "bun"),
        ("bun.lock", "bun"),
        ("package-lock.json", "npm"),
        ("npm-shrinkwrap.json", "npm"),
    ):
        if (root / filename).exists():
            return manager
    return fallback if fallback and (root / "package.json").is_file() else (
        "npm" if (root / "package.json").is_file() else None
    )


def node_command(manager: str, script: str) -> str:
    if manager == "yarn":
        return f"yarn {script}"
    if manager == "bun":
        return f"bun run {script}"
    return f"{manager} run {script}"


def pyproject_text(root: Path) -> str:
    path = root / "pyproject.toml"
    return read_utf8(path).lower() if path.is_file() else ""


def project_areas(root: Path) -> list[Path]:
    """Return manifest-backed subprojects whose paths make scoped checks meaningful."""
    candidates: list[Path] = []
    package = json_file(root / "package.json")
    workspaces = package.get("workspaces", [])
    if isinstance(workspaces, dict):
        workspaces = workspaces.get("packages", [])
    if isinstance(workspaces, list):
        for pattern in workspaces:
            if isinstance(pattern, str) and not Path(pattern).is_absolute() and ".." not in Path(pattern).parts:
                candidates.extend(path for path in sorted(root.glob(pattern)) if path.is_dir())
    for container in ("apps", "packages", "services"):
        base = root / container
        if base.is_dir():
            candidates.extend(path for path in sorted(base.iterdir()) if path.is_dir())

    manifests = ("package.json", "pyproject.toml", "Cargo.toml", "go.mod")
    unique: list[Path] = []
    resolved_root = root.resolve()
    for candidate in candidates:
        resolved = candidate.resolve()
        if not resolved.is_relative_to(resolved_root):
            continue
        relative = resolved.relative_to(resolved_root).as_posix()
        if any(character in relative for character in ("`", "\n", "\r")):
            continue
        if resolved != resolved_root and any((resolved / name).is_file() for name in manifests) and resolved not in unique:
            unique.append(resolved)
        if len(unique) >= 24:
            break
    return unique


def detect_one(
    root: Path,
    command_root: Path,
    label_prefix: str = "",
    manager_fallback: str | None = None,
) -> tuple[list[tuple[str, str]], str | None]:
    commands: list[tuple[str, str]] = []
    dev_command: str | None = None
    manager = package_manager(root, manager_fallback)

    package_path = root / "package.json"
    if package_path.is_file():
        package = json_file(package_path)
        scripts = package.get("scripts", {}) if isinstance(package.get("scripts", {}), dict) else {}
        if manager is None:
            return commands, dev_command
        for label, names in (
            ("린트", ("lint",)),
            ("타입 검사", ("typecheck", "type-check", "check:types")),
            ("테스트", ("test",)),
            ("빌드", ("build",)),
            ("브라우저", ("test:e2e", "e2e", "test:browser")),
        ):
            selected = next((name for name in names if name in scripts), None)
            if selected:
                commands.append((label_prefix + label, node_command(manager, selected)))
        dev_names = ("dev:linux", "dev", "start", "serve") if sys.platform.startswith("linux") else ("dev", "start", "serve")
        for name in dev_names:
            if name in scripts:
                dev_command = node_command(manager, name)
                break

    pyproject = pyproject_text(root)
    if pyproject or (root / "requirements.txt").is_file() or (root / "setup.py").is_file():
        prefix = "uv run " if (root / "uv.lock").is_file() else "python -m "
        if "ruff" in pyproject:
            commands.append((label_prefix + "린트", prefix + "ruff check ."))
        if "mypy" in pyproject:
            commands.append((label_prefix + "타입 검사", prefix + "mypy ."))
        if "pytest" in pyproject or (root / "pytest.ini").is_file() or (root / "tests").is_dir():
            commands.append((label_prefix + "테스트", prefix + "pytest"))

    if (root / "Cargo.toml").is_file():
        commands.extend((
            (label_prefix + "포맷", "cargo fmt --check"),
            (label_prefix + "테스트", "cargo test"),
            (label_prefix + "빌드", "cargo build"),
        ))
    if (root / "go.mod").is_file():
        commands.extend(((label_prefix + "테스트", "go test ./..."), (label_prefix + "빌드", "go build ./...")))

    if root != command_root:
        relative = root.relative_to(command_root).as_posix()
        quoted_relative = shlex.quote(relative)
        commands = [(label, f"(cd {quoted_relative} && {command})") for label, command in commands]
        if dev_command:
            dev_command = f"(cd {quoted_relative} && {dev_command})"

    unique: list[tuple[str, str]] = []
    seen = set()
    for item in commands:
        if item not in seen:
            seen.add(item)
            unique.append(item)
    return unique, dev_command


def detect(root: Path) -> tuple[list[tuple[str, str]], list[str]]:
    commands, root_dev = detect_one(root, root)
    dev_commands = [root_dev] if root_dev else []
    root_manager = package_manager(root)
    for area in project_areas(root):
        relative = area.relative_to(root).as_posix()
        scoped, dev = detect_one(area, root, f"{relative} ", root_manager)
        commands.extend(scoped)
        if dev:
            dev_commands.append(dev)
    return list(dict.fromkeys(commands)), list(dict.fromkeys(dev_commands))


def route_lines(root: Path) -> list[str]:
    docs = existing_docs(root)
    skills = existing_skills(root)
    routes: list[str] = []

    categories = (
        ("제품 또는 요구사항 작업", ("product", "requirement", "spec", "roadmap", "제품", "요구")),
        ("아키텍처 또는 구현 구조 작업", ("architecture", "design", "adr", "아키텍처", "설계")),
        ("보안, 인증 또는 개인정보 작업", ("security", "auth", "privacy", "threat", "보안", "인증", "개인정보")),
        ("테스트 또는 기여 절차 변경", ("test", "contribut", "테스트", "기여")),
        ("API 또는 연동 작업", ("api", "integration", "연동")),
        ("릴리스 또는 배포 작업", ("deploy", "release", "runbook", "배포", "릴리스")),
    )
    assigned: set[str] = set()
    for label, tokens in categories:
        matches = [doc for doc in docs if any(token in doc.lower() for token in tokens)]
        if matches:
            routes.append(f"- {label}: {', '.join(f'`{item}`' for item in matches)} 문서를 읽는다.")
            assigned.update(matches)
    general = [doc for doc in docs if doc not in assigned]
    if general:
        routes.append(f"- 프로젝트 맥락 또는 동작 변경: {', '.join(f'`{item}`' for item in general)} 문서를 읽는다.")
    for skill in skills:
        name = Path(skill).parent.name
        routes.append(f"- `{name}` 스킬에 해당하는 작업: `{skill}` 파일을 읽고 따른다.")
    for area in project_areas(root):
        relative = area.relative_to(root).as_posix()
        manifest = next(
            name for name in ("package.json", "pyproject.toml", "Cargo.toml", "go.mod") if (area / name).is_file()
        )
        routes.append(f"- `{relative}/` 아래 변경: `{relative}/{manifest}`를 확인하고 해당 영역의 범위별 검증을 사용한다.")
    return routes


def bullet_lines(values: Iterable[str]) -> list[str]:
    return [f"- {value.strip()}" for value in values if value.strip()]


def make_block(
    root: Path,
    principles: list[str],
    approval_boundaries: list[str],
    manual_routes: list[str],
    check_commands: list[str],
) -> str:
    commands, dev_commands = detect(root)
    for command in check_commands:
        if not any(existing_command == command for _, existing_command in commands):
            commands.append(("프로젝트 검증", command))
    lines = [
        PHILOSOPHY,
        VERSION_MARKER,
        START,
        "## WOMC 프로젝트 하네스",
    ]

    if principles:
        lines.extend(["", "### 변하지 않는 제품 원칙"])
        lines.extend(bullet_lines(principles))

    lines.extend([
        "",
        "### 보안·승인 경계",
    ])
    lines.extend(bullet_lines(DEFAULT_APPROVAL_BOUNDARIES))
    lines.extend(bullet_lines(approval_boundaries))

    routes = route_lines(root)
    manual_route_lines: list[str] = []
    for route in manual_routes:
        manual_route_lines.append(f"- {route.strip()} {MANUAL_ROUTE_MARKER}")
    routes = manual_route_lines + routes
    if routes:
        lines.extend(["", "### 작업별 문서·스킬 경로"])
        lines.extend(routes)

    if commands or dev_commands:
        lines.extend(["", "### 공통 검증 방법"])
    if commands:
        lines.append("- 변경 범위에 해당하는 프로젝트 검증을 실행한다:")
        lines.extend(f"  - `{command}` ({label})" for label, command in commands)
        lines.append("- 검증 명령이 성공 종료해야 통과로 본다. 실행할 수 없다면 구체적인 방해 요인을 보고하고 통과했다고 표현하지 않는다.")

    for dev_command in dev_commands:
        lines.extend([
            f"- 해당 영역의 웹 변경은 `{dev_command}`로 앱을 시작하고 변경된 흐름과 관련 시각 상태를 브라우저에서 확인한다.",
            "- 기존 브라우저/E2E 도구를 우선 사용한다. 작업에 명확히 필요할 때만 브라우저 의존성을 추가한다.",
        ])
    lines.extend([END, ""])
    return "\n".join(lines)


def merge(existing: str, block: str, replace_unmanaged: bool = False) -> str:
    starts = existing.count(START)
    ends = existing.count(END)
    if starts != ends or starts > 1:
        raise HarnessError(
            f"marker conflict: expected zero or one complete WOMC block, found {starts} start and {ends} end marker(s)"
        )
    newline = "\r\n" if "\r\n" in existing else "\n"
    rendered = block.replace("\n", newline)
    if starts == 1:
        pattern = re.compile(re.escape(START) + r".*?" + re.escape(END) + r"(?:\r?\n)?", re.DOTALL)
        remaining = pattern.sub("", existing, count=1)
        # Migrate the philosophy line from older/current blocks while keeping WOMC content at the top.
        remaining = re.sub(r"^> \*\*WOMC (?:philosophy|철학):.*\r?\n?", "", remaining, count=1)
        remaining = re.sub(r"^<!-- womc:skeleton-version=[^>]+ -->\r?\n?", "", remaining, count=1)
        remaining = remaining.lstrip("\r\n")
        return rendered if replace_unmanaged or not remaining else rendered + newline + remaining
    if not existing:
        return rendered
    return rendered if replace_unmanaged else rendered + newline + existing.lstrip("\r\n")


def persisted_bullets(existing: str, heading: str) -> list[str]:
    """Read only previously typed WOMC fields; detected routes and checks are always rebuilt."""
    if existing.count(START) != 1 or existing.count(END) != 1:
        return []
    managed = existing.split(START, 1)[1].split(END, 1)[0]
    lines = managed.splitlines()
    try:
        start = lines.index(f"### {heading}") + 1
    except ValueError:
        return []
    values: list[str] = []
    for line in lines[start:]:
        if line.startswith("### "):
            break
        if line.startswith("- "):
            values.append(line[2:].strip())
    return values


def persisted_project_checks(existing: str) -> list[str]:
    if existing.count(START) != 1 or existing.count(END) != 1:
        return []
    managed = existing.split(START, 1)[1].split(END, 1)[0]
    return re.findall(r"^  - `(.+)` \((?:project check|프로젝트 검증)\)$", managed, re.MULTILINE)


def persisted_manual_routes(existing: str) -> list[str]:
    if existing.count(START) != 1 or existing.count(END) != 1:
        return []
    managed = existing.split(START, 1)[1].split(END, 1)[0]
    suffix = f" {MANUAL_ROUTE_MARKER}"
    return [
        line[2:-len(suffix)].strip()
        for line in managed.splitlines()
        if line.startswith("- ") and line.endswith(suffix)
    ]


def atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=".AGENTS.md.womc.", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(content.encode("utf-8"))
        os.replace(temp_name, path)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", default=".", help="Project root (default: current directory)")
    parser.add_argument("--principle", action="append", default=[], help="Invariant product principle; repeatable")
    parser.add_argument(
        "--approval-boundary",
        action="append",
        default=[],
        help="Additional durable security or approval boundary; repeatable",
    )
    parser.add_argument("--replace-principles", action="store_true", help="Replace stored principles instead of merging")
    parser.add_argument("--replace-approval-boundaries", action="store_true", help="Replace stored custom approval boundaries instead of merging")
    parser.add_argument("--replace-check-commands", action="store_true", help="Replace stored explicit check commands instead of merging")
    parser.add_argument("--route", action="append", default=[], help="Durable task-to-document or skill route; repeatable")
    parser.add_argument("--replace-routes", action="store_true", help="Replace stored manual routes instead of merging")
    parser.add_argument(
        "--replace-unmanaged",
        action="store_true",
        help="Discard content outside the WOMC block after it has been reviewed and migrated",
    )
    parser.add_argument(
        "--check-command",
        action="append",
        default=[],
        help="Exact safe local validation command established by project files or the user; repeatable",
    )
    parser.add_argument("--dry-run", action="store_true", help="Print the proposed managed block without writing")
    parser.add_argument("--check", action="store_true", help="Exit 0 when AGENTS.md is current, 1 when it would change")
    return parser.parse_args()


def validate_text_inputs(args: argparse.Namespace) -> None:
    values = list(args.principle)
    values.extend(args.approval_boundary)
    values.extend(args.route)
    values.extend(args.check_command)
    for value in values:
        if not value.strip():
            raise HarnessError("principles, approval boundaries, routes, and check commands must not be empty")
        if "\n" in value or "\r" in value:
            raise HarnessError("principles, approval boundaries, routes, and check commands must be single-line values")
        if any(marker in value for marker in (START, END, VERSION_MARKER, MANUAL_ROUTE_MARKER)):
            raise HarnessError("WOMC marker text is not allowed in generated values")


def main() -> int:
    args = parse_args()
    root = Path(args.project).expanduser().resolve()
    if not root.is_dir():
        print(f"WOMC error: project is not a directory: {root}", file=sys.stderr)
        return 2
    try:
        validate_text_inputs(args)
        override = root / "AGENTS.override.md"
        if override.is_file() and read_utf8(override).strip():
            raise HarnessError(
                "non-empty AGENTS.override.md takes precedence over root AGENTS.md; "
                "review and resolve that conflict before installing the root-only WOMC harness"
            )
        target = root / "AGENTS.md"
        existing = read_utf8(target) if target.exists() else ""
        old_principles = persisted_bullets(existing, "변하지 않는 제품 원칙") or persisted_bullets(existing, "Invariant product principles")
        persisted_boundaries = [
            value
            for value in (
                persisted_bullets(existing, "보안·승인 경계")
                or persisted_bullets(existing, "Security and approval boundaries")
            )
            if value not in DEFAULT_APPROVAL_BOUNDARIES and not value.startswith("Get explicit approval before") and not value.startswith("Routine reversible project edits")
        ]
        old_checks = persisted_project_checks(existing)
        old_routes = persisted_manual_routes(existing)
        principles = list(dict.fromkeys(args.principle if args.replace_principles else old_principles + args.principle))
        approval_boundaries = list(dict.fromkeys(
            args.approval_boundary
            if args.replace_approval_boundaries
            else persisted_boundaries + args.approval_boundary
        ))
        check_commands = list(dict.fromkeys(
            args.check_command if args.replace_check_commands else old_checks + args.check_command
        ))
        manual_routes = list(dict.fromkeys(
            args.route if args.replace_routes else old_routes + args.route
        ))
        block = make_block(root, principles, approval_boundaries, manual_routes, check_commands)
        updated = merge(existing, block, args.replace_unmanaged)
    except (OSError, HarnessError) as exc:
        print(f"WOMC error: {exc}", file=sys.stderr)
        return 2

    changed = updated != existing
    if not detect(root)[0] and not check_commands:
        print(
            "WOMC note: no validation command was detected; pass each command established by "
            "project documentation or CI with --check-command.",
            file=sys.stderr,
        )
    if args.dry_run:
        print(block, end="")
        print(
            f"WOMC dry-run: {target.name} would be {'updated' if target.exists() else 'created'}."
            if changed else f"WOMC dry-run: {target.name} is current.",
            file=sys.stderr,
        )
        return 0
    if args.check:
        print(
            f"WOMC check: {target.name} is current."
            if not changed else f"WOMC check: {target.name} would change."
        )
        return 0 if not changed else 1
    if not changed:
        print(f"WOMC: {target.name} unchanged.")
        return 0
    atomic_write(target, updated)
    merge_note = (
        "content outside the managed block was replaced after review."
        if args.replace_unmanaged
        else "content outside the managed block was preserved."
    )
    print(f"WOMC: {target.name} {'updated' if existing else 'created'}; {merge_note}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
