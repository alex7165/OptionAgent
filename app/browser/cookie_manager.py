import json
from pathlib import Path


class CookieManager:

    def __init__(self, get_context):
        self.get_context = get_context

    def save(self, path: str):
        context = self.get_context()

        cookie_path = Path(path)
        cookie_path.parent.mkdir(parents=True, exist_ok=True)

        cookies = context.cookies()

        with cookie_path.open("w", encoding="utf-8") as file:
            json.dump(cookies, file, indent=2)

        return cookie_path

    def load(self, path: str):
        context = self.get_context()

        cookie_path = Path(path)

        with cookie_path.open("r", encoding="utf-8") as file:
            cookies = json.load(file)

        context.add_cookies(cookies)

        return cookie_path