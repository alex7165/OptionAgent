from assistant import ask_agent

print("OptionAgent gestartet")
print()

frage = input("Frage an den Agenten: ")

antwort = ask_agent(frage)

print()
print("Antwort:")
print(antwort)