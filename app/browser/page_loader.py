from app.browser.browser import BrowserClient


class PageLoader:

    def __init__(self, headless: bool = True):
        self.headless = headless

    def load_page(self, url: str) -> tuple[str, str]:
    browser = BrowserClient(headless=self.headless)

    browser.start()
    browser.goto(url)

    title = browser.get_title()
    text = browser.get_text()

    browser.close()

    return title, text