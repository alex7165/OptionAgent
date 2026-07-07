# Architektur

## Architekturprinzipien

OptionAgent ist nach den Prinzipien der Clean Architecture aufgebaut.

Grundsätze:

- Kleine Klassen
- Eine Klasse = eine Verantwortung
- Öffentliche APIs bleiben möglichst stabil
- Implementierungsdetails sind gekapselt
- Module kommunizieren ausschließlich über definierte Schnittstellen

---

# Gesamtübersicht

```text
main.py
    │
    ▼
OptionAgent
    │
    ▼
Planner
    │
    ├──────────────┐
    ▼              ▼
MarketData      Browser
    │
    ▼
Analysis
    │
    ▼
Reports
```

---

# Module

## OptionAgent

Verantwortlich für:

- Start des Systems
- Initialisierung der Services
- Koordination des Ablaufs

---

## Planner

Verantwortlich für:

- Zerlegen einer Benutzeranfrage
- Erstellen eines Arbeitsplans
- Aufruf der benötigten Services

Der Planner enthält keine technische Logik.

---

## Browser

Der Browser ist eine Infrastrukturkomponente.

Er besteht aus:

```text
BrowserClient
│
├── TabManager
├── BrowserInteraction
├── CookieManager
└── ScreenshotService
```

BrowserClient ist die einzige öffentliche Schnittstelle.

---

## MarketData

MarketData sammelt Marktdaten aus unterschiedlichen Quellen.

Die öffentliche API lautet:

```python
market_data.get_snapshot(symbol)
```

Intern werden spezialisierte Provider verwendet.

Beispiele:

- PriceProvider
- EarningsProvider
- OptionChainProvider
- VolatilityProvider

---

## Analysis

Analysis enthält die fachliche Intelligenz.

Beispiele:

- Earnings Analyzer
- Covered Call Analyzer
- Short Put Analyzer
- Portfolio Analyzer

Analysis entscheidet niemals, woher Daten stammen.

---

## Reports

Reports erzeugen Ausgaben.

Zum Beispiel:

- Markdown
- HTML
- PDF

---

# Abhängigkeiten

Erlaubt:

```text
Planner
    ↓
MarketData
    ↓
Analysis
    ↓
Reports
```

Nicht erlaubt:

- Analysis kennt Browser
- Reports kennen Browser
- Planner kennt Implementierungsdetails eines Providers

---

# Architekturregel

Neue Funktionen werden grundsätzlich in bestehende Verantwortungsbereiche eingeordnet.

Neue Klassen entstehen nur dann, wenn eine neue Verantwortung entsteht.