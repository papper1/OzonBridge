import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from crawler.session import check_session_valid


def main() -> None:
    """Check whether the saved 1688 session is still valid."""
    try:
        is_valid = check_session_valid()
        if is_valid:
            print("Session 1688 con dung duoc.")
        else:
            print("Session 1688 khong con dung duoc.")
    except Exception as exc:
        print(f"Khong the kiem tra session 1688: {exc}")


if __name__ == "__main__":
    main()
