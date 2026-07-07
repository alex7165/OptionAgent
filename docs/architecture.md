# OptionAgent Architektur

## Ziel

OptionAgent ist ein persönlicher KI-Agent zur Analyse von Optionsstrategien,
insbesondere Earnings-Crush-Trades.

Der Agent soll Daten sammeln, analysieren und Handlungsvorschläge erstellen.
Er führt niemals selbstständig Orders aus.

---

# Architektur

main.py

↓

OptionAgent

↓

Planner

↓

Services

- AI
- Browser
- Reports
- Strategy
- Market Data (geplant)

---

# Module

## app/main.py

Startet den Agenten.

## app/agent.py

Koordiniert den Programmablauf.

## app/planner/

Entscheidet, welche Schritte zur Lösung einer Aufgabe notwendig sind.

## app/browser/

Steuert den Browser mit Playwright.

## app/ai/

Kommunikation mit OpenAI.

## app/reports/

Erzeugt Reports.

## app/strategy/

Enthält später die Handelslogik.

---

# Entwicklungsprinzipien

- Eine Klasse = eine Aufgabe.
- Kleine, klar verständliche Methoden.
- Vor jeder größeren Änderung Architektur überlegen.
- Jede neue Funktion erhält mindestens einen Test.
- Erst testen, dann Commit.
- Erst Commit, dann Push.