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
