# OptionAgent – Projektkontext

## Projektziel

OptionAgent ist ein persönlicher KI-Agent zur Analyse von Optionsstrategien.

Der Schwerpunkt liegt auf Earnings-Trades und systematischen Optionsanalysen.

Der Agent soll Informationen sammeln, analysieren und Handlungsvorschläge erstellen.

Der Agent führt niemals selbstständig Orders aus.

---

# Aktueller Entwicklungsstand

## Infrastruktur

Fertig:

- Git
- GitHub
- GitHub Desktop
- VS Code
- Python
- virtuelle Umgebung
- OpenAI API
- Playwright
- pytest

---

## Architektur

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
- Strategy (noch leer)
- MarketData (noch nicht implementiert)

---

# Vorhandene Module

app/

- ai/
- browser/
- planner/
- reports/
- strategy/

---

# Browser

BrowserClient

Kann bereits:

- Browser starten
- Browser schließen
- Webseite öffnen
- Titel lesen
- gesamten Seitentext lesen

---

# Planner

Der Planner entscheidet aktuell:

- URL → Webseite lesen und zusammenfassen
- normale Frage → direkt an GPT

---

# Tests

pytest eingerichtet

Vorhandene Tests:

- Browser
- Planner

---

# Entwicklungsprinzipien

- Kleine Klassen
- Eine Klasse = eine Aufgabe
- Clean Architecture
- Erst Architektur
- Dann Implementierung
- Dann Test
- Dann Commit
- Dann Push

---

# Nächster Entwicklungsschritt

Version 1.2

Browser professionell erweitern:

- mehrere Tabs
- Screenshots
- Cookies
- Downloads

Danach:

MarketData-Service

Danach:

OptionStrat-Integration

---

# Arbeitsweise

Der Benutzer ist Python-Einsteiger.

Deshalb:

- immer nur ein Schritt
- komplette Dateien statt Codefragmente
- zuerst Architektur erklären
- danach implementieren
- danach testen
- danach Commit
- danach Push
---

# Wichtige Designentscheidungen

## Architektur

Der OptionAgent ist schichtenbasiert aufgebaut.

main.py startet ausschließlich den Agenten.

OptionAgent koordiniert den Ablauf.

Der Planner entscheidet, welche Schritte zur Lösung einer Aufgabe notwendig sind.

Die Services führen diese Schritte aus.

Der Planner kennt keine technischen Details der Services.

---

## Browser

BrowserClient hält den Browser geöffnet.

Dadurch bleiben Cookies und Login erhalten.

Dies ist Voraussetzung für die spätere OptionStrat-Integration.

---

## Tests

Jede neue Funktion erhält mindestens einen pytest-Test.

---

## Git

Nach jeder abgeschlossenen Funktion:

- Test
- Commit
- Push

---

## Langfristiges Ziel

Der Agent soll später selbstständig entscheiden,

- welche Daten benötigt werden,
- welche Webseiten besucht werden,
- welche Strategie geeignet ist,

und daraus einen vollständigen Analysebericht erstellen.