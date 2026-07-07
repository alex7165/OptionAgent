from app.ai.client import ask_agent
from app.reports.reporting import save_report


class OptionAgent:

    def run(self):

        print("OptionAgent gestartet")
        print()

        question = input("Frage an den Agenten: ")

        answer = ask_agent(question)

        report = save_report(question, answer)

        print()
        print("Antwort:")
        print(answer)

        print()
        print(f"Report gespeichert unter: {report}")