import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from crawler.session import open_login_browser, save_context_session, wait_for_manual_login


def main() -> None:
    """Open browser for manual 1688 login and save session data."""
    try:
        playwright, browser, context, page = open_login_browser()
        try:
            wait_for_manual_login(page)
            session_path = save_context_session(context)
            print(f"Luu session 1688 thanh cong: {session_path}")
        finally:
            page.close()
            context.close()
            browser.close()
            playwright.stop()
    except Exception as exc:
        print(f"Luu session 1688 that bai: {exc}")


if __name__ == "__main__":
    main()
