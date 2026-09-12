#!/usr/bin/env python3
"""Create or refresh the WOMC-managed block in a project's root AGENTS.md."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Iterable

START = "<!-- womc:project-harness:start -->"
END = "<!-- womc:project-harness:end -->"
SKIP_NAMES = {
    ".git",
    ".hg",
    ".svn",
    ".DS_Store",
    ".idea",
    ".vscode",
    "AGENTS.md",
    "AGENTS.override.md",
    "node_modules",
    "dist",
    "build",
    "coverage",
    "__pycache__",
    ".venv",
    "venv",
}
SECRET_NAMES = {
    ".env",
    ".env.local",
    ".env.development",
    ".env.production",
    ".env.test",
    "credentials.json",
    "secrets.json",
}


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


def meaningful_entries(root: Path) -> list[Path]:
    entries = []
    for path in root.iterdir():
        if path.name in SKIP_NAMES or path.name in SECRET_NAMES or path.name.startswith(".env."):
            continue
        entries.append(path)
    return sorted(entries, key=lambda p: p.name.lower())


def existing_docs(root: Path) -> list[str]:
    candidates = [
        "README.md",
        "README.rst",
        "README.txt",
        "CONTRIBUTING.md",
        "DEVELOPING.md",
        "docs/README.md",
        "docs/architecture.md",
        "docs/product.md",
        "docs/requirements.md",
    ]
    return [item for item in candidates if (root / item).is_file()]


def dependency_names(package: dict) -> set[str]:
    names: set[str] = set()
    for key in ("dependencies", "devDependencies", "peerDependencies", "optionalDependencies"):
        value = package.get(key, {})
        if isinstance(value, dict):
            names.update(str(name).lower() for name in value)
    return names


def package_manager(root: Path) -> str | None:
    package = json_file(root / "package.json")
    declared = package.get("packageManager")
    if isinstance(declared, str) and declared:
        return declared.split("@", 1)[0]
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
    return "npm" if (root / "package.json").is_file() else None


def node_command(manager: str, script: str) -> str:
    if manager == "yarn":
        return f"yarn {script}"
    if manager == "bun":
        return f"bun run {script}"
    return f"{manager} run {script}"


def pyproject_text(root: Path) -> str:
    path = root / "pyproject.toml"
    return read_utf8(path).lower() if path.is_file() else ""


def detect(root: Path) -> tuple[list[str], str | None, list[tuple[str, str]], str | None]:
    stacks: list[str] = []
    commands: list[tuple[str, str]] = []
    dev_command: str | None = None
    manager = package_manager(root)

    package_path = root / "package.json"
    if package_path.is_file():
        package = json_file(package_path)
        deps = dependency_names(package)
        scripts = package.get("scripts", {}) if isinstance(package.get("scripts", {}), dict) else {}
        framework_map = (
            ("next", "Next.js"),
            ("nuxt", "Nuxt"),
            ("@sveltejs/kit", "SvelteKit"),
            ("vite", "Vite"),
            ("react", "React"),
            ("vue", "Vue"),
            ("express", "Express"),
        )
        frameworks = [label for name, label in framework_map if name in deps]
        stacks.append("JavaScript/TypeScript" + (f" ({', '.join(frameworks)})" if frameworks else ""))
        assert manager is not None
        for label, names in (
            ("lint", ("lint",)),
            ("typecheck", ("typecheck", "type-check", "check:types")),
            ("test", ("test",)),
            ("build", ("build",)),
            ("browser", ("test:e2e", "e2e", "test:browser")),
        ):
            selected = next((name for name in names if name in scripts), None)
            if selected:
                commands.append((label, node_command(manager, selected)))
        for name in ("dev", "start", "serve"):
            if name in scripts:
                dev_command = node_command(manager, name)
                break

    pyproject = pyproject_text(root)
    if pyproject or (root / "requirements.txt").is_file() or (root / "setup.py").is_file():
        stacks.append("Python")
        prefix = "uv run " if (root / "uv.lock").is_file() else "python -m "
        if "ruff" in pyproject:
            commands.append(("lint", prefix + "ruff check ."))
        if "mypy" in pyproject:
            commands.append(("typecheck", prefix + "mypy ."))
        if "pytest" in pyproject or (root / "pytest.ini").is_file() or (root / "tests").is_dir():
            commands.append(("test", prefix + "pytest"))

    if (root / "Cargo.toml").is_file():
        stacks.append("Rust")
        commands.extend((
            ("format", "cargo fmt --check"),
            ("test", "cargo test"),
            ("build", "cargo build"),
        ))
    if (root / "go.mod").is_file():
        stacks.append("Go")
        commands.extend((("test", "go test ./..."), ("build", "go build ./...")))

    unique: list[tuple[str, str]] = []
    seen = set()
    for item in commands:
        if item not in seen:
            seen.add(item)
            unique.append(item)
    return stacks or ["Not detected"], manager, unique, dev_command


def git_summary(root: Path, managed_name: str) -> str:
    try:
        probe = subprocess.run(
            ["git", "-C", str(root), "status", "--short", "--", ".", f":(exclude){managed_name}"],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired):
        return "Git status unavailable"
    if probe.returncode != 0:
        return "Not a Git repository"
    count = len([line for line in probe.stdout.splitlines() if line.strip()])
    return "Clean" if count == 0 else f"Preserve {count} existing changed/untracked path(s)"


def bullet_lines(values: Iterable[str], fallback: str) -> list[str]:
    items = [value.strip() for value in values if value.strip()]
    return [f"- {item}" for item in items] or [f"- {fallback}"]


def make_block(
    root: Path,
    purpose: str | None,
    guardrails: list[str],
    done: list[str],
    managed_name: str,
) -> str:
    is_empty = not meaningful_entries(root)
    stacks, manager, commands, dev_command = detect(root)
    docs = existing_docs(root)
    project_kind = "Empty starter repository" if is_empty else "Existing project"
    purpose_text = purpose.strip() if purpose and purpose.strip() else (
        "Product purpose has not been supplied yet; get it from the user's next task."
        if is_empty else
        "Infer the current product behavior from the code and linked project documents; ask only when a product decision is missing."
    )

    lines = [
        START,
        "## WOMC project harness",
        "",
        "### Project context",
        f"- Purpose: {purpose_text}",
        f"- State: {project_kind}",
        f"- Stack: {', '.join(stacks)}",
        f"- Package manager: {manager or 'Not detected'}",
        f"- Git: {git_summary(root, managed_name)}",
    ]
    if docs:
        lines.append(f"- Read when relevant: {', '.join(f'`{item}`' for item in docs)}")

    lines.extend([
        "",
        "### Guardrails",
        "- Preserve existing files, local conventions, and user changes; stay within the requested scope.",
        "- Routine project edits and local lint, typecheck, test, build, and dev-server runs do not need extra approval.",
        "- Get explicit approval before reading or exposing secrets; deleting data; changing a production database; making a real payment; deploying; changing an external service; or changing a remote repository.",
    ])
    lines.extend(bullet_lines(guardrails, "No additional project-specific guardrails recorded."))

    lines.extend(["", "### Completion criteria"])
    lines.extend(bullet_lines(done, "Meet the task-specific behavior the user requested."))
    if commands:
        lines.append("- Run the applicable project checks:")
        lines.extend(f"  - `{command}` ({label})" for label, command in commands)
    else:
        lines.append("- No project validation command is declared yet; add one only when the project has a real toolchain or runnable check.")

    if dev_command:
        lines.extend([
            f"- For web-facing changes, start the app with `{dev_command}` and verify the changed flow and relevant visual states in a browser.",
            "- Prefer existing browser/E2E tooling. Add a browser dependency only when the task clearly requires it.",
        ])
    lines.append("- Use independent verification for auth, payment, database, deployment, security/privacy, or broad changes; otherwise verify directly.")
    lines.extend([END, ""])
    return "\n".join(lines)


def merge(existing: str, block: str) -> str:
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
        return pattern.sub(rendered, existing, count=1)
    if not existing:
        return rendered
    separator = "" if existing.endswith(("\n", "\r")) else newline
    return existing + separator + newline + rendered


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
    parser.add_argument("--purpose", help="Stable product purpose to record")
    parser.add_argument("--guardrail", action="append", default=[], help="Additional durable guardrail; repeatable")
    parser.add_argument("--done", action="append", default=[], help="Additional durable completion criterion; repeatable")
    parser.add_argument("--dry-run", action="store_true", help="Print the proposed managed block without writing")
    parser.add_argument("--check", action="store_true", help="Exit 0 when AGENTS.md is current, 1 when it would change")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = Path(args.project).expanduser().resolve()
    if not root.is_dir():
        print(f"WOMC error: project is not a directory: {root}", file=sys.stderr)
        return 2
    try:
        override = root / "AGENTS.override.md"
        override_text = read_utf8(override) if override.is_file() else ""
        target = override if override_text.strip() else root / "AGENTS.md"
        existing = override_text if target == override else (read_utf8(target) if target.exists() else "")
        block = make_block(root, args.purpose, args.guardrail, args.done, target.name)
        updated = merge(existing, block)
    except (OSError, HarnessError) as exc:
        print(f"WOMC error: {exc}", file=sys.stderr)
        return 2

    changed = updated != existing
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
    print(
        f"WOMC: {target.name} {'updated' if existing else 'created'}; "
        "content outside the managed block was preserved."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
