# AI_CONTEXT

## Zweck

Diese Datei ermöglicht es einer neuen ChatGPT-Unterhaltung, den aktuellen Projektstand schnell zu verstehen und ohne Wissensverlust weiterzuarbeiten.

README.md ist der Einstiegspunkt.

Diese Datei beschreibt ausschließlich den aktuellen Entwicklungsstand.

---

# Projekt

Name:

OptionAgent

OptionAgent ist ein persönlicher KI-Agent zur Analyse von Optionsstrategien.

Der Agent führt niemals selbstständig Orders aus.

---

# Entwicklungsprinzipien

Bei jeder Weiterentwicklung gelten folgende Regeln:

1. Architektur zuerst
2. Kleine Klassen
3. Eine Klasse = eine Aufgabe
4. Clean Architecture
5. Öffentliche APIs möglichst stabil halten
6. Erst Implementierung
7. Dann Tests
8. Danach Commit
9. Danach Push

---

# Arbeitsweise

Der Benutzer ist Python-Einsteiger.

Deshalb gilt:

- immer nur ein Entwicklungsschritt
- vollständige Erklärung vor jeder Implementierung
- möglichst kleine Änderungen
- komplette Dateien nur bei neuen Dateien oder größeren Refactorings
- ansonsten gezielte Änderungen an bestehenden Dateien

---

# Aktuelle Architektur

Planner

↓

MarketData

↓

Analysis

↓

Reports

Browser und AI sind Infrastrukturmodule.

---

# Browser

Der Browser ist als Facade aufgebaut.

Aktuelle Komponenten:

- BrowserClient
- BrowserInteraction
- TabManager
- CookieManager
- ScreenshotService

BrowserClient ist ausschließlich öffentliche API.

---

# MarketData

Die öffentliche API lautet:

market_data.get_snapshot(symbol)

Der Rückgabewert ist:

MarketSnapshot

MarketData verwendet Provider.

Derzeit existiert:

DummyPriceProvider

Weitere Provider folgen später.

---

# Domänenmodelle

Aktuell vorhanden:

- Quote
- OptionContract
- OptionChain
- EarningsEvent
- MarketSnapshot

Diese Modelle bilden die gemeinsame Sprache des Projekts.

---

# Noch nicht implementiert

Analysis

Reports

Echte MarketData Provider

Planner-Workflow

OptionStrat-Integration

---

# Entwicklungsreihenfolge

1. Browser
2. MarketData
3. Analysis
4. Reports
5. Planner
6. OptionStrat

---

# Wichtig

Neue Chats sollen niemals anhand der Chat-Historie arbeiten.

Stattdessen:

1. README.md lesen
2. AI_CONTEXT.md lesen
3. weitere Dokumentation bei Bedarf lesen

Die Dokumentation ist die einzige Quelle für den Projektkontext.

---

# Nächster Schritt

Als Nächstes wird das Modul Analysis aufgebaut.

Zunächst Architektur.

Danach Modelle.

Danach Service.

Erst danach Implementierung der ersten Earnings-Analyse.