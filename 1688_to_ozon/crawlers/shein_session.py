from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from playwright.async_api import BrowserContext, Page, Playwright, async_playwright

from config import (
    BROWSER_HEADLESS,
    BROWSER_LOCALE,
    BROWSER_VIEWPORT_CHOICES,
    DEFAULT_TIMEOUT,
    SHEIN_PROFILE_DIR,
    ensure_directories,
)
from utils import logger as logger_module


SHEIN_HOME_URL = "https://www.shein.com.vn"
SHEIN_LOGIN_URL = "https://www.shein.com.vn/user/auth/login?redirection=%2Fuser%2Forders%2Flist%3Ffrom%3DnavTop"
SHEIN_LOCALE = "vi-VN"
VERIFICATION_WAIT_TIMEOUT_MS = 30 * 60 * 1000
VERIFICATION_POLL_INTERVAL_MS = 1500


def get_logger() -> logging.Logger:
    for factory_name in ("get_logger", "setup_logger", "build_logger", "create_logger"):
        factory = getattr(logger_module, factory_name, None)
        if callable(factory):
            try:
                return factory("crawlers.shein_session")
            except TypeError:
                try:
                    return factory()
                except TypeError:
                    continue

    logger = logging.getLogger("crawlers.shein_session")
    if not logger.handlers:
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        )
    logger.setLevel(logging.INFO)
    return logger


LOGGER = get_logger()


def resolve_profile_dir(profile_dir: str | Path | None = None) -> Path:
    if profile_dir in (None, ""):
        return SHEIN_PROFILE_DIR
    return Path(profile_dir)


def choose_viewport() -> dict[str, int]:
    viewport = BROWSER_VIEWPORT_CHOICES[0] if BROWSER_VIEWPORT_CHOICES else {"width": 1366, "height": 768}
    return {
        "width": int(viewport.get("width", 1366)),
        "height": int(viewport.get("height", 768)),
    }


async def install_anti_detection(context: BrowserContext) -> None:
    await context.add_init_script(
        """
        Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
        Object.defineProperty(navigator, 'platform', { get: () => 'Win32' });
        Object.defineProperty(navigator, 'languages', { get: () => ['vi-VN', 'vi', 'en-US', 'en'] });
        Object.defineProperty(navigator, 'plugins', {
          get: () => [
            { name: 'Chrome PDF Plugin' },
            { name: 'Chrome PDF Viewer' },
            { name: 'Native Client' }
          ]
        });
        window.chrome = window.chrome || { runtime: {} };
        const originalQuery = window.navigator.permissions && window.navigator.permissions.query;
        if (originalQuery) {
          window.navigator.permissions.query = (parameters) => (
            parameters && parameters.name === 'notifications'
              ? Promise.resolve({ state: Notification.permission })
              : originalQuery(parameters)
          );
        }
        """
    )


async def is_shein_verification_page(page: Page) -> bool:
    """Detect common SHEIN captcha / anti-bot challenge pages."""
    try:
        current_url = str(page.url or "").lower()
    except Exception:
        current_url = ""

    if any(
        token in current_url
        for token in (
            "captcha",
            "verify",
            "challenge",
            "security",
            "risk",
        )
    ):
        return True

    try:
        body_text = await page.evaluate(
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
            "verify",
            "verification",
            "security check",
            "unusual traffic",
            "slide to verify",
            "drag the slider",
            "complete the puzzle",
            "please verify",
            "xác minh",
            "mã xác minh",
        )
    )


async def wait_for_manual_verification_async(page: Page, reason: str = "") -> None:
    """Pause SHEIN flow until manual captcha/challenge is fully cleared."""
    message = "SHEIN dang yeu cau captcha/xac minh."
    if reason:
        message = f"{message} Context: {reason}."
    LOGGER.warning("%s Hay xu ly trong browser dang mo.", message)
    LOGGER.warning("Pipeline se tu dong cho tiep sau khi captcha bien mat.")

    deadline = asyncio.get_running_loop().time() + (VERIFICATION_WAIT_TIMEOUT_MS / 1000)
    while asyncio.get_running_loop().time() < deadline:
        try:
            if not await is_shein_verification_page(page):
                LOGGER.info("Captcha/xac minh SHEIN da duoc xu ly, tiep tuc pipeline.")
                await page.wait_for_timeout(1000)
                return
        except Exception as exc:
            LOGGER.debug("SHEIN verification polling hit a transient error: %s", exc)
        await page.wait_for_timeout(VERIFICATION_POLL_INTERVAL_MS)

    raise RuntimeError(
        "Captcha/xac minh SHEIN van chua duoc xu ly sau thoi gian cho. "
        "Hay giai captcha trong browser roi chay lai neu can."
    )


async def launch_shein_persistent_context_async(
    profile_dir: str | Path | None = None,
) -> tuple[Playwright, BrowserContext, Page]:
    ensure_directories()
    resolved_profile_dir = resolve_profile_dir(profile_dir)
    resolved_profile_dir.mkdir(parents=True, exist_ok=True)

    LOGGER.info("Launching SHEIN persistent context with profile=%s", resolved_profile_dir)
    playwright = await async_playwright().start()
    context = await playwright.chromium.launch_persistent_context(
        user_data_dir=str(resolved_profile_dir),
        channel="msedge",
        headless=BROWSER_HEADLESS,
        locale=SHEIN_LOCALE or BROWSER_LOCALE,
        viewport=choose_viewport(),
        args=[
            "--disable-blink-features=AutomationControlled",
            "--lang=vi-VN",
        ],
    )
    context.set_default_timeout(DEFAULT_TIMEOUT)
    await install_anti_detection(context)

    page = context.pages[0] if context.pages else await context.new_page()
    return playwright, context, page


async def save_shein_session_async(profile_dir: str | Path | None = None) -> str:
    playwright = None
    context = None
    try:
        playwright, context, page = await launch_shein_persistent_context_async(profile_dir=profile_dir)
        LOGGER.info("Opening SHEIN login page for manual login/captcha handling")
        try:
            await page.goto(SHEIN_LOGIN_URL, wait_until="domcontentloaded", timeout=DEFAULT_TIMEOUT)
        except Exception as exc:
            LOGGER.warning("Could not open SHEIN login page directly, falling back to homepage: %s", exc)
            await page.goto(SHEIN_HOME_URL, wait_until="domcontentloaded", timeout=DEFAULT_TIMEOUT)
        input("Hoan tat login/captcha tren browser SHEIN roi nhan Enter de luu profile...")
        LOGGER.info("Saved SHEIN persistent profile to %s", resolve_profile_dir(profile_dir))
        return str(resolve_profile_dir(profile_dir))
    finally:
        if context is not None:
            await context.close()
        if playwright is not None:
            await playwright.stop()


def save_shein_session(profile_dir: str | Path | None = None) -> str:
    return asyncio.run(save_shein_session_async(profile_dir=profile_dir))
