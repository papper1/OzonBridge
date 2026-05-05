import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from crawlers.shein_session import save_shein_session


def main() -> None:
    try:
        profile_path = save_shein_session()
        print(f"Luu SHEIN profile thanh cong: {profile_path}")
    except Exception as exc:
        print(f"Luu SHEIN profile that bai: {exc}")


if __name__ == "__main__":
    main()
