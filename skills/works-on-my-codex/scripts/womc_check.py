#!/usr/bin/env python3
"""Report a missing, stale, or shadowed WOMC root harness during session start."""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

from setup_harness import END, PHILOSOPHY, START, WOMC_VERSION

MARKER = re.compile(r"womc:(?:version|skeleton-version)=([0-9A-Za-z][0-9A-Za-z.+-]*)")


def version_tuple(value: str) -> tuple[int, int, int]:
    base = value.split("+", 1)[0].split("-", 1)[0]
    parts = base.split(".")
    if len(parts) != 3 or not all(part.isdigit() for part in parts):
        return (0, 0, 0)
    return tuple(int(part) for part in parts)  # type: ignore[return-value]


def codex_cachebuster(value: str) -> str | None:
    if "+codex." not in value:
        return None
    return value.split("+codex.", 1)[1]


def project_version_is_older(project_version: str, plugin_version: str) -> bool:
    project_base = version_tuple(project_version)
    plugin_base = version_tuple(plugin_version)
    if project_base != plugin_base:
        return project_base < plugin_base
    if project_version == plugin_version:
        return False
    project_build = codex_cachebuster(project_version)
    plugin_build = codex_cachebuster(plugin_version)
    if plugin_build is None:
        return False
    if project_build is None:
        return True
    if project_build.isdigit() and plugin_build.isdigit():
        return project_build < plugin_build
    return project_version != plugin_version


def generated_harness_would_change(project: Path) -> bool:
    """Compare detected routes and checks without writing project files."""
    setup = Path(__file__).with_name("setup_harness.py")
    result = subprocess.run(
        [sys.executable, str(setup), "--project", str(project), "--check"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
        timeout=10,
    )
    return result.returncode == 1


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
    if (
        content.count(START) != 1
        or content.count(END) != 1
        or not content.startswith(PHILOSOPHY)
    ):
        return (
            "[WOMC] 루트 AGENTS.md의 WOMC 골격이 불완전하다. 사용자의 첫 요청을 처리하기 전에 "
            "$works-on-my-codex 스킬을 읽고 마커 충돌을 확인한 뒤 갱신한다."
        )
    found_version = found.group(1)
    if project_version_is_older(found_version, WOMC_VERSION):
        return (
            f"[WOMC] 프로젝트 WOMC는 v{found_version}이고 설치된 WOMC는 v{WOMC_VERSION}이다. "
            "사용자의 첫 요청을 처리하기 전에 $works-on-my-codex 스킬을 읽고 루트 AGENTS.md를 갱신한다."
        )
    if found_version == WOMC_VERSION and generated_harness_would_change(project):
        return (
            "[WOMC] 프로젝트의 시작 문서·로컬 스킬·워크스페이스 또는 검증 명령이 "
            "루트 AGENTS.md의 WOMC 하네스와 달라졌다. 사용자에게 갱신 여부를 되묻지 말고, "
            "첫 요청을 처리하기 전에 $works-on-my-codex 스킬로 하네스를 갱신한다."
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
