from app.browser.browser import BrowserClient


def test_browser_title():
    browser = BrowserClient(headless=True)

    browser.start()

    browser.goto("https://openai.com")

    title = browser.get_title()

    browser.close()

    assert len(title) > 0

def test_browser_can_open_new_tab():
    browser = BrowserClient(headless=True)

    try:
        browser.start()

        first_page = browser.page
        second_page = browser.new_tab()

        assert len(browser.pages) == 2
        assert first_page != second_page
        assert browser.page == second_page

    finally:
        browser.close()

def test_browser_can_select_tab():
    browser = BrowserClient(headless=True)

    try:
        browser.start()

        first_page = browser.page
        second_page = browser.new_tab()

        assert browser.current_tab_index() == 1

        selected_page = browser.select_tab(0)

        assert selected_page == first_page
        assert browser.page == first_page
        assert browser.current_tab_index() == 0

        browser.select_tab(1)

        assert browser.page == second_page
        assert browser.current_tab_index() == 1

    finally:
        browser.close()

def test_browser_can_take_screenshot(tmp_path):
    browser = BrowserClient(headless=True)

    try:
        browser.start()
        browser.goto("https://example.com")

        screenshot_path = tmp_path / "example.png"
        result_path = browser.screenshot(str(screenshot_path))

        assert result_path.exists()
        assert result_path.suffix == ".png"

    finally:
        browser.close()