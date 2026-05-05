import logging
from pathlib import Path
import time

from playwright.sync_api import Browser, BrowserContext, sync_playwright

from config import DEFAULT_TIMEOUT, HEADLESS, SESSION_FILE, ensure_directories
from utils import logger as logger_module


def _get_logger() -> logging.Logger:
    """Return project logger with a safe fallback."""
    for factory_name in ("get_logger", "setup_logger", "build_logger", "create_logger"):
        factory = getattr(logger_module, factory_name, None)
        if callable(factory):
            try:
                return factory("crawler.session")
            except TypeError:
                try:
                    return factory()
                except TypeError:
                    continue

    logger = logging.getLogger("crawler.session")
    if not logger.handlers:
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        )
    logger.setLevel(logging.INFO)
    return logger


LOGGER = _get_logger()

LOGIN_URL = "https://login.1688.com/member/signin.htm?Done=https%3A%2F%2Fwww.1688.com%2F&from=sm"
VERIFICATION_WAIT_TIMEOUT_MS = 30 * 60 * 1000
VERIFICATION_POLL_INTERVAL_MS = 1500
LOGIN_WAIT_TIMEOUT_MS = 30 * 60 * 1000
LOGIN_POLL_INTERVAL_MS = 1500


def _resolve_session_path(session_file: str = "1688_session.json") -> Path:
    """Resolve session path, defaulting to project config when applicable."""
    if session_file == "1688_session.json":
        return SESSION_FILE
    return Path(session_file)


def _is_login_redirect(current_url: str) -> bool:
    """Detect whether the current page points to a login flow."""
    lowered = (current_url or "").lower()
    return any(
        token in lowered
        for token in (
            "login",
            "signin",
            "passport",
            "member.1688.com",
            "auth.1688.com",
        )
    )


def is_verification_page(page) -> bool:
    """Detect common captcha / verification pages on 1688."""
    try:
        current_url = str(page.url or "").lower()
    except Exception:
        current_url = ""

    if any(
        token in current_url
        for token in (
            "captcha",
            "verify",
            "sec.1688.com",
            "nocaptcha",
            "challenge",
        )
    ):
        return True

    try:
        body_text = page.evaluate(
            """
            () => (document.body ? (document.body.innerText || document.body.textContent || "") : "")
            """
        )
    except Exception:
        body_text = ""

    lowered_text = str(body_text or "").lower()
    return any(
        token in lowered_text
        for token in (
            "captcha",
            "verification",
            "verify",
            "slider",
            "slide to verify",
            "please slide to verify",
            "unusual traffic",
            "detected unusual traffic",
            "drag the slider",
            "请完成验证",
            "请先完成验证",
            "安全验证",
            "验证码",
        )
    )


def wait_for_manual_verification(page, reason: str = "") -> None:
    """Pause the pipeline so the user can solve captcha manually in the open browser."""
    message = "1688 dang yeu cau captcha/xac minh."
    if reason:
        message = f"{message} Context: {reason}."
    LOGGER.warning("%s Hay xu ly trong browser dang mo.", message)
    LOGGER.warning(
        "Pipeline se tu dong cho tiep sau khi captcha bien mat. "
        "Khong can nhan Enter trong terminal."
    )

    deadline = time.time() + (VERIFICATION_WAIT_TIMEOUT_MS / 1000)
    while time.time() < deadline:
        try:
            if not is_verification_page(page):
                LOGGER.info("Captcha/xac minh da duoc xu ly, tiep tuc pipeline.")
                page.wait_for_timeout(1000)
                return
        except Exception as exc:
            LOGGER.debug("Verification polling hit a transient error: %s", exc)
        page.wait_for_timeout(VERIFICATION_POLL_INTERVAL_MS)

    raise RuntimeError(
        "Captcha/xac minh van chua duoc xu ly sau thoi gian cho. "
        "Hay giai captcha trong browser roi chay lai neu can."
    )


def open_login_browser():
    """Open a visible browser and navigate to 1688 for manual login."""
    ensure_directories()
    LOGGER.info("Opening browser for manual 1688 login")

    playwright = sync_playwright().start()
    browser = playwright.chromium.launch(headless=False)
    context = browser.new_context()
    page = context.new_page()
    page.set_default_timeout(DEFAULT_TIMEOUT)

    try:
        page.goto(LOGIN_URL, wait_until="domcontentloaded", timeout=DEFAULT_TIMEOUT)
    except Exception as exc:
        LOGGER.warning(
            "Direct login page failed or timed out, trying homepage and keeping browser open: %s",
            exc,
        )
        try:
            page.goto("https://www.1688.com", wait_until="domcontentloaded", timeout=DEFAULT_TIMEOUT)
        except Exception as homepage_exc:
            LOGGER.warning(
                "Homepage load also failed or timed out, browser will stay open for manual login: %s",
                homepage_exc,
            )

    return playwright, browser, context, page


def wait_for_manual_login(page) -> None:
    """Keep the browser open and wait for the user to complete login manually."""
    LOGGER.info("Please log in manually in the opened browser window")
    input("After login is complete, press Enter here to continue...")


def wait_for_login_completion(page) -> None:
    """Wait until the opened browser is no longer on the login flow."""
    LOGGER.info("Please log in manually in the opened browser window")
    LOGGER.info("The session will be saved automatically after login succeeds.")

    deadline = time.time() + (LOGIN_WAIT_TIMEOUT_MS / 1000)
    while time.time() < deadline:
        try:
            current_url = str(page.url or "")
            if not _is_login_redirect(current_url) and not is_verification_page(page):
                LOGGER.info("Detected a logged-in 1688 session.")
                page.wait_for_timeout(1000)
                return
        except Exception as exc:
            LOGGER.debug("Login polling hit a transient error: %s", exc)
        page.wait_for_timeout(LOGIN_POLL_INTERVAL_MS)

    raise RuntimeError(
        "Login was not completed within the allowed time window. "
        "Please finish the 1688 login in the opened browser and try again."
    )


def save_context_session(context: BrowserContext, session_file: str = "1688_session.json") -> str:
    """Save Playwright storage state to the configured session file."""
    session_path = _resolve_session_path(session_file)
    session_path.parent.mkdir(parents=True, exist_ok=True)
    context.storage_state(path=str(session_path))
    LOGGER.info("Session saved successfully to: %s", session_path)
    return str(session_path)


def save_session(session_file: str = "1688_session.json") -> None:
    """Open browser, wait for manual login, then save storage state."""
    session_path = _resolve_session_path(session_file)
    LOGGER.info("Session file will be saved to: %s", session_path)

    playwright, browser, context, page = open_login_browser()

    try:
        wait_for_manual_login(page)
        save_context_session(context, session_file=session_file)
    finally:
        page.close()
        context.close()
        browser.close()
        playwright.stop()


def capture_session_via_browser(session_file: str = "1688_session.json") -> str:
    """Open browser, wait until login succeeds, then save storage state."""
    session_path = _resolve_session_path(session_file)
    LOGGER.info("Session file will be saved to: %s", session_path)

    playwright, browser, context, page = open_login_browser()

    try:
        wait_for_login_completion(page)
        return save_context_session(context, session_file=session_file)
    finally:
        page.close()
        context.close()
        browser.close()
        playwright.stop()


def check_session_valid(session_file: str = "1688_session.json") -> bool:
    """Load storage state and verify the session is not redirected to login."""
    session_path = _resolve_session_path(session_file)
    if not session_path.exists():
        LOGGER.warning("Session file not found: %s", session_path)
        return False

    LOGGER.info("Checking 1688 session from: %s", session_path)

    playwright = sync_playwright().start()
    browser = playwright.chromium.launch(headless=HEADLESS)
    context = browser.new_context(storage_state=str(session_path))
    page = context.new_page()
    page.set_default_timeout(DEFAULT_TIMEOUT)

    try:
        page.goto(
            "https://s.1688.com/selloffer/offer_search.htm?keywords=laptop",
            wait_until="domcontentloaded",
            timeout=DEFAULT_TIMEOUT,
        )
        page.wait_for_timeout(2000)

        current_url = page.url
        if _is_login_redirect(current_url):
            LOGGER.warning("Session invalid. Redirected to login: %s", current_url)
            return False

        LOGGER.info("Session is valid")
        return True
    except Exception as exc:
        LOGGER.exception("Failed to validate session: %s", exc)
        return False
    finally:
        page.close()
        context.close()
        browser.close()
        playwright.stop()


def create_context_with_session(browser: Browser, session_file: str) -> BrowserContext:
    """Create a browser context using saved storage_state when available."""
    session_path = _resolve_session_path(session_file)
    if session_path.exists():
        LOGGER.info("Creating browser context with session: %s", session_path)
        return browser.new_context(storage_state=str(session_path))

    LOGGER.info("Session file not found. Creating browser context without session")
    return browser.new_context()
