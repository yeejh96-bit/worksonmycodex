# Works on My Codex

Works on My Codex(WOMC)는 빈 폴더나 기존 소프트웨어 프로젝트에 얇고 프로젝트에 특화된 Codex 하네스를 만드는 플러그인입니다.

## 철학

사람은 원하는 것과 되돌릴 수 없는 결정만 맡고, 나머지는 모델이 맡는다. 루트 `AGENTS.md`에는 다음 네 범주만 둔다.

- 변하지 않는 제품 원칙
- 보안·승인 경계
- 작업별 문서·스킬 경로
- 공통 검증 방법

현재 작업, 일회성 인수 조건, 구현 이력과 진행 기록은 `AGENTS.md`에 쌓지 않는다. 긴 배경과 근거는 프로젝트의 기존 `docs/` 관례에 맞게 두고, `AGENTS.md`에는 해당 작업에서 읽을 경로만 남긴다.

## 설치

Git 마켓플레이스를 한 번 등록한다.

```sh
codex plugin marketplace add yeejh96-bit/worksonmycodex --ref main
```

그다음 Codex에서 `/plugins`를 열고 `WOMC` 또는 `Works on My Codex`를 검색해 설치한다. CLI에서 바로 설치하려면 다음 명령을 사용한다.

```sh
codex plugin add works-on-my-codex@works-on-my-codex
```

마켓플레이스 등록과 플러그인 설치는 Codex 설정을 변경한다. 설치 후 새 세션을 열고 `/hooks`에서 WOMC `SessionStart` 훅을 검토해 신뢰한다. 다음 세션부터 훅이 상태 표시줄을 한 번 설정하고, 현재 프로젝트의 WOMC 하네스 유무와 버전을 검사한다. 훅은 프로젝트 파일을 직접 수정하지 않고 필요한 설정·갱신만 모델에게 알린다.

## 사용

Codex에 `이 프로젝트에 $works-on-my-codex를 적용해 줘.`라고 요청한다. WOMC는 저장소의 문서, 로컬 스킬, 매니페스트, 작업 공간 구조를 살펴보고 작업 경로와 공통 검증을 맞춘다. 문서 이름이 회의록·변경 기록·구현 일지인 경우 자동 라우팅에서 제외한다.

포함된 생성기를 직접 실행할 수도 있다.

```sh
python3 skills/works-on-my-codex/scripts/setup_harness.py \
  --project /path/to/project \
  --principle "사용자 데이터는 기본적으로 로컬에 유지한다" \
  --approval-boundary "사용자 데이터를 제3자에게 보내기 전에 승인을 받는다" \
  --route "결제 작업: docs/billing.md를 읽는다" \
  --check-command "make test" \
  --dry-run
```

기존 수동 원칙·승인 경계·작업 경로·검증 명령은 갱신 시 병합된다. 정리할 내용을 모두 검토한 뒤에만 `--replace-principles`, `--replace-approval-boundaries`, `--replace-routes`, `--replace-check-commands`, `--replace-unmanaged`를 사용한다.

## 파일과 동작

- WOMC 철학과 하네스는 루트 `AGENTS.md`에만 관리한다.
- 루트 `AGENTS.md`가 없으면 만든다.
- 비어 있지 않은 루트 `AGENTS.override.md`가 있으면 이 파일이 `AGENTS.md`를 가리므로 수정을 멈추고 충돌을 보고한다.
- WOMC 철학 문구와 `womc:project-harness` 표시 영역을 맨 위에 둔다.
- 표시가 부분적이거나 중복되면 파일을 쓰지 않는다.
- 관리 영역 밖의 기존 내용은 기본적으로 보존한다. 모델이 네 범주 기준으로 감사·이전한 후에만 `--replace-unmanaged`로 정리한다.
- 갱신할 때마다 정식 문서, 로컬 스킬, 매니페스트, `apps/`·`packages/`·`services/`, JavaScript workspace를 다시 탐색한다.
- 프로젝트 밖 workspace, 마크다운을 깨뜨리는 경로, 허용되지 않은 패키지 매니저 이름은 지침에 넣지 않는다.
- 중첩 `AGENTS.md`는 하위 트리의 실제 제약이나 명령이 루트와 다른 대규모 저장소에만 검토한다.

## 상태 표시줄

신뢰된 일회성 `SessionStart` 훅이 Codex 기본 상태 표시줄을 다음 순서로 설정한다: 추론 수준을 표시한 모델, 권한 모드, 주간 잔여량, 컨텍스트 잔여량, 프로젝트 폴더. 훅은 관련 없는 설정을 보존하고 이후 사용자 설정을 덮어쓰지 않는다.

## 제거

루트 `AGENTS.md`에서 WOMC 철학 문구, `womc:skeleton-version` 표식, 완전한 WOMC 관리 영역을 함께 제거한다. 주변의 사용자 작성 내용은 보존한다. 플러그인은 명령의 범위를 검토한 뒤 `codex plugin remove works-on-my-codex@works-on-my-codex`로 제거한다.

## 검증

```sh
python3 -B -m unittest discover -s tests -v
python3 /home/lee/.codex/skills/.system/skill-creator/scripts/quick_validate.py skills/works-on-my-codex
python3 /home/lee/.codex/skills/.system/plugin-creator/scripts/validate_plugin.py .
```

`WOMC_RUN_CODEX_INTEGRATION=1 python3 -B -m unittest tests.test_codex_integration -v`는 읽기 전용 임시 Codex 턴으로 실제 지침 탐색을 검사하며 계정·네트워크를 사용하므로 명시적으로 활성화해야 한다.
