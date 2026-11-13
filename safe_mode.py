"""AI에 diff를 보내기 전에 민감정보를 가리는 모듈 (--safe-mode)"""
import re

MASK = "[MASKED]"

# (규칙 이름, 패턴, 바꿀 문자열)
# 순서가 중요하다: 대입문 규칙이 먼저 값을 통째로 가려야
# 그 안의 sk-... key를 API key 규칙이 한 번 더 세지 않는다.
# r"..." : raw 문자열로 \를 특수문자로 처리하지 않고 글자 그대로 봅니다.

_RULES = [
  (
    "비밀값 대입",
    # API_KEY = "abc123"에서 이름과 = 는 남기고 값만 가린다.
    re.compile(r"(?i)((?:api_?key|secret|token|password)\w*\s*[:=]\s*['\"]?)[^'\"\s]+"),
    r"\1" + MASK,
  ),
  (
    "API Key",
    # 대표적인 키 모양: OpenAI/Anthropic(sk-), Github(ghp_), AWS(AKIA)
    re.compile(r"sk-[A-Za-z0-9_-]{20,}|ghp_[A-Za-z0-9]{36}|AKIA[0-9A-Z]{16}"),
    MASK,
  ),
  (
    "이메일",
    re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+"),
    MASK,
  ),
]

def mask_secrets(text: str) -> tuple[str, int]:
    """민감정보를 가린 텍스트와 가린 개수를 돌려준다."""
    total = 0
    for _name, pattern, replacement in _RULES:
      text, count = pattern.subn(replacement, text)
      total += count
    return text, total

MAX_FILES = 10
MAX_LINES = 200

def _split_by_file(diff: str) -> list[str]:
    """diff 전체를 파일 단위 덩어리로 나눈다."""
    chunks = []
    # keepends=True: 줄바꿈을 살려 둬야 나중에 "".join으로 원래 모양대로 붙일 수 있다.
    for line in diff.splitlines(keepends=True):
      # 첫 줄이 "diff --git"이 아닌 경우에도 chunks[-1]에서 오류가 나지 않게 새 덩어리를 연다.
      if line.startswith("diff --git ") or not chunks:
        chunks.append(line)
      else:
        chunks[-1] += line
    return chunks

def limit_diff(
    diff: str, max_files: int = MAX_FILES, max_lines: int = MAX_LINES) -> tuple[str, bool]:
    """diff를 앞에서부터 max_files개 파일, max_lines줄까지만 남긴다. (결과, 잘렸는지)"""
    chunks = _split_by_file(diff)
    lines = "".join(chunks[:max_files]).splitlines(keepends=True)
    truncated = len(chunks) > max_files or len(lines) > max_lines
    limited = "".join(lines[:max_lines])
    if truncated:
      # AI가 "이게 전부"라고 오해하지 않도록 생략 사실을 알려준다.
      limited += "\n... (safe-mode: 일부 diff 생략)\n"
    return limited, truncated
