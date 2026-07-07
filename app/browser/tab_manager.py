class TabManager:

    def __init__(self, get_context, get_page, set_page):
        self.get_context = get_context
        self.get_page = get_page
        self.set_page = set_page
        self.pages = []

    def initialize(self):
        context = self.get_context()

        page = context.new_page()
        self.pages.clear()
        self.pages.append(page)
        self.set_page(page)

        return page

    def new_tab(self):
        context = self.get_context()

        page = context.new_page()
        self.pages.append(page)
        self.set_page(page)

        return page

    def select_tab(self, index: int):
        if not self.pages:
            raise RuntimeError(
                "Browser wurde noch nicht gestartet. Erst browser.start() aufrufen."
            )

        if index < 0 or index >= len(self.pages):
            raise IndexError("Tab-Index existiert nicht.")

        page = self.pages[index]
        self.set_page(page)

        return page

    def current_tab_index(self) -> int:
        page = self.get_page()

        if page is None:
            raise RuntimeError(
                "Browser wurde noch nicht gestartet. Erst browser.start() aufrufen."
            )

        return self.pages.index(page)