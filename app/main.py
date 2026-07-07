from assistant import ask_agent
from reporting import save_report

print("OptionAgent gestartet")
print()

frage = input("Frage an den Agenten: ")

antwort = ask_agent(frage)
report_path = save_report(frage, antwort)

print()
print("Antwort:")
print(antwort)

print()
print(f"Report gespeichert unter: {report_path}")