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

마켓플레이스 등록과 플러그인 설치는 Codex 설정을 변경한다. WOMC는 세션 시작 훅을 등록하거나 프로젝트를 자동 점검하지 않는다. 설치만으로 프로젝트 루트 `AGENTS.md`가 생성되지는 않으며, 처음 적용할 때 `이 프로젝트에 WOMC를 적용해 줘`라고 요청한다. 이후 `WOMC 업데이트해 줘`라는 자연어 요청 한 번으로 설치본과 현재 프로젝트 하네스를 함께 최신화한다.

## WOMC 업데이트

Codex에 `이 프로젝트 WOMC를 최신 버전으로 업데이트해 줘.`처럼 실행을 요청하면 `$works-on-my-codex`가 다음 명령을 순서대로 실행한다.

```sh
codex plugin marketplace upgrade works-on-my-codex
codex plugin add works-on-my-codex@works-on-my-codex
```

설치 버전을 확인한 뒤 최신 스킬로 현재 프로젝트의 운영 스킬과 확인 가능한 연결 도구를 한 번 감사하고 `AGENTS.md` 하네스를 갱신한다. WOMC 저장소 자체도 같은 감사 대상이다. 기존 프로젝트에서는 이전 WOMC 관리 영역을 새 원칙으로 교체하고, 관리 영역 밖의 사용자 작성 내용은 보존한다. 업데이트 방법이나 버전을 질문만 한 경우에는 명령을 실행하지 않는다. WOMC 버전은 날짜나 빌드 번호를 붙이지 않은 `x.x.x` 형식만 사용한다.
설치본 버전·활성화 상태, 하네스의 `--check` 결과, 실행 중인 세션의 자동 반영 여부는 구분해서 보고한다. 최신 스킬 파일을 직접 읽었다는 이유로 세션의 스킬 목록도 자동 갱신됐다고 판단하지 않는다.
두 `codex plugin` 명령은 Windows, macOS, Linux에서 동일하며, 하네스 생성에는 각 환경에서 사용 가능한 Python 실행 파일을 사용한다.

## 사용

Codex에 `이 프로젝트에 $works-on-my-codex를 적용해 줘.`라고 요청한다. WOMC는 저장소의 문서, 로컬 스킬, 매니페스트, 작업 공간 구조를 살펴보고 작업 경로와 공통 검증을 맞춘다. 문서 이름이 회의록·변경 기록·구현 일지인 경우 자동 라우팅에서 제외한다.

처음 적용·명시적 WOMC 갱신에서는 현재 프로젝트의 [스킬과 연결 도구를 함께 감사](skills/works-on-my-codex/references/project-environment-audit.md)한다. 새 프로젝트는 추가 스킬 없이 시작할 수 있고, 기존 지침으로 충분한 일반 작업 조언은 스킬로 만들지 않는다. 기존 스킬은 근거에 따라 유지·축소·통합·문서 이동·제거 후보로 판단한다. 실제 보이는 MCP·커넥터·플러그인만 점검하고 접근할 수 없는 상태는 확인 불가로 보고한다. 감사만으로 스킬을 삭제하거나 연결을 끄지 않으며, 일회성 결과를 `AGENTS.md`에 쓰지 않는다. 일반 작업의 하네스 동기화에서는 바뀐 항목만 살피고 전체 감사를 반복하지 않는다.

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

생성기는 `AGENTS.md`를 만들며 스킬의 유용성이나 연결 도구의 적합성을 자동 판정하지 않는다. `--check`는 생성 결과가 현재 하네스와 일치하는지만 검사한다. 환경 감사는 적용·업데이트 절차에서 모델이 실제 지침과 확인 가능한 도구 목록을 보고 수행한다.

기존 수동 원칙·완료 기준·승인 경계·작업 경로·검증 명령은 갱신 시 병합된다. 정리할 내용을 모두 검토한 뒤에만 `--replace-principles`, `--replace-done-conditions`, `--replace-approval-boundaries`, `--replace-routes`, `--replace-check-commands`, `--replace-unmanaged`를 사용한다.

## 작업별 서브에이전트 선택

생성·갱신한 하네스에는 [짧은 위임 원칙](skills/works-on-my-codex/assets/delegation-policy.md)만 포함된다. 메인은 분리 가능한 조사·구현·검토의 위임 여부와 현재 환경에 맞는 모델·추론 수준을 판단한다. 짧거나 분리 실익이 없는 작업은 직접 처리하고, 위임 결과의 통합과 최종 검증을 책임진다. 사용자 지정 모델·예산·위임 제한을 우선하며 메인 모델과 `config.toml`은 바꾸지 않는다.

스킬 전달과 검증에 관한 자세한 내용은 위임 정책을 수정하거나 검증할 때만 [위임 참고 문서](skills/works-on-my-codex/references/delegation.md)에서 읽는다. 생성기는 작업을 자동 분류하거나 에이전트를 실행하지 않는다.

## 승인 경계

되돌리기 쉬운 로컬 코드·문서·테스트·안전한 설정 변경은 요청 범위 안에서 자율적으로 진행한다. 금전 비용, 운영 환경이나 외부 사용자에 대한 실제 영향, 사용자 데이터 손실·공개, 자격 증명 노출, 되돌리기 어려운 외부 변경은 실행 전에 명시적 승인을 받는다. 사용자의 구체적인 요청과 Codex 플랫폼·프로젝트의 상위 승인 정책을 함께 따른다.

## 파일과 동작

- WOMC 철학과 하네스는 루트 `AGENTS.md`에만 관리한다.
- 필요한 질문은 지원되는 환경에서 비동기로 전달하고, 답변과 무관한 안전한 작업은 계속한다. 답변·승인이 필요한 작업은 응답을 기다리며 무응답을 동의로 간주하지 않는다.
- 루트 `AGENTS.md`가 없으면 만든다.
- 비어 있지 않은 루트 `AGENTS.override.md`가 있으면 이 파일이 `AGENTS.md`를 가리므로 수정을 멈추고 충돌을 보고한다.
- 맨 위 두 줄에 아래 설명 원칙을 고정하고, 한 줄을 비운 뒤 WOMC 철학 문구와 `womc:project-harness` 표시 영역을 둔다. 기존 하네스 갱신에도 적용하며 반복 실행해도 중복하지 않는다.
  ```text
  나는 코딩을 모른다. 전문 용어는 쉽고 간결하게 설명한다.
  모든 설명·보고는 한국어로 하며, 쉽고 간결하게 한다.
  ```
- 표시가 부분적이거나 중복되면 파일을 쓰지 않는다.
- 관리 영역 밖의 기존 내용은 기본적으로 보존한다. 모델이 위 범주 기준으로 감사·이전한 후에만 `--replace-unmanaged`로 정리한다.
- 갱신할 때마다 정식 문서, 로컬 스킬, 매니페스트, `apps/`·`packages/`·`services/`, JavaScript workspace를 다시 탐색한다.
- WOMC는 세션 시작 훅이나 자동 드리프트 점검을 사용하지 않는다. Codex 밖에서 프로젝트 구조가 바뀌면 `WOMC 업데이트해 줘`라고 요청해 현재 하네스를 다시 맞춘다.
- Codex가 자동 발견하는 `.codex/skills/`, `.agents/skills/`, 플러그인 `skills/`는 `AGENTS.md`에 설명을 중복하지 않는다. 비표준 경로의 스킬만 짧은 사용 조건과 진입점을 기록한다.
- 읽기 경로·비표준 로컬 스킬·워크스페이스·검증 명령의 구조를 바꾸는 작업은 같은 작업이 끝나기 전에 하네스도 갱신한다.
- 일반 문서 본문이나 소스 코드 수정만으로 하네스를 자동 갱신하지 않는다. 작업 중 새로 알게 된 지속 정보는 현재 작업에서 하네스나 연결 문서에 반영한다.
- 이름만으로 중요도를 알 수 없는 문서도 내용상 전체 구현이나 특정 작업 전에 반드시 읽어야 한다면 전역 또는 작업별 읽기 경로로 기록한다.
- 프로젝트 밖 workspace, 마크다운을 깨뜨리는 경로, 허용되지 않은 패키지 매니저 이름은 지침에 넣지 않는다.
- 특정 하위 경로에만 적용되는 지속 제약이나 검증은 그 경로에 가장 가까운 중첩 `AGENTS.md`에 둔다. 저장소가 크다는 이유만으로 중첩 파일을 만들지 않는다.

## 제거

루트 `AGENTS.md`에서 WOMC가 추가한 맨 위 설명 원칙 두 줄, WOMC 철학 문구, `womc:version` 표식, 완전한 WOMC 관리 영역을 함께 제거한다. 주변의 사용자 작성 내용은 보존한다. 플러그인은 명령의 범위를 검토한 뒤 `codex plugin remove works-on-my-codex@works-on-my-codex`로 제거한다.

## 검증

```sh
python3 -B -m unittest discover -s tests -v
python3 /home/lee/.codex/skills/.system/skill-creator/scripts/quick_validate.py skills/works-on-my-codex
python3 /home/lee/.codex/skills/.system/plugin-creator/scripts/validate_plugin.py .
```

`WOMC_RUN_CODEX_INTEGRATION=1 python3 -B -m unittest tests.test_codex_integration -v`는 읽기 전용 임시 Codex 턴으로 실제 지침 탐색을 검사하며 계정·네트워크를 사용하므로 명시적으로 활성화해야 한다.
이 자동 테스트는 새 실행의 지침 탐색만 확인한다. 기존 세션에서 플러그인 갱신이 자동 반영되는지는 별도의 [선택형 수동 통합 검사](skills/works-on-my-codex/references/update-verification.md)로 확인한다.
