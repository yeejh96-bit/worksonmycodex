> **WOMC 철학:** 사람은 원하는 것과 되돌릴 수 없는 결정만 맡고, 나머지는 모델이 맡는다. AGENTS.md에는 변하지 않는 제품 원칙, 보안·승인 경계, 작업별 문서·스킬 경로, 공통 검증 방법만 둔다.
<!-- womc:skeleton-version=1.0.0 -->
<!-- womc:project-harness:start -->
## WOMC 프로젝트 하네스

### 변하지 않는 제품 원칙
- 프로젝트 관련 설명과 지침 문서는 한국어로 작성한다.

### 보안·승인 경계
- 비밀 정보 열람·노출, 데이터 삭제, 운영 데이터 변경, 실제 결제, 배포, 외부 서비스 변경, 원격 저장소 변경 전에는 명시적 승인을 받는다.
- 되돌릴 수 있는 일반 프로젝트 수정과 안전한 로컬 검증은 별도 승인 없이 진행할 수 있다.

### 작업별 문서·스킬 경로
- 프로젝트 맥락 또는 동작 변경: `README.md` 문서를 읽는다.
- `works-on-my-codex` 스킬에 해당하는 작업: `skills/works-on-my-codex/SKILL.md` 파일을 읽고 따른다.
- `works-on-my-codex-statusline` 스킬에 해당하는 작업: `skills/works-on-my-codex-statusline/SKILL.md` 파일을 읽고 따른다.

### 공통 검증 방법
- 변경 범위에 해당하는 프로젝트 검증을 실행한다:
  - `python3 -B -m unittest discover -s tests -v` (프로젝트 검증)
- 검증 명령이 성공 종료해야 통과로 본다. 실행할 수 없다면 구체적인 방해 요인을 보고하고 통과했다고 표현하지 않는다.
<!-- womc:project-harness:end -->
