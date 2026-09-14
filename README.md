# Works on My Codex

Works on My Codex(WOMC)는 빈 폴더나 기존 소프트웨어 프로젝트에 얇고 프로젝트에 특화된 Codex 하네스를 만드는 플러그인입니다.

## 철학

사람은 원하는 것과 되돌릴 수 없는 결정만 맡고, 나머지는 모델이 맡는다. 루트 `AGENTS.md`에는 다음 범주만 둔다.

- 자율 실행 원칙
- 프로젝트 브리핑: 목적·제품 원칙·보안 경계·지속적인 완료 기준
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

마켓플레이스 등록과 플러그인 설치는 Codex 설정을 변경한다. 설치 후 새 세션을 열고 `/hooks`에서 WOMC `SessionStart` 훅을 검토해 신뢰한다. 다음 세션부터 훅이 현재 프로젝트의 WOMC 하네스 유무·버전과 프로젝트 드리프트를 읽기 전용으로 검사한다. 플러그인과 `AGENTS.md` 하네스는 하나의 WOMC 버전을 사용하며, 플러그인이 갱신되면 다음 세션에서 하네스도 같은 버전으로 갱신한다. 읽기 경로, 비표준 로컬 스킬, 워크스페이스 또는 검증 명령의 구조가 달라지면 모델이 첫 요청 전에 하네스를 갱신한다. 일반 문서 본문이나 소스 코드 수정만으로는 갱신을 일으키지 않는다. 훅은 프로젝트 파일이나 개인 Codex UI 설정을 직접 수정하지 않고 필요한 하네스 갱신만 모델에게 알린다.

## WOMC 업데이트

Codex에 `이 프로젝트 WOMC를 최신 버전으로 업데이트해 줘.`처럼 실행을 요청하면 `$works-on-my-codex`가 다음 명령을 순서대로 실행한다.

```sh
codex plugin marketplace upgrade works-on-my-codex
codex plugin add works-on-my-codex@works-on-my-codex
```

설치 버전을 확인한 뒤 최신 스킬로 현재 프로젝트의 `AGENTS.md` 하네스까지 갱신한다. 업데이트 방법이나 버전을 질문만 한 경우에는 명령을 실행하지 않는다. WOMC 버전은 날짜나 빌드 번호를 붙이지 않은 `x.x.x` 형식만 사용한다.
두 `codex plugin` 명령은 Windows, macOS, Linux에서 동일하며, 하네스 생성에는 각 환경에서 사용 가능한 Python 실행 파일을 사용한다.

## 사용

Codex에 `이 프로젝트에 $works-on-my-codex를 적용해 줘.`라고 요청한다. WOMC는 저장소의 문서, 로컬 스킬, 매니페스트, 작업 공간 구조를 살펴보고 작업 경로와 공통 검증을 맞춘다. 문서 이름이 회의록·변경 기록·구현 일지인 경우 자동 라우팅에서 제외한다.

포함된 생성기를 직접 실행할 수도 있다.

```sh
python3 skills/works-on-my-codex/scripts/setup_harness.py \
  --project /path/to/project \
  --project-summary "사용자가 로컬 문서를 정리하고 검색하는 앱이다" \
  --principle "사용자 데이터는 기본적으로 로컬에 유지한다" \
  --done-condition "변경 범위의 자동 테스트와 사용자 흐름 확인이 통과한다" \
  --approval-boundary "사용자 데이터를 제3자에게 보내기 전에 승인을 받는다" \
  --route "결제 작업: docs/billing.md를 읽는다" \
  --check-command "make test" \
  --dry-run
```

기존 수동 원칙·완료 기준·승인 경계·작업 경로·검증 명령은 갱신 시 병합된다. 정리할 내용을 모두 검토한 뒤에만 `--replace-principles`, `--replace-done-conditions`, `--replace-approval-boundaries`, `--replace-routes`, `--replace-check-commands`, `--replace-unmanaged`를 사용한다.

## 파일과 동작

- WOMC 철학과 하네스는 루트 `AGENTS.md`에만 관리한다.
- 루트 `AGENTS.md`가 없으면 만든다.
- 비어 있지 않은 루트 `AGENTS.override.md`가 있으면 이 파일이 `AGENTS.md`를 가리므로 수정을 멈추고 충돌을 보고한다.
- WOMC 철학 문구와 `womc:project-harness` 표시 영역을 맨 위에 둔다.
- 표시가 부분적이거나 중복되면 파일을 쓰지 않는다.
- 관리 영역 밖의 기존 내용은 기본적으로 보존한다. 모델이 위 범주 기준으로 감사·이전한 후에만 `--replace-unmanaged`로 정리한다.
- 갱신할 때마다 정식 문서, 로컬 스킬, 매니페스트, `apps/`·`packages/`·`services/`, JavaScript workspace를 다시 탐색한다.
- 신뢰된 세션 시작 훅은 위 탐색 결과와 현재 하네스를 읽기 전용으로 비교하고, 차이가 있으면 모델이 첫 요청 전에 갱신하도록 알린다.
- Codex가 자동 발견하는 `.codex/skills/`, `.agents/skills/`, 플러그인 `skills/`는 `AGENTS.md`에 설명을 중복하지 않는다. 비표준 경로의 스킬만 짧은 사용 조건과 진입점을 기록한다.
- 읽기 경로·비표준 로컬 스킬·워크스페이스·검증 명령의 구조를 바꾸는 작업은 같은 작업이 끝나기 전에 하네스도 갱신한다.
- 일반 문서 본문 수정은 다음 세션에서 자동 갱신을 유발하지 않는다. 작업 중 새로 알게 된 지속 정보는 현재 작업에서 하네스나 연결 문서에 반영한다.
- 이름만으로 중요도를 알 수 없는 문서도 내용상 전체 구현이나 특정 작업 전에 반드시 읽어야 한다면 전역 또는 작업별 읽기 경로로 기록한다.
- 프로젝트 밖 workspace, 마크다운을 깨뜨리는 경로, 허용되지 않은 패키지 매니저 이름은 지침에 넣지 않는다.
- 특정 하위 경로에만 적용되는 지속 제약이나 검증은 그 경로에 가장 가까운 중첩 `AGENTS.md`에 둔다. 저장소가 크다는 이유만으로 중첩 파일을 만들지 않는다.

## 제거

루트 `AGENTS.md`에서 WOMC 철학 문구, `womc:version` 표식, 완전한 WOMC 관리 영역을 함께 제거한다. 주변의 사용자 작성 내용은 보존한다. 플러그인은 명령의 범위를 검토한 뒤 `codex plugin remove works-on-my-codex@works-on-my-codex`로 제거한다.

## 검증

```sh
python3 -B -m unittest discover -s tests -v
python3 /home/lee/.codex/skills/.system/skill-creator/scripts/quick_validate.py skills/works-on-my-codex
python3 /home/lee/.codex/skills/.system/plugin-creator/scripts/validate_plugin.py .
```

`WOMC_RUN_CODEX_INTEGRATION=1 python3 -B -m unittest tests.test_codex_integration -v`는 읽기 전용 임시 Codex 턴으로 실제 지침 탐색을 검사하며 계정·네트워크를 사용하므로 명시적으로 활성화해야 한다.
