from app.ai.client import ask_agent
from app.browser.browser import BrowserClient
from app.reports.reporting import save_report


class Planner:

    def execute(self, task: str) -> str:
        if self._is_url(task):
            return self._summarize_website(task)

        return self._answer_question(task)

    def _is_url(self, text: str) -> bool:
        return text.startswith("http://") or text.startswith("https://")

    def _answer_question(self, question: str) -> str:
        answer = ask_agent(question)
        save_report(question, answer)
        return answer

    def _summarize_website(self, url: str) -> str:
        browser = BrowserClient(headless=False)

        browser.start()
        browser.goto(url)

        title = browser.get_title()
        text = browser.get_text()

        browser.close()

        prompt = f"""
Titel:
{title}

Seiteninhalt:
{text[:8000]}

Fasse diese Webseite in höchstens 10 Stichpunkten zusammen.
"""

        answer = ask_agent(prompt)
        save_report(url, answer)

        return answer