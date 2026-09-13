#!/usr/bin/env python3
"""Report a missing, stale, or shadowed WOMC root harness during session start."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

from setup_harness import PHILOSOPHY, SKELETON_VERSION, START

MARKER = re.compile(r"womc:skeleton-version=(\d+\.\d+\.\d+)")


def version_tuple(value: str) -> tuple[int, int, int]:
    return tuple(int(part) for part in value.split("."))  # type: ignore[return-value]


def message(project: Path) -> str | None:
    override = project / "AGENTS.override.md"
    if override.is_file() and override.read_text(encoding="utf-8").strip():
        return (
            "[WOMC] 비어 있지 않은 루트 AGENTS.override.md가 AGENTS.md보다 우선한다. "
            "사용자의 첫 요청을 처리하기 전에 $works-on-my-codex 스킬을 읽고 충돌을 보고한다. "
            "WOMC 철학은 루트 AGENTS.md에만 둔다."
        )

    agents = project / "AGENTS.md"
    try:
        content = agents.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        content = ""
    found = MARKER.search(content)
    if found is None:
        return (
            "[WOMC] 이 프로젝트에 WOMC 하네스가 없다. 사용자의 첫 요청을 처리하기 전에 "
            "$works-on-my-codex 스킬을 읽고 루트 AGENTS.md를 설정한다. 사용자에게 설치 여부를 되묻지 않는다."
        )
    if START not in content or not content.startswith(PHILOSOPHY):
        return (
            "[WOMC] 루트 AGENTS.md의 WOMC 골격이 불완전하다. 사용자의 첫 요청을 처리하기 전에 "
            "$works-on-my-codex 스킬을 읽고 마커 충돌을 확인한 뒤 갱신한다."
        )
    if version_tuple(found.group(1)) < version_tuple(SKELETON_VERSION):
        return (
            f"[WOMC] 프로젝트 골격은 v{found.group(1)}이고 플러그인 골격은 v{SKELETON_VERSION}이다. "
            "사용자의 첫 요청을 처리하기 전에 $works-on-my-codex 스킬을 읽고 루트 AGENTS.md를 갱신한다."
        )
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", default=".", help="Project root (default: current directory)")
    args = parser.parse_args()
    try:
        result = message(Path(args.project).expanduser().resolve())
        if result:
            print(result)
    except Exception:
        # A session hook must never prevent Codex from starting.
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
