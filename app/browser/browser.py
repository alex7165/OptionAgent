from pathlib import Path

from playwright.sync_api import sync_playwright


class BrowserClient:

    def __init__(self, headless: bool = False):
        self.headless = headless
        self.playwright = None
        self.browser = None
        self.page = None
        self.pages = []

    def start(self):
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(headless=self.headless)

        self.page = self.browser.new_page()
        self.pages = [self.page]

    def new_tab(self):
        if self.browser is None:
            raise RuntimeError(
                "Browser wurde noch nicht gestartet. Erst browser.start() aufrufen."
            )

        self.page = self.browser.new_page()
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

        self.page.screenshot(path=str(screenshot_path), full_page=True)

        return screenshot_path

    def close(self):
        if self.browser:
            self.browser.close()

        if self.playwright:
            self.playwright.stop()