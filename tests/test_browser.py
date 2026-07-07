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