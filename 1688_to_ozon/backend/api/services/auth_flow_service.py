from __future__ import annotations

from playwright.sync_api import Browser, BrowserContext, Page, Playwright

from crawler.session import check_session_valid, open_login_browser, save_context_session
from config import SESSION_FILE


class AuthFlowService:
    def __init__(self) -> None:
        self._playwright: Playwright | None = None
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None
        self._page: Page | None = None

    @property
    def flow_active(self) -> bool:
        return self._page is not None and not self._page.is_closed()

    def open_1688_login(self) -> str:
        if self.flow_active:
            return "1688 login browser is already open."

        self.close()
        playwright, browser, context, page = open_login_browser()
        self._playwright = playwright
        self._browser = browser
        self._context = context
        self._page = page
        return "1688 login browser opened. Complete login, then click Save session in the app."

    def save_1688_session(self) -> tuple[bool, str]:
        if self._context is None:
            raise RuntimeError("1688 login browser is not open.")

        session_path = save_context_session(self._context, session_file=str(SESSION_FILE))
        self.close()
        is_valid = check_session_valid(session_file=str(SESSION_FILE))
        return is_valid, session_path

    def close(self) -> None:
        if self._page is not None:
            try:
                self._page.close()
            except Exception:
                pass
        if self._context is not None:
            try:
                self._context.close()
            except Exception:
                pass
        if self._browser is not None:
            try:
                self._browser.close()
            except Exception:
                pass
        if self._playwright is not None:
            try:
                self._playwright.stop()
            except Exception:
                pass

        self._page = None
        self._context = None
        self._browser = None
        self._playwright = None


auth_flow_service = AuthFlowService()
