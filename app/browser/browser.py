from app.browser.cookie_manager import CookieManager

from pathlib import Path

from playwright.sync_api import sync_playwright

from app.browser.interaction import BrowserInteraction
from app.browser.tab_manager import TabManager


class BrowserClient:

    def __init__(self, headless: bool = False):
        self.headless = headless
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
        self.cookies = CookieManager(self._require_context)

        self.tab_manager = TabManager(
            self._require_context,
            self._get_page,
            self._set_page,
        )

        self.interaction = BrowserInteraction(self._require_page)

    @property
    def pages(self):
        return self.tab_manager.pages

    def start(self):
        self.playwright = sync_playwright().start()

        self.browser = self.playwright.chromium.launch(
            headless=self.headless
        )

        self.context = self.browser.new_context()
        self.tab_manager.initialize()

    def new_tab(self):
        return self.tab_manager.new_tab()

    def select_tab(self, index: int):
        return self.tab_manager.select_tab(index)

    def current_tab_index(self) -> int:
        return self.tab_manager.current_tab_index()

    def _require_context(self):
        if self.context is None:
            raise RuntimeError(
                "Browser wurde noch nicht gestartet. Erst browser.start() aufrufen."
            )

        return self.context

    def _require_page(self):
        if self.page is None:
            raise RuntimeError(
                "Browser wurde noch nicht gestartet. Erst browser.start() aufrufen."
            )

        return self.page

    def _get_page(self):
        return self.page

    def _set_page(self, page):
        self.page = page

    def goto(self, url: str):
        page = self._require_page()
        page.goto(url)

    def get_title(self) -> str:
        page = self._require_page()
        return page.title()

    def get_text(self) -> str:
        page = self._require_page()
        return page.locator("body").inner_text()

    def screenshot(self, path: str):
        page = self._require_page()

        screenshot_path = Path(path)
        screenshot_path.parent.mkdir(parents=True, exist_ok=True)

        page.screenshot(
            path=str(screenshot_path),
            full_page=True,
        )

        return screenshot_path

    def click(self, selector: str):
        self.interaction.click(selector)

    def fill(self, selector: str, text: str):
        self.interaction.fill(selector, text)

    def press(self, selector: str, key: str):
        self.interaction.press(selector, key)

    def wait_for(self, selector: str):
        self.interaction.wait_for(selector)

    def save_cookies(self, path: str):
        return self.cookies.save(path)

        cookie_path = Path(path)
        cookie_path.parent.mkdir(parents=True, exist_ok=True)

        cookies = self.context.cookies()

        with cookie_path.open("w", encoding="utf-8") as file:
            json.dump(cookies, file, indent=2)

        return cookie_path

    def load_cookies(self, path: str):
        return self.cookies.load(path)

        cookie_path = Path(path)

        with cookie_path.open("r", encoding="utf-8") as file:
            cookies = json.load(file)

        self.context.add_cookies(cookies)

        return cookie_path

    def close(self):
        if self.context:
            self.context.close()
            self.context = None

        if self.browser:
            self.browser.close()
            self.browser = None

        if self.playwright:
            self.playwright.stop()
            self.playwright = None

        self.page = None