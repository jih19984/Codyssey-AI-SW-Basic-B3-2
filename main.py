"""git 변경 사항으로 커밋 메시지 / PR 초안을 만드는 CLI 진입점.

사용법:
    python main.py commit [--safe-mode] [--model M] [--temperature T] [--max-tokens N]
    python main.py pr     [--safe-mode] [--model M] [--temperature T] [--max-tokens N]
"""
import argparse
import sys

from ai_client import AIError, chat, get_api_key
from git_collector import GitError, collect_changes
from prompts import build_commit_prompt, build_pr_prompt
from safe_mode import MAX_FILES, MAX_LINES, limit_diff, mask_secrets
from validator import check_commit, check_pr

DEFAULT_MODEL = "gpt-5-mini"
DEFAULT_TEMPERATURE = 1.0
# 추론형 모델은 답을 쓰기 전에 생각하는 데도 토큰을 쓰므로 넉넉히 잡는다.
DEFAULT_MAX_TOKENS = 2000

LINE = "=" * 60
THIN = "-" * 60

def _parse_args() -> argparse.Namespace:
    # 공통 옵션을 부모 파서에 두면 "main.py commit --safe-mode"처럼 명령 뒤에 옵션을 쓸 수 있다.
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--model", default=DEFAULT_MODEL, help=f"사용할 모델 (기본값: {DEFAULT_MODEL})")
    common.add_argument("--temperature", type=float, default=DEFAULT_TEMPERATURE,
                        help=f"생성 다양성 0~2 (기본값: {DEFAULT_TEMPERATURE})")
    common.add_argument("--max-tokens", type=int, default=DEFAULT_MAX_TOKENS,
                        help=f"응답 최대 토큰 수 (기본값: {DEFAULT_MAX_TOKENS})")
    common.add_argument("--safe-mode", action="store_true",
                        help=f"민감정보 마스킹 + diff를 최대 {MAX_FILES}개 파일 / {MAX_LINES}줄로 제한")

    parser = argparse.ArgumentParser(description="git diff로 커밋 메시지 / PR 초안을 생성합니다.")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("commit", parents=[common], help="커밋 메시지 초안 생성")
    sub.add_parser("pr", parents=[common], help="PR 제목/본문 초안 생성")
    return parser.parse_args()

def _section(title: str, content: str) -> None:
    print(LINE)
    print(f" {title}")
    print(LINE)
    print(content)

def main() -> int:
    args = _parse_args()

    try:
        changes = collect_changes()
    except GitError as e:
        print(f"[오류] {e}", file=sys.stderr)
        return 1

    if not changes.files and not changes.diff.strip():
        print("변경 사항이 없습니다.")
        return 0

    # 요청을 보내기 전에 키를 확인해야 "호출 0회"인 실패를 1회로 잘못 세지 않는다.
    try:
        get_api_key()
    except AIError as e:
        print(f"[오류] {e}", file=sys.stderr)
        return 1

    diff = changes.diff
    if args.safe_mode:
        diff, masked = mask_secrets(diff)
        diff, truncated = limit_diff(diff)
        print(f"[safe-mode] 민감정보 {masked}건 마스킹, diff 생략 여부: {'예' if truncated else '아니오'}")

    build = build_commit_prompt if args.command == "commit" else build_pr_prompt
    system, user = build(changes.files, diff)

    call_count = 0
    try:
        call_count += 1
        answer = chat(system, user, args.model, args.temperature, args.max_tokens)
    except AIError as e:
        print(f"[오류] {e}", file=sys.stderr)
        return 1
    finally:
        # 실패해도 요청은 나갔을 수 있으므로 비용 추적을 위해 항상 남긴다.
        print(f"[로그] AI API 호출 횟수: {call_count}회 (model={args.model}, "
              f"temperature={args.temperature}, max_tokens={args.max_tokens})")

    if args.command == "commit":
        message, warnings = check_commit(answer)
        _section("커밋 메시지 초안", message)
    else:
        title, body, warnings = check_pr(answer)
        _section("PR 제목", title)
        _section("PR 본문", body)

    print(THIN)
    if warnings:
        print("[검증] 규칙에 맞게 후처리한 항목:")
        for warning in warnings:
            print(f"  - {warning}")
    else:
        print("[검증] 형식 규칙을 모두 통과했습니다.")
    print(THIN)
    print("※ 초안입니다. 내용을 확인한 뒤 직접 커밋/PR에 사용하세요.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
