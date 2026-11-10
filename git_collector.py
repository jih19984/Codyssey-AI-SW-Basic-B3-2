# TMI
# *args: 호출할 때 넘긴 값들을 하나씩 튜플로 모은다.
# subprocess.run(...): 파이썬이 터미널에 명령어를 대신 입력하는 기능
# capture_output=True: 결과를 화면에 바로 찍지 않고 변수로 받아 오기
# raise ... from:  낮은 수준의 오류(FileNotFoundError)를 우리 프로그램의 오류(GitError)로 바꿔 다루기 쉽게 하고, from으로 원래 원인은 잃어버리지 않게 붙여 둔다.
# returncode: 명령이 성공했는지 알려 주는 숫자 (0이면 성공) -> 프로그램이 끝나면서 운영체제에 남기는 숫자 하나를 의미한다.터미널에서 실행되는 모든 프로그램은 반드시 이 숫자를 돌려준다. 0은 정상 종료를 1은 일반적인 상태를 의미한다.
# @dataclass란? 이름으로 꺼낼 수 있는 상자를 간단히 만들 수 있음. r.files, r.diff처럼 이름으로 꺼낼 수 있는 상자로 만듦
# @property란? 계산해서 보여주는 칸. r.diff_line_count를 괄호없이 쓰면 꺼낼 때마다 줄 수를 계산해서 돌려줌

"""git status / git diff 결과를 프로그램 입력으로 바꾸는 모듈."""
from dataclasses import dataclass
from pathlib import Path
import subprocess

class GitError(Exception):
    """Git 명령을 실행할 수 없거나 실패했을 때 발생한다."""

@dataclass
class GitChanges:
    """결과를 담을 상자"""
    files: list[str]
    diff: str

    @property
    def diff_line_count(self) -> int:
        return len(self.diff.splitlines())

def _run_git(*args: str) -> str:
    try:
        result = subprocess.run(
            # quotePath를 꺼야 한글 파일명이 \355\225... 처럼 깨지지 않는다
            ["git", "-c", "core.quotePath=false", *args],
            capture_output=True,
            encoding="utf-8",
            errors="replace",  # 글자가 깨진 파일이 있어도 프로그램이 죽지 않도록
        )
    except FileNotFoundError as error:
        raise GitError("git 명령을 찾을 수 없습니다. Git 설치를 확인하세요.") from error

    # subprocess는 명령이 실패해도 알아서 오류를 내지 않으므로 직접 확인한다
    if result.returncode != 0:
        raise GitError(f"git {args[0]} 실패: {result.stderr.strip()}")
    return result.stdout

def _parse_status(output: str) -> list[str]:
    """status 출력에서 파일 경로만 뽑는다: 상태 3글자 제거, 이름 보존, 따옴표 제거"""
    files = []
    for line in output.splitlines():
        # 맨 앞 공백도 상태표시이므로 strip() 없이 정확히 3글자를 자른다.
        path = line[3:]
        if " -> " in path:
            # 이름 변경은 새 이름만 남긴다.
            path = path.split(" -> ")[-1]
        files.append(path.strip('"'))
    return files

def collect_changes() -> GitChanges:
    # 워크트리에서는 .git이 폴더가 아니라 파일이라서 is_dir()이 아닌 exists()로 확인합니다.
    if not Path(".git").exists():
        raise GitError("Git 프로젝트 루트 디렉토리에서 실행해 주세요.")
    
    # all을 주지 않으면 새 폴더 속 파일들의 "폴더/" 한 줄로 뭉쳐서 나온다
    status = _run_git("status", "--porcelain", "--untracked-files=all")

    staged = _run_git("diff", "--cached", "--no-color")
    # git add까지 한 변경
    unstaged = _run_git("diff", "--no-color")
    # git add 안 한 변경
    return GitChanges(files=_parse_status(status), diff=staged + unstaged)