#!/usr/bin/env python3
"""Safely set WOMC's Codex TUI status-line items in config.toml."""

from __future__ import annotations

import argparse
import os
import re
import sys
import tempfile
import tomllib
from pathlib import Path

ITEMS = [
    "model-with-reasoning",
    "current-dir",
    "five-hour-limit",
    "weekly-limit",
]
SETTING = "status_line = [" + ", ".join(f'"{item}"' for item in ITEMS) + "]"
TABLE_RE = re.compile(r"^\s*\[([^]]+)]\s*(?:#.*)?$")
KEY_RE = re.compile(r"^(\s*)status_line\s*=\s*(.*?)(\r?\n)?$")
INLINE_TUI_RE = re.compile(r"^\s*tui\s*=", re.MULTILINE)


class ConfigError(Exception):
    pass


def default_config() -> Path:
    codex_home = os.environ.get("CODEX_HOME")
    return Path(codex_home).expanduser() / "config.toml" if codex_home else Path.home() / ".codex" / "config.toml"


def read_config(path: Path) -> str:
    try:
        return path.read_bytes().decode("utf-8") if path.exists() else ""
    except UnicodeDecodeError as exc:
        raise ConfigError(f"cannot safely edit non-UTF-8 config: {path}") from exc


def validate_toml(text: str) -> None:
    try:
        tomllib.loads(text)
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"config.toml is not valid TOML: {exc}") from exc


def section_ranges(lines: list[str]) -> list[tuple[int, int]]:
    headings: list[tuple[int, str]] = []
    for index, line in enumerate(lines):
        match = TABLE_RE.match(line.rstrip("\r\n"))
        if match:
            headings.append((index, match.group(1).strip()))
    tui_starts = [index for index, name in headings if name == "tui"]
    if len(tui_starts) > 1:
        raise ConfigError("multiple [tui] sections are ambiguous")
    if not tui_starts:
        return []
    start = tui_starts[0]
    end = next((index for index, _ in headings if index > start), len(lines))
    return [(start, end)]


def update(text: str) -> str:
    if text:
        validate_toml(text)
    if INLINE_TUI_RE.search(text):
        raise ConfigError("inline 'tui = {...}' tables are not modified automatically; use /statusline")

    newline = "\r\n" if "\r\n" in text else "\n"
    lines = text.splitlines(keepends=True)
    ranges = section_ranges(lines)

    if not ranges:
        prefix = text
        if prefix and not prefix.endswith(("\n", "\r")):
            prefix += newline
        if prefix and not prefix.endswith(newline * 2):
            prefix += newline
        result = prefix + f"[tui]{newline}{SETTING}{newline}"
        validate_toml(result)
        return result

    start, end = ranges[0]
    matches = [(index, KEY_RE.match(lines[index].rstrip("\r\n"))) for index in range(start + 1, end)]
    matches = [(index, match) for index, match in matches if match]
    if len(matches) > 1:
        raise ConfigError("multiple tui.status_line keys are ambiguous")
    if matches:
        index, match = matches[0]
        assert match is not None
        rhs = match.group(2).strip()
        value, separator, comment = rhs.partition("#")
        value = value.rstrip()
        if value.startswith("[") and not value.endswith("]"):
            raise ConfigError("multiline tui.status_line is not modified automatically; use /statusline")
        comment_suffix = f"  #{comment}" if separator else ""
        lines[index] = f"{match.group(1)}{SETTING}{comment_suffix}{newline}"
    else:
        lines.insert(end, SETTING + newline)

    result = "".join(lines)
    validate_toml(result)
    return result


def atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    existing_mode = path.stat().st_mode if path.exists() else None
    fd, temporary = tempfile.mkstemp(prefix=".config.toml.womc.", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(text.encode("utf-8"))
        if existing_mode is not None:
            os.chmod(temporary, existing_mode)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=default_config(), help="Config path for testing")
    parser.add_argument("--apply", action="store_true", help="Write the change; default is preview only")
    parser.add_argument("--check", action="store_true", help="Exit 0 when current, 1 when a change is needed")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    path = args.config.expanduser().resolve()
    try:
        current = read_config(path)
        desired = update(current)
    except (OSError, ConfigError) as exc:
        print(f"WOMC status-line error: {exc}", file=sys.stderr)
        return 2

    changed = current != desired
    print(f"Config: {path}")
    print(f"Status line: {', '.join(ITEMS)}")
    if args.check:
        print("WOMC status line is current." if not changed else "WOMC status line would change.")
        return 0 if not changed else 1
    if not args.apply:
        print("Preview only; rerun with --apply to write." if changed else "No change needed.")
        return 0
    if not changed:
        print("WOMC status line unchanged.")
        return 0
    try:
        atomic_write(path, desired)
    except OSError as exc:
        print(f"WOMC status-line error: {exc}", file=sys.stderr)
        return 2
    print("WOMC status line updated. Start a new Codex session to use it.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
