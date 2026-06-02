# Smartshift – Schichtplanung MVP

Einfache, lokale Schichtplanungssoftware für Restaurants, Einzelhandel und Fabriken.
Ersetzt klassische Excel-Schichtpläne durch einen automatischen Algorithmus.

---

## Schnellstart

### 1. Voraussetzungen

- Python 3.10 oder höher
- pip

### 2. Installation

```bash
# In den Projektordner wechseln
cd smartshift

# Virtuelle Umgebung erstellen (empfohlen)
python -m venv .venv

# Aktivieren (Windows)
.venv\Scripts\activate

# Aktivieren (Mac/Linux)
source .venv/bin/activate

# Abhängigkeiten installieren
pip install -r requirements.txt
```

### 3. Konfiguration (optional)

```bash
# .env Datei anlegen (für Gemini-Assistent)
copy .env.example .env   # Windows
cp .env.example .env     # Mac/Linux

# GEMINI_API_KEY in .env eintragen (optional)
# Das Programm funktioniert ohne diesen Key vollständig!
```

### 4. Server starten

```bash
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 5. Im Browser öffnen

```
http://localhost:8000
```

Die Datenbank und Demo-Daten werden beim ersten Start automatisch angelegt.

---

## Funktionen

| Funktion | Beschreibung |
|---|---|
| **Betriebsprofil** | Betrieb anlegen mit Branche (Restaurant/Einzelhandel/Fabrik) und Öffnungszeiten |
| **Mitarbeiterverwaltung** | Mitarbeiter mit Rollen, Bereichen, Stundenziel und Erfahrungslevel |
| **Verfügbarkeiten** | Tagesgenaue Verfügbarkeit mit Zeitfenstern eintragen |
| **Abwesenheiten** | Urlaub, Krankheit, Schule – werden bei der Planung berücksichtigt |
| **Schichtanforderungen** | Wöchentlich wiederkehrende oder tagesgenaue Anforderungen |
| **Automatischer Plan** | Heuristischer Algorithmus ohne KI – nachvollziehbar und erweiterbar |
| **Wochenansicht** | Übersichtliche Kalenderansicht mit Filterfunktionen |
| **CSV-Export** | Plan als CSV exportieren |
| **Gemini-Assistent** | Optionale KI-Analyse des Plans (GEMINI_API_KEY erforderlich) |

---

## Planungsalgorithmus

Der Algorithmus arbeitet ohne KI/ML und ist vollständig nachvollziehbar:

1. Lade alle aktiven Schichtanforderungen für die Zielwoche
2. Filtere Mitarbeiter nach:
   - Passende Rolle und Bereich
   - Keine Abwesenheit (Urlaub, Krankheit, etc.)
   - Verfügbar im Schichtzeitraum
   - Kein Zeitkonflikt mit bereits zugeteilten Schichten
   - Max. Wochenstunden nicht überschritten
3. Sortiere Kandidaten nach:
   - Weniger geplante Stunden zuerst (gleichmäßige Verteilung)
   - Senior vor Normal vor Junior (Schlüsselbereiche)
4. Weise die ersten N Kandidaten zu
5. Markiere unterbesetzte Schichten mit Begründung

---

## Projektstruktur

```
smartshift/
├── backend/
│   ├── main.py              # FastAPI App, alle API-Endpunkte
│   ├── database.py          # SQLite Datenbankverbindung
│   ├── models.py            # SQLAlchemy ORM Modelle
│   ├── schemas.py           # Pydantic Validierungsschemas
│   ├── crud.py              # Datenbankoperationen
│   ├── scheduler.py         # Planungsalgorithmus
│   ├── gemini_assistant.py  # Optionale Gemini-Integration
│   └── seed.py              # Demo-Daten
├── frontend/
│   ├── index.html           # Single-Page-App
│   ├── styles.css           # Design
│   └── app.js               # Frontend-Logik
├── data/
│   └── smartshift.db        # SQLite Datenbank (wird automatisch erstellt)
├── .env.example
├── requirements.txt
└── README.md
```

---

## Demo-Daten

Beim ersten Start werden automatisch angelegt:
- **Betrieb**: Demo Bistro (Restaurant)
- **Mitarbeiter**: Ali (Kellner), Sara (Koch, Senior), Max (Kellner/Bar), Lena (Kassierer), Tom (Koch)
- **Schichtanforderungen**: Mo–Sa, Mittags (10–15 Uhr) und Abends (17–22 Uhr)
- **Verfügbarkeiten** und **Abwesenheiten** für die aktuelle Woche

---

## API-Dokumentation

Die interaktive API-Dokumentation ist unter `http://localhost:8000/docs` erreichbar.

---

## Gemini API Key

1. Google AI Studio öffnen: https://aistudio.google.com/
2. API Key erstellen
3. In `.env` eintragen: `GEMINI_API_KEY=dein_key`
4. Server neu starten

Ohne Key: Das Programm läuft vollständig. Nur die KI-Assistenzfunktion ist deaktiviert.
