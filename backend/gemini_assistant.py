"""
Gemini Assistant – optional AI analysis of the generated schedule.
Falls back gracefully when GEMINI_API_KEY is not set or the call fails.
"""

import os
import json
from datetime import date
from typing import List

try:
    import google.generativeai as genai
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False


def _build_prompt(summary: dict) -> str:
    lines = [
        "Du bist ein erfahrener Schichtplanungs-Assistent. Analysiere den folgenden Schichtplan und gib konkrete Verbesserungsvorschläge.",
        "",
        f"Woche ab: {summary['week_start']}",
        f"Erstellte Schichten: {summary['shifts_created']}",
        f"Zuweisungen gesamt: {summary['assignments_made']}",
        f"Unterbesetzte Schichten: {summary['understaffed_count']}",
        "",
        "Schichten (Datum | Bereich | Rolle | Start–Ende | Benötigt/Zugeteilt | Status):",
    ]
    for s in summary["shifts"]:
        status = "UNTERBESETZT" if s["is_understaffed"] else "OK"
        lines.append(
            f"  {s['date']} | {s['area']} | {s.get('role', '-')} | "
            f"{s['start_time']}–{s['end_time']} | "
            f"{s['assigned_count']}/{s['required_count']} | {status}"
        )
        if s["is_understaffed"] and s["understaffed_reason"]:
            lines.append(f"    Grund: {s['understaffed_reason']}")

    if summary.get("employee_hours"):
        lines.append("")
        lines.append("Mitarbeiterstunden diese Woche:")
        for emp_name, hours in summary["employee_hours"].items():
            lines.append(f"  {emp_name}: {hours:.1f}h")

    lines += [
        "",
        "Bitte beantworte folgende Fragen:",
        "1. Welche Schichten sind kritisch unterbesetzt?",
        "2. Welche Mitarbeiter sind überlastet oder unterbeschäftigt?",
        "3. Gibt es zeitliche Konflikte oder Risiken?",
        "4. Welche konkreten Verbesserungen empfiehlst du?",
        "",
        "Antworte auf Deutsch, klar und strukturiert. Keine persönlichen Daten weitergeben.",
    ]
    return "\n".join(lines)


def analyze_schedule(summary: dict) -> dict:
    """
    Send schedule summary to Gemini for analysis.
    Returns {"analysis": str, "available": bool}
    """
    api_key = os.getenv("GEMINI_API_KEY", "").strip()

    if not api_key:
        return {
            "analysis": "Gemini-Assistent nicht verfügbar: Kein GEMINI_API_KEY in der .env Datei gesetzt.",
            "available": False,
        }

    if not GENAI_AVAILABLE:
        return {
            "analysis": "Gemini-Assistent nicht verfügbar: Das Paket 'google-generativeai' ist nicht installiert.",
            "available": False,
        }

    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-1.5-flash")
        prompt = _build_prompt(summary)
        response = model.generate_content(prompt)
        return {
            "analysis": response.text,
            "available": True,
        }
    except Exception as e:
        return {
            "analysis": f"Gemini-Analyse fehlgeschlagen: {str(e)}",
            "available": False,
        }
