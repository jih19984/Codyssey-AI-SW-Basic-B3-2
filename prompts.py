
"""AI에게 보낼 지시문(프롬프트)을 만드는 모듈."""

# 규칙은 매번 같으므로 상수로 둔다. 숫자는 미션의 검증 기준과 일부러 맞췄다.
COMMIT_SYSTEM = """당신은 Git 커밋 메시지를 작성하는 시니어 개발자입니다.
아래 규칙을 반드시 지키세요.

[형식]
- 첫 줄: 커밋 제목 1줄. "타입: 요약" 형태 (타입은 feat, fix, docs, refactor, test, chore 중 하나)
- 제목은 50자 이내 권장, 절대 72자를 넘기지 않는다
- 제목 끝에 마침표를 찍지 않는다
- 둘째 줄: 빈 줄
- 셋째 줄부터: 핵심 변경 사항 1~3개를 "- "로 시작하는 불릿으로 쓴다
- 불릿에는 변경된 파일(모듈) 이름을 1개 이상 언급한다

[내용]
- diff에 실제로 있는 변경만 쓴다. 추측하지 않는다
- 한국어로 쓴다
- [MASKED]는 민감정보를 가린 표시이므로 원래 값을 추측하거나 언급하지 않는다

[출력]
- 커밋 메시지만 출력한다. 설명, 인사말, 코드 블록(```)을 붙이지 않는다
"""


def _format_changes(files: list[str], diff: str) -> str:
    """파일 목록과 diff를 AI가 구분하기 쉽게 제목을 붙여 묶는다."""
    file_list = "\n".join(f"- {path}" for path in files)
    return f"## 변경된 파일 ({len(files)}개)\n{file_list}\n\n## diff\n{diff}"


def build_commit_prompt(files: list[str], diff: str) -> tuple[str, str]:
    """커밋 메시지 생성용 (system, user) 프롬프트를 돌려준다."""
    user = "아래 변경 사항으로 커밋 메시지를 작성해 주세요.\n\n" + _format_changes(files, diff)
    return COMMIT_SYSTEM, user