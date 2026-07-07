from app.browser.browser import BrowserClient


def test_browser_title():
    browser = BrowserClient(headless=True)

    browser.start()

    browser.goto("https://openai.com")

    title = browser.get_title()

    browser.close()

    assert len(title) > 0