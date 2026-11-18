"""AI API를 REST로 호출하는 모듈."""
import os

import requests

API_URL = "https://copa.codyssey.kr/v1/chat/completions"
API_KEY_ENV = "AI_API_KEY"

# 응답이 안 오면 CLI가 끝없이 멈춰 있으므로 상한을 둔다.
TIMEOUT_SECONDS = 60

class AIError(Exception):
    """AI API 호출 실패 원인을 담아 올리는 예외."""

def get_api_key() -> str:
    # 키는 코드나 파일에 두지 않고 환경변수로만 받는다. (미션 요구사항)
    key = os.environ.get(API_KEY_ENV, "").strip()
    if not key:
        raise AIError(f"환경변수 {API_KEY_ENV}가 없습니다. export {API_KEY_ENV}=<키>로 설정하세요.")
    return key

def chat(system: str, user: str, model: str, temperature: float, max_tokens: int) -> str:
    """system/user 프롬프트를 보내고 AI가 생성한 텍스트를 돌려준다."""
    headers = {"Authorization": f"Bearer {get_api_key()}"}
    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    try:
        response = requests.post(API_URL, headers=headers, json=body, timeout=TIMEOUT_SECONDS)
    except requests.Timeout as e:
        raise AIError(f"AI API가 {TIMEOUT_SECONDS}초 안에 응답하지 않았습니다.") from e
    except requests.RequestException as e:
        raise AIError(f"AI API에 연결하지 못했습니다: {e}") from e

    if response.status_code != 200:
        # 401(키 오류), 429(한도 초과) 등을 구분할 수 있게 서버 메시지 앞부분을 같이 보여준다.
        raise AIError(f"AI API 오류 (HTTP {response.status_code}): {response.text[:300]}")

    try:
        content = response.json()["choices"][0]["message"]["content"]
    except (ValueError, KeyError, IndexError, TypeError) as e:
        raise AIError(f"AI API 응답 형식이 예상과 다릅니다: {response.text[:300]}") from e

    # 토큰 한도에 걸리면 200인데도 내용이 비어 올 수 있다.
    if not content or not content.strip():
        raise AIError("AI가 빈 응답을 보냈습니다. --max-tokens 값을 늘려 보세요.")
    return content.strip()
