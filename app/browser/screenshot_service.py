from pathlib import Path


class ScreenshotService:

    def __init__(self, get_page):
        self.get_page = get_page

    def save(self, path: str):
        page = self.get_page()

        screenshot_path = Path(path)
        screenshot_path.parent.mkdir(parents=True, exist_ok=True)

        page.screenshot(
            path=str(screenshot_path),
            full_page=True,
        )

        return screenshot_path