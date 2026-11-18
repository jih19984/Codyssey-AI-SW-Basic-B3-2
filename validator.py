"""AI가 만든 커밋 메시지 / PR 초안을 규칙에 맞는지 검사하고 고치는 모듈.

명령당 API 호출은 1회로 제한되므로, 규칙을 어기면 다시 부르지 않고 후처리로 고친다.
고친 내용은 경고 목록으로 돌려줘서 사용자가 무엇이 바뀌었는지 알 수 있게 한다.
"""
import re

COMMIT_TITLE_RECOMMENDED = 50
COMMIT_TITLE_MAX = 72
PR_TITLE_MAX = 80
PR_SECTIONS = ["## Why", "## What", "## How to Test"]
PLACEHOLDER_BULLET = "- (AI가 작성하지 않음: 직접 채워 주세요)"

# 프롬프트에서 금지해도 AI가 ```로 감싸서 보내는 경우가 있다.
_FENCE = re.compile(r"^```[\w-]*\s*\n(.*?)\n```$", re.DOTALL)

def _strip_fence(text: str) -> str:
    text = text.strip()
    match = _FENCE.match(text)
    return match.group(1).strip() if match else text

def _split_title(text: str) -> tuple[str, str]:
    """첫 줄은 제목, 빈 줄 뒤는 본문으로 나눈다."""
    title, _, body = text.partition("\n")
    return title.strip(), body.strip()

def _fix_title(title: str, max_len: int, warnings: list[str]) -> str:
    # AI가 "제목: ..." 같은 머리말이나 마크다운 헤더를 붙이는 경우를 걷어낸다.
    title = re.sub(r"^(#+\s*|(커밋\s*)?제목\s*:\s*|title\s*:\s*)", "", title, flags=re.IGNORECASE)
    if title.endswith("."):
        title = title.rstrip(".")
        warnings.append("제목 끝의 마침표를 제거했습니다.")
    if len(title) > max_len:
        title = title[:max_len].rstrip()
        warnings.append(f"제목이 {max_len}자를 넘어 {max_len}자로 잘랐습니다.")
    return title

def check_commit(text: str) -> tuple[str, list[str]]:
    """커밋 메시지를 검사/후처리해 (고친 메시지, 경고 목록)을 돌려준다."""
    warnings: list[str] = []
    title, body = _split_title(_strip_fence(text))
    title = _fix_title(title, COMMIT_TITLE_MAX, warnings)
    if len(title) > COMMIT_TITLE_RECOMMENDED:
        warnings.append(f"제목이 권장 길이 {COMMIT_TITLE_RECOMMENDED}자를 넘습니다 ({len(title)}자).")
    # 본문은 선택 사항이라 비어 있어도 된다. 있으면 제목과 빈 줄로 구분한다.
    return (f"{title}\n\n{body}" if body else title), warnings

def _section_ranges(body: str) -> dict[str, str]:
    """본문을 "## 헤더" 단위로 잘라 {헤더: 내용}으로 만든다."""
    sections: dict[str, str] = {}
    current = None
    for line in body.splitlines():
        if line.startswith("## "):
            current = line.strip()
            sections[current] = ""
        elif current is not None:
            sections[current] += line + "\n"
    return sections

def check_pr(text: str) -> tuple[str, str, list[str]]:
    """PR 초안을 검사/후처리해 (제목, 본문, 경고 목록)을 돌려준다."""
    warnings: list[str] = []
    title, body = _split_title(_strip_fence(text))
    title = _fix_title(title, PR_TITLE_MAX, warnings)

    sections = _section_ranges(body)
    fixed = []
    # 필수 섹션은 정해진 순서로 다시 조립한다. 빠지거나 불릿이 없으면 자리표시를 넣는다.
    for header in PR_SECTIONS:
        content = sections.get(header, "").strip()
        if header not in sections:
            warnings.append(f"'{header}' 섹션이 없어 자리표시를 추가했습니다.")
        has_bullet = any(line.lstrip().startswith(("- ", "* ")) for line in content.splitlines())
        if not has_bullet:
            if header in sections:
                warnings.append(f"'{header}' 섹션에 불릿이 없어 자리표시를 추가했습니다.")
            content = (content + "\n" + PLACEHOLDER_BULLET).strip()
        fixed.append(f"{header}\n{content}")
    return title, "\n\n".join(fixed), warnings
