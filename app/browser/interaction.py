class BrowserInteraction:

    def __init__(self, get_page):
        self.get_page = get_page

    def click(self, selector: str):
        page = self.get_page()
        page.click(selector)

    def fill(self, selector: str, text: str):
        page = self.get_page()
        page.fill(selector, text)

    def press(self, selector: str, key: str):
        page = self.get_page()
        page.press(selector, key)

    def wait_for(self, selector: str):
        page = self.get_page()
        page.wait_for_selector(selector)