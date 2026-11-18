# AI 커밋 메시지 / PR 초안 생성기

현재 Git 저장소의 변경 사항(`git status`, `git diff`)을 AI API에 REST로 보내서
**커밋 메시지 초안**과 **PR 제목/본문 초안**을 만들어 주는 Python CLI입니다.

> 초안만 출력합니다. `git commit`, `git push`, PR 생성은 하지 않습니다.

## 설치

Python 3.10 이상이 필요합니다.

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## 환경변수

API Key는 코드나 파일에 적지 않고 **환경변수로만** 받습니다.

| 이름 | 설명 |
|------|------|
| `AI_API_KEY` | Codyssey AI API(`https://copa.codyssey.kr`)에서 발급받은 키 |

```bash
export AI_API_KEY=<발급받은 키>     # Windows PowerShell: $env:AI_API_KEY="<키>"
```

## 사용법

반드시 **Git 프로젝트 루트 디렉토리**에서 실행합니다.

```bash
python main.py commit                  # 커밋 메시지 초안
python main.py pr                      # PR 제목/본문 초안
python main.py commit --safe-mode      # 민감정보 마스킹 + diff 크기 제한 후 전송
python main.py pr --model gpt-5-mini --temperature 1.0 --max-tokens 3000
```

| 옵션 | 기본값 | 설명 |
|------|--------|------|
| `--model` | `gpt-5-mini` | 사용할 모델 |
| `--temperature` | `1.0` | 생성 다양성 (0~2) |
| `--max-tokens` | `2000` | 응답 최대 토큰 수. 빈 응답 오류가 나면 늘려 주세요 |
| `--safe-mode` | 꺼짐 | API Key·비밀값·이메일을 `[MASKED]`로 가리고, diff를 최대 10개 파일 / 200줄로 자름 |

변경 사항이 없으면 `변경 사항이 없습니다.`를 출력하고 종료합니다.

## 출력 예시

```text
$ python main.py pr --safe-mode
[safe-mode] 민감정보 1건 마스킹, diff 생략 여부: 아니오
[로그] AI API 호출 횟수: 1회 (model=gpt-5-mini, temperature=1.0, max_tokens=2000)
============================================================
 PR 제목
============================================================
feat: AI API 호출과 커밋/PR 초안 CLI 추가
============================================================
 PR 본문
============================================================
## Why
- 변경 사항으로 커밋 메시지와 PR 초안을 자동으로 만들기 위해

## What
- ai_client.py: AI API를 REST로 1회 호출하고 실패 원인을 AIError로 전달
- main.py: commit / pr 명령과 옵션을 처리하는 CLI 추가

## How to Test
- export AI_API_KEY=<키> 후 python main.py commit 실행
------------------------------------------------------------
[검증] 형식 규칙을 모두 통과했습니다.
------------------------------------------------------------
※ 초안입니다. 내용을 확인한 뒤 직접 커밋/PR에 사용하세요.
```

## 생성 규칙과 검증

| 대상 | 규칙 |
|------|------|
| 커밋 제목 | 1줄 필수, 50자 권장, 최대 72자, 끝에 마침표 없음 |
| 커밋 본문 | 선택. 변경 파일을 언급하는 불릿 1~3개 |
| PR 제목 | 최대 80자 |
| PR 본문 | `## Why` / `## What` / `## How to Test` 섹션, 각 섹션에 불릿 1개 이상 |

명령 하나당 API는 **1번만** 호출합니다. 그래서 AI 응답이 규칙을 어겨도 다시 요청하지 않고
후처리로 고칩니다(코드 블록 제거, 제목 자르기, 빠진 섹션 자리표시 추가).
무엇을 고쳤는지는 `[검증]` 항목에 표시됩니다.

## 프로젝트 구조

| 파일 | 역할 |
|------|------|
| `main.py` | CLI 진입점. 옵션 처리, 전체 흐름, 출력 |
| `git_collector.py` | `git status` / `git diff` 수집 |
| `safe_mode.py` | 민감정보 마스킹, diff 크기 제한 |
| `prompts.py` | 커밋 / PR용 프롬프트 생성 |
| `ai_client.py` | AI API REST 호출과 오류 처리 |
| `validator.py` | AI 응답 검증과 후처리 |

## 보안 / 비용 안내

- **diff 내용이 외부 AI 서버로 전송됩니다.** 비밀번호, 키, 개인정보가 들어 있을 수 있는 변경이라면 `--safe-mode`를 쓰세요.
  다만 마스킹은 정규식 기반이라 모든 민감정보를 잡아내지는 못합니다. 전송 전에 diff를 직접 확인하는 것이 가장 안전합니다.
- API Key는 환경변수로만 다루고, `.env` 파일은 `.gitignore`에 포함되어 있습니다. 키를 코드나 커밋에 넣지 마세요.
- 호출마다 입력(diff)과 출력 토큰만큼 비용이 듭니다. diff가 클수록 비용이 커지므로 `--safe-mode`로 크기를 제한할 수 있습니다.
- 실행할 때마다 `[로그] AI API 호출 횟수`가 출력되어 사용량을 확인할 수 있습니다.
- API 실패(키 오류 401, 한도 초과 429, 타임아웃 등) 시 원인이 담긴 메시지를 출력하고 종료 코드 1로 끝납니다.
