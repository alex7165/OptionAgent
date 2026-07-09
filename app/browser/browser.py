from app.browser.screenshot_service import ScreenshotService
from app.browser.cookie_manager import CookieManager

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
        self.screenshots = ScreenshotService(self._require_page)

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

    def collect_request_urls(self, url: str) -> list[str]:
        page = self._require_page()
        request_urls = []

        page.on("request", lambda request: request_urls.append(request.url))
        page.goto(url)
        page.wait_for_timeout(5000)

        return request_urls

    def collect_responses(self, url: str) -> list[dict]:
        page = self._require_page()
        responses = []

        def handle_response(response):
            responses.append(
                {
                    "url": response.url,
                    "status": response.status,
                    "content_type": response.headers.get("content-type", ""),
                }
            )

        page.on("response", handle_response)
        page.goto(url)
        page.wait_for_timeout(5000)

        return responses

    def screenshot(self, path: str):
        return self.screenshots.save(path)

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

    def collect_json_requests(self, url: str) -> list[dict]:
        page = self._require_page()
        requests = []

        def handle_request(request):
            request_url = request.url

            if "proxies/core-api" not in request_url:
                return

            requests.append(
                {
                    "url": request_url,
                    "method": request.method,
                    "headers": request.headers,
                }
            )

        page.on("request", handle_request)
        page.goto(url)
        page.wait_for_timeout(8000)

        return requests

    def get_barchart_session(self) -> tuple[dict, list[dict]]:
        page_url = "https://www.barchart.com/options/iv-rank-percentile/high?sector=stock"

        requests = self.collect_json_requests(page_url)

        return (
            requests[0]["headers"],
            self._require_context().cookies(),
        )