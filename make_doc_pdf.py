# -*- coding: utf-8 -*-
"""Erzeugt eine PDF mit der kompletten Code-Erklaerung von Smartshift."""

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
)

OUT = "Smartshift_Code_Erklaerung.pdf"

# ── Farben ───────────────────────────────────────────────────────────────────
PRIMARY = colors.HexColor("#2563eb")
DARK = colors.HexColor("#1e293b")
GRAY = colors.HexColor("#64748b")
LIGHT = colors.HexColor("#f1f5f9")
BORDER = colors.HexColor("#cbd5e1")

# ── Styles ───────────────────────────────────────────────────────────────────
styles = getSampleStyleSheet()

h_title = ParagraphStyle("HTitle", parent=styles["Title"], fontSize=26,
                         textColor=PRIMARY, spaceAfter=6, leading=30)
h_sub = ParagraphStyle("HSub", parent=styles["Normal"], fontSize=12,
                       textColor=GRAY, spaceAfter=20, alignment=TA_LEFT)
h1 = ParagraphStyle("H1", parent=styles["Heading1"], fontSize=17,
                    textColor=PRIMARY, spaceBefore=16, spaceAfter=8, leading=20)
h2 = ParagraphStyle("H2", parent=styles["Heading2"], fontSize=13,
                    textColor=DARK, spaceBefore=10, spaceAfter=5, leading=16)
body = ParagraphStyle("Body", parent=styles["Normal"], fontSize=10,
                      textColor=DARK, spaceAfter=6, leading=15)
small = ParagraphStyle("Small", parent=styles["Normal"], fontSize=9,
                       textColor=GRAY, spaceAfter=4, leading=13)
code = ParagraphStyle("Code", parent=styles["Code"], fontSize=8.5,
                      textColor=DARK, backColor=LIGHT, leading=12,
                      borderPadding=6, spaceAfter=8, spaceBefore=2)
cell = ParagraphStyle("Cell", parent=styles["Normal"], fontSize=9, leading=12,
                      textColor=DARK)
cell_b = ParagraphStyle("CellB", parent=cell, fontName="Helvetica-Bold")

story = []


def P(text, st=body):
    story.append(Paragraph(text, st))


def gap(h=6):
    story.append(Spacer(1, h))


def bullets(items, st=body):
    for it in items:
        story.append(Paragraph("•&nbsp;&nbsp;" + it, st))


def make_table(rows, widths, header=True):
    """rows: list of lists of strings."""
    data = []
    for r_i, row in enumerate(rows):
        styled = []
        for c in row:
            styled.append(Paragraph(str(c), cell_b if (header and r_i == 0) else cell))
        data.append(styled)
    t = Table(data, colWidths=widths, repeatRows=1 if header else 0)
    ts = [
        ("GRID", (0, 0), (-1, -1), 0.5, BORDER),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]
    if header:
        ts += [
            ("BACKGROUND", (0, 0), (-1, 0), PRIMARY),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ]
        for r_i in range(1, len(rows)):
            if r_i % 2 == 0:
                ts.append(("BACKGROUND", (0, r_i), (-1, r_i), LIGHT))
    t.setStyle(TableStyle(ts))
    story.append(t)
    gap(10)


# ── Kopf-/Fusszeile ──────────────────────────────────────────────────────────
def on_page(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(GRAY)
    canvas.drawString(20 * mm, 12 * mm, "Smartshift – Code-Erklaerung")
    canvas.drawRightString(190 * mm, 12 * mm, "Seite %d" % doc.page)
    canvas.setStrokeColor(BORDER)
    canvas.line(20 * mm, 15 * mm, 190 * mm, 15 * mm)
    canvas.restoreState()


# ══════════════════════════════════════════════════════════════════════════════
# INHALT
# ══════════════════════════════════════════════════════════════════════════════

P("Smartshift", h_title)
P("Vollstaendige Erklaerung des Quellcodes &mdash; Schichtplanungssoftware "
  "(FastAPI + SQLite + HTML/JS)", h_sub)

P("Architektur-Ueberblick", h1)
P("Das Backend ist dreischichtig aufgebaut. Der Browser kommuniziert per "
  "HTTP/JSON mit FastAPI, das ueber die CRUD-Schicht auf die SQLite-Datenbank "
  "zugreift. Zwei Spezialmodule (Scheduler, Gemini-Assistent) erweitern die Logik.", body)
P("Browser (index.html + app.js + styles.css)<br/>"
  "&nbsp;&nbsp;&nbsp;&nbsp;&darr; HTTP/JSON (fetch)<br/>"
  "FastAPI (main.py) &rarr; crud.py &rarr; SQLAlchemy (models.py) &rarr; SQLite<br/>"
  "&nbsp;&nbsp;&nbsp;&nbsp;&rarr; scheduler.py (Planungsalgorithmus)<br/>"
  "&nbsp;&nbsp;&nbsp;&nbsp;&rarr; gemini_assistant.py (optionale KI)", code)
bullets([
    "<b>main.py</b> = API-Schicht (nimmt HTTP-Anfragen entgegen)",
    "<b>crud.py</b> = Logik-Schicht (Datenbankoperationen)",
    "<b>models.py</b> = Datenschicht (Tabellen-Definitionen)",
    "<b>schemas.py</b> = Validierung der Ein- und Ausgaben",
    "<b>scheduler.py / gemini_assistant.py</b> = Spezialmodule",
])

# 1. database.py
P("1. database.py &ndash; Datenbankverbindung", h1)
P("Die kleinste Datei. Stellt die Verbindung zur SQLite-Datei her.", body)
make_table([
    ["Element", "Funktion"],
    ["DB_PATH / DATABASE_URL", "Berechnet den Pfad zu data/smartshift.db"],
    ["engine", "SQLAlchemy-Verbindung. check_same_thread=False, da FastAPI mehrere Threads nutzt"],
    ["SessionLocal", "Fabrik, die einzelne Datenbank-Sitzungen erzeugt"],
    ["init_db()", "Erstellt den data-Ordner und legt alle Tabellen an. Laeuft beim Start"],
    ["get_db()", "Liefert pro Anfrage eine Session und schliesst sie sicher (yield + finally)"],
], [55 * mm, 110 * mm])

# 2. models.py
P("2. models.py &ndash; Die Datenbank-Tabellen", h1)
P("Jede Klasse entspricht einer Tabelle. Zuerst drei Enums (feste Auswahllisten): "
  "<b>IndustryType</b> (restaurant/retail/factory), <b>ExperienceLevel</b> "
  "(junior/normal/senior), <b>AbsenceType</b> (vacation/sick/school/other).", body)
make_table([
    ["Klasse", "Tabelle", "Speichert"],
    ["Business", "businesses", "Betrieb: Name, Branche"],
    ["OpeningHour", "opening_hours", "Oeffnungszeit pro Wochentag (0=Mo)"],
    ["Area", "areas", "Bereich (z.B. Kueche)"],
    ["Role", "roles", "Rolle (z.B. Koch)"],
    ["Employee", "employees", "Mitarbeiter: Zielstunden, Maxstunden, Level, freie Tage"],
    ["EmployeeRole", "employee_roles", "Verknuepfung: welcher MA hat welche Rolle"],
    ["EmployeeArea", "employee_areas", "Verknuepfung: welcher MA darf in welchem Bereich"],
    ["Availability", "availability", "Verfuegbarkeit an einem Datum (von/bis)"],
    ["Absence", "absences", "Abwesenheit (Typ, von/bis, genehmigt)"],
    ["ShiftRequirement", "shift_requirements", "Anforderung: Bereich, Rolle, Zeit, Anzahl"],
    ["GeneratedShift", "generated_shifts", "Ergebnis: konkrete Schicht mit Soll/Ist + Grund"],
    ["ShiftAssignment", "shift_assignments", "Verknuepfung: welcher MA in welcher Schicht"],
], [38 * mm, 38 * mm, 89 * mm])
P("<b>Warum Verknuepfungstabellen?</b> Ein Mitarbeiter kann mehrere Rollen haben "
  "und eine Rolle viele Mitarbeiter (n:m-Beziehung). Geloest ueber eine "
  "Zwischentabelle. <b>cascade=\"all, delete-orphan\"</b> loescht zugehoerige "
  "Daten automatisch mit, wenn der Betrieb geloescht wird.", small)

story.append(PageBreak())

# 3. schemas.py
P("3. schemas.py &ndash; Validierung (Pydantic)", h1)
P("Waehrend models.py definiert, WIE Daten gespeichert werden, definiert "
  "schemas.py, WIE Daten ueber die API rein- und rauskommen. Pro Entitaet meist "
  "drei Varianten:", body)
bullets([
    "<b>...Create</b> &ndash; Felder, die beim Anlegen erlaubt sind",
    "<b>...Update</b> &ndash; Felder zum Aendern (alle optional)",
    "<b>...Out</b> &ndash; Felder, die zurueckgegeben werden (mit id)",
])
P("Eingebaute Validierung &ndash; Beispiele:", h2)
bullets([
    "name: min_length=1, max_length=200 &rarr; darf nicht leer sein",
    "weekday: ge=0, le=6 &rarr; nur Wochentage 0&ndash;6",
    "target_hours_per_week: ge=0, le=168 &rarr; gueltige Stundenzahl",
])
P("Zwei eigene Validatoren: Enddatum &ge; Startdatum (Abwesenheit) und Endzeit "
  "nach Startzeit (Anforderung).", body)

# 4. crud.py
P("4. crud.py &ndash; Datenbankoperationen", h1)
P("CRUD = Create, Read, Update, Delete. Jede Funktion erhaelt eine db-Session "
  "und erledigt genau eine Aufgabe. Besondere Funktionen:", body)
bullets([
    "<b>create_business</b>: legt den Betrieb an UND automatisch die Standard-"
    "Bereiche/Rollen je nach Branche (Restaurant &rarr; Service/Kueche/Bar/Kasse).",
    "<b>create_employee</b>: legt MA an und fuellt die Verknuepfungstabellen "
    "(Rollen/Bereiche).",
    "<b>update_employee</b>: alte Rollen/Bereiche werden geloescht und neu gesetzt.",
    "<b>upsert_availability</b>: update-or-insert &ndash; verhindert doppelte "
    "Eintraege pro MA und Tag.",
    "<b>get_generated_shifts</b>: laedt Schichten + Bereiche + Rollen + "
    "Zuweisungen + MA in einer Abfrage (joinedload, vermeidet N+1-Problem).",
    "<b>delete_generated_shifts</b>: loescht alle Schichten einer Woche &ndash; "
    "wird vor jeder Neuplanung aufgerufen.",
])

story.append(PageBreak())

# 5. scheduler.py
P("5. scheduler.py &ndash; Der Planungsalgorithmus (Herzstueck)", h1)
P("Keine KI &ndash; eine nachvollziehbare Heuristik. EXPERIENCE_PRIORITY: "
  "senior=0, normal=1, junior=2 (kleiner = hoehere Prioritaet).", body)
P("Hilfsfunktionen", h2)
make_table([
    ["Funktion", "Aufgabe"],
    ["_time_to_hours(t)", "Wandelt 17:30 in 17.5 um (zum Rechnen)"],
    ["_shift_duration(s, e)", "Dauer einer Schicht in Stunden"],
    ["_times_overlap(...)", "Ueberschneiden sich zwei Zeitfenster? (Zeitkonflikt)"],
    ["_is_absent(emp, datum)", "Ist der MA abwesend? Gibt (True, 'Krank') zurueck"],
    ["_is_available_for_shift", "Passt die eingetragene Verfuegbarkeit zur Schicht? "
     "Ohne Eintrag gilt der MA als verfuegbar"],
    ["_employee_role_ids / _area_ids", "Listet Rollen-/Bereichs-IDs eines MA"],
], [50 * mm, 115 * mm])

P("Hauptfunktion: generate_schedule(db, business_id, week_start)", h2)
bullets([
    "<b>1.</b> Pruefung: week_start muss ein Montag sein.",
    "<b>2.</b> Alten Plan dieser Woche loeschen.",
    "<b>3.</b> Daten laden: aktive Mitarbeiter (mit Rollen, Bereichen, "
    "Abwesenheiten, Verfuegbarkeiten) und aktive Anforderungen.",
    "<b>4.</b> Tracking anlegen: weekly_hours (Stunden je MA) und "
    "daily_assignments (belegte Zeiten je MA).",
    "<b>5.</b> Anforderungen auf konkrete Daten umrechnen (weekday=0 &rarr; Montag).",
    "<b>6.</b> Sortieren nach Datum, dann Startzeit.",
])
P("<b>7. Fuer jede Anforderung</b> alle Mitarbeiter pruefen (wer durchfaellt, "
  "wird mit Grund gezaehlt):", body)
bullets([
    "Passende Rolle? &rarr; sonst 'Falsche Rolle'",
    "Passender Bereich? &rarr; sonst 'Falscher Bereich'",
    "Abwesend? &rarr; 'Krank' / 'Urlaub'",
    "Verfuegbar zur Schichtzeit? &rarr; sonst 'Nur 9&ndash;16 Uhr verfuegbar'",
    "Zeitkonflikt mit anderer Schicht? &rarr; 'Zeitkonflikt'",
    "Wuerde Maximalstunden sprengen? &rarr; 'Max. Wochenstunden erreicht'",
], small)
P("Die uebrigen Kandidaten werden sortiert nach (1) wenigste bisherige Stunden "
  "&rarr; gleichmaessige Verteilung, dann (2) Erfahrungslevel &rarr; Senior zuerst. "
  "Die ersten N werden zugeteilt. Bei Unterbesetzung wird ein Begruendungstext "
  "erzeugt, z.B.: 'Fehlend: 1 Person(en). Gruende: 2x Krank; 1x Zeitkonflikt'. "
  "Schicht und Zuweisungen werden gespeichert.", body)
P("<b>8.</b> Commit und Rueckgabe: {shifts_created, assignments_made, "
  "understaffed_count, warnings}. Das Besondere: Jede Ablehnung wird gezaehlt "
  "und als Klartext begruendet &ndash; volle Nachvollziehbarkeit.", body)

story.append(PageBreak())

# 6. gemini
P("6. gemini_assistant.py &ndash; Optionale KI-Analyse", h1)
P("Berechnet NICHTS am Plan &ndash; fasst ihn nur zusammen und laesst ihn von "
  "Gemini kommentieren.", body)
make_table([
    ["Element", "Funktion"],
    ["try: import google.generativeai", "Fehlt das Paket, wird GENAI_AVAILABLE=False gesetzt statt abzustuerzen"],
    ["_build_prompt(summary)", "Baut einen deutschen Prompt: Wochenuebersicht, Schichten, MA-Stunden + 4 Fragen"],
    ["analyze_schedule(summary)", "Dreifache Absicherung: kein Key / Paket fehlt / API-Fehler. Programm laeuft immer weiter"],
], [62 * mm, 103 * mm])
P("Datenschutz: nur Vornamen werden uebergeben, keine sensiblen Daten.", small)

# 7. main.py
P("7. main.py &ndash; Die API (alle Endpunkte)", h1)
P("Verbindet alles. Beim Start: .env laden, Tabellen anlegen, Demo-Daten "
  "einspielen. / liefert index.html, /static die Frontend-Dateien. "
  "Rund 40 Endpunkte nach gleichem Muster (Beispiel Mitarbeiter):", body)
make_table([
    ["Methode + Pfad", "Funktion"],
    ["GET .../employees", "Liste aller Mitarbeiter"],
    ["POST .../employees", "Neuen anlegen"],
    ["GET /api/employees/{id}", "Einen abrufen"],
    ["PUT /api/employees/{id}", "Aendern"],
    ["DELETE /api/employees/{id}", "Loeschen"],
], [70 * mm, 95 * mm])
P("Spezial-Endpunkte:", h2)
bullets([
    "<b>POST .../schedule/generate</b>: ruft den Scheduler. ValueError (kein "
    "Montag) wird als HTTP 400 zurueckgegeben.",
    "<b>GET/DELETE .../schedule</b>: Plan einer Woche abrufen/loeschen.",
    "<b>GET .../schedule/export/csv</b>: baut im Speicher eine CSV (Semikolon-"
    "getrennt, utf-8-sig fuer korrekte Umlaute in Excel) als Download.",
    "<b>POST .../gemini-analysis</b>: sammelt den Plan, berechnet MA-Stunden, "
    "anonymisiert (nur Vorname) und schickt die Zusammenfassung an Gemini.",
])

story.append(PageBreak())

# 8. seed.py
P("8. seed.py &ndash; Demo-Daten", h1)
bullets([
    "Bricht ab, wenn schon ein Betrieb existiert &ndash; wird nicht doppelt angelegt.",
    "Legt 'Demo Bistro' an: Oeffnungszeiten (Mo&ndash;Sa 9&ndash;23, So zu), "
    "Bereiche, Rollen.",
    "5 Mitarbeiter: Ali, Sara (Senior), Max (Junior, 2 Rollen), Lena, Tom.",
    "Anforderungen fuer Mo&ndash;Sa (Mittag + Abend).",
    "Verfuegbarkeiten (z.B. Lena nur vormittags, Max montags nur abends).",
    "Krankmeldung: Sara ist Donnerstag krank &rarr; Kueche wird sichtbar unterbesetzt.",
    "Alle Daten beziehen sich auf die aktuelle Woche &rarr; sofort planbar.",
])

# 9. Frontend
P("9. Frontend (index.html, styles.css, app.js)", h1)
P("<b>index.html</b>: Single-Page-App &ndash; alle Seiten sind vorhanden, nur "
  "eine ist sichtbar (active). Sidebar-Navigation, Betriebsauswahl, Modals fuer "
  "Formulare.", body)
P("<b>styles.css</b>: modernes Design ueber CSS-Variablen (--primary, --danger). "
  "Sidebar, Karten, Tabellen, Badges, Schicht-Karten (rot bei Unterbesetzung), "
  "Toasts, Modals.", body)
P("<b>app.js</b> &ndash; die Logik:", h2)
bullets([
    "<b>state</b>: merkt sich Betrieb, Listen, aktuelle Woche.",
    "<b>api(method, path, body)</b>: zentrale fetch-Funktion mit lesbarer "
    "Fehlerbehandlung.",
    "<b>navigate(page)</b>: zeigt Seite und laedt deren Daten bei Bedarf (lazy).",
    "Pro Bereich ein Set aus load + render + save + delete.",
    "<b>renderSchedule</b>: baut die 7-Spalten-Wochenansicht, filtert nach "
    "MA/Bereich, markiert heute, zeigt die Warnungen-Box.",
    "<b>generateSchedule / deleteSchedule / exportCSV</b>: bedienen die Buttons.",
    "<b>init()</b>: startet alles; bei Backend-Fehler erscheint ein Toast.",
])

# Datenfluss
P("Datenfluss am Beispiel 'Plan erstellen'", h1)
bullets([
    "1. Klick auf 'Plan erstellen' &rarr; generateSchedule() in app.js",
    "2. api('POST', '.../schedule/generate', {week_start}) &rarr; HTTP-Anfrage",
    "3. main.py-Endpunkt &rarr; ruft scheduler.generate_schedule",
    "4. scheduler.py laedt Daten, rechnet, schreibt GeneratedShift + "
    "ShiftAssignment in die DB",
    "5. Rueckgabe der Zusammenfassung &rarr; Toast 'X Schichten, Y Zuweisungen'",
    "6. renderSchedule() zeichnet die Wochenansicht mit roten Markierungen",
])

# ── Build ────────────────────────────────────────────────────────────────────
doc = SimpleDocTemplate(
    OUT, pagesize=A4,
    leftMargin=20 * mm, rightMargin=20 * mm,
    topMargin=18 * mm, bottomMargin=20 * mm,
    title="Smartshift - Code-Erklaerung",
    author="Smartshift",
)
doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
print("PDF erstellt:", OUT)
