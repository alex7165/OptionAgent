import json
from pathlib import Path

from playwright.sync_api import sync_playwright


class BrowserClient:

    def __init__(self, headless: bool = False):
        self.headless = headless
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
        self.pages = []

    def start(self):
        self.playwright = sync_playwright().start()

        self.browser = self.playwright.chromium.launch(
            headless=self.headless
        )

        self.context = self.browser.new_context()

        self.page = self.context.new_page()
        self.pages = [self.page]

    def new_tab(self):
        if self.context is None:
            raise RuntimeError(
                "Browser wurde noch nicht gestartet. Erst browser.start() aufrufen."
            )

        self.page = self.context.new_page()
        self.pages.append(self.page)

        return self.page

    def select_tab(self, index: int):
        if not self.pages:
            raise RuntimeError(
                "Browser wurde noch nicht gestartet. Erst browser.start() aufrufen."
            )

        if index < 0 or index >= len(self.pages):
            raise IndexError("Tab-Index existiert nicht.")

        self.page = self.pages[index]

        return self.page

    def current_tab_index(self) -> int:
        if self.page is None:
            raise RuntimeError(
                "Browser wurde noch nicht gestartet. Erst browser.start() aufrufen."
            )

        return self.pages.index(self.page)

    def goto(self, url: str):
        if self.page is None:
            raise RuntimeError(
                "Browser wurde noch nicht gestartet. Erst browser.start() aufrufen."
            )

        self.page.goto(url)

    def get_title(self) -> str:
        if self.page is None:
            raise RuntimeError(
                "Browser wurde noch nicht gestartet. Erst browser.start() aufrufen."
            )

        return self.page.title()

    def get_text(self) -> str:
        if self.page is None:
            raise RuntimeError(
                "Browser wurde noch nicht gestartet. Erst browser.start() aufrufen."
            )

        return self.page.locator("body").inner_text()

    def screenshot(self, path: str):
        if self.page is None:
            raise RuntimeError(
                "Browser wurde noch nicht gestartet. Erst browser.start() aufrufen."
            )

        screenshot_path = Path(path)
        screenshot_path.parent.mkdir(parents=True, exist_ok=True)

        self.page.screenshot(
            path=str(screenshot_path),
            full_page=True
        )

        return screenshot_path

    def save_cookies(self, path: str):
        if self.context is None:
            raise RuntimeError(
                "Browser wurde noch nicht gestartet. Erst browser.start() aufrufen."
            )

        cookie_path = Path(path)
        cookie_path.parent.mkdir(parents=True, exist_ok=True)

        cookies = self.context.cookies()

        with cookie_path.open("w", encoding="utf-8") as file:
            json.dump(cookies, file, indent=2)

        return cookie_path

    def load_cookies(self, path: str):
        if self.context is None:
            raise RuntimeError(
                "Browser wurde noch nicht gestartet. Erst browser.start() aufrufen."
            )

        cookie_path = Path(path)

        with cookie_path.open("r", encoding="utf-8") as file:
            cookies = json.load(file)

        self.context.add_cookies(cookies)

        return cookie_path

    def close(self):
        if self.context:
            self.context.close()

        if self.browser:
            self.browser.close()

        if self.playwright:
            self.playwright.stop()