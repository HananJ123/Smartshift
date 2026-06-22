"""
Seed the database with demo data.
Legt 'Demo Bistro' sowie vier realistische Beispielbetriebe an.
Läuft nur, wenn noch kein Betrieb existiert.
"""

from datetime import date, time, timedelta
import models


def _build_business(db, name, industry, area_names, role_names, employees, requirements):
    """Hilfsfunktion: legt einen kompletten Betrieb mit Bereichen, Rollen,
    Mitarbeitern und Schichtanforderungen an.

    employees:   Liste aus (name, [rollen], [bereiche], ziel_h, max_h, level)
    requirements: Liste aus dicts {days, start, end, area, role, count}
                  days = 'daily' oder Liste von Wochentagen (0=Mo .. 6=So)

    Gibt None zurück, wenn ein Betrieb mit diesem Namen bereits existiert
    (additiver Seed – vorhandene Daten bleiben unberührt).
    """
    if db.query(models.Business).filter_by(name=name).first():
        return None

    business = models.Business(name=name, industry=industry)
    db.add(business)
    db.flush()

    # Öffnungszeiten Mo–Sa offen, So zu (nur als Standardannahme)
    for wd in range(7):
        if wd == 6:
            db.add(models.OpeningHour(business_id=business.id, weekday=wd, is_closed=True))
        else:
            db.add(models.OpeningHour(business_id=business.id, weekday=wd,
                                      open_time=time(6, 0), close_time=time(23, 0), is_closed=False))

    areas, roles = {}, {}
    for n in area_names:
        a = models.Area(business_id=business.id, name=n)
        db.add(a); db.flush(); areas[n] = a
    for n in role_names:
        r = models.Role(business_id=business.id, name=n)
        db.add(r); db.flush(); roles[n] = r

    for (emp_name, emp_roles, emp_areas, target, maximum, level) in employees:
        emp = models.Employee(
            business_id=business.id, name=emp_name,
            target_hours_per_week=target, max_hours_per_week=maximum,
            experience_level=level,
        )
        db.add(emp); db.flush()
        for rk in emp_roles:
            db.add(models.EmployeeRole(employee_id=emp.id, role_id=roles[rk].id))
        for ak in emp_areas:
            db.add(models.EmployeeArea(employee_id=emp.id, area_id=areas[ak].id))

    for req in requirements:
        days = req["days"]
        is_daily = days == "daily"
        weekday_list = [None] if is_daily else days
        for wd in weekday_list:
            db.add(models.ShiftRequirement(
                business_id=business.id,
                area_id=areas[req["area"]].id,
                role_id=roles[req["role"]].id,
                is_daily=is_daily,
                weekday=wd,
                start_time=req["start"],
                end_time=req["end"],
                required_count=req["count"],
                is_active=True,
            ))
    return business


def seed_demo_data(db):
    # Additiv: _build_business legt nur Betriebe an, die es noch nicht gibt
    # (anhand des Namens). So gehen vorhandene Daten nicht verloren und neue
    # Beispielbetriebe werden bei jedem Start ergänzt.
    J = models.ExperienceLevel.junior
    N = models.ExperienceLevel.normal
    S = models.ExperienceLevel.senior
    MOFR = [0, 1, 2, 3, 4]
    MOSA = [0, 1, 2, 3, 4, 5]

    # ── 1. Demo Bistro (Restaurant) ──────────────────────────────────────────
    bistro = _build_business(
        db, "Demo Bistro", models.IndustryType.restaurant,
        area_names=["Service", "Küche", "Bar", "Kasse"],
        role_names=["Kellner", "Koch", "Barkeeper", "Kassierer"],
        employees=[
            ("Ali", ["Kellner"], ["Service"], 30, 40, N),
            ("Sara", ["Koch"], ["Küche"], 25, 35, S),
            ("Max", ["Kellner", "Barkeeper"], ["Service", "Bar"], 20, 30, J),
            ("Lena", ["Kassierer"], ["Kasse"], 15, 20, N),
            ("Tom", ["Koch"], ["Küche"], 30, 40, N),
        ],
        requirements=[
            {"days": MOSA, "start": time(10, 0), "end": time(15, 0), "area": "Service", "role": "Kellner", "count": 2},
            {"days": MOSA, "start": time(10, 0), "end": time(15, 0), "area": "Küche", "role": "Koch", "count": 1},
            {"days": MOSA, "start": time(10, 0), "end": time(15, 0), "area": "Kasse", "role": "Kassierer", "count": 1},
            {"days": MOSA, "start": time(17, 0), "end": time(22, 0), "area": "Service", "role": "Kellner", "count": 3},
            {"days": MOSA, "start": time(17, 0), "end": time(22, 0), "area": "Küche", "role": "Koch", "count": 2},
            {"days": MOSA, "start": time(17, 0), "end": time(22, 0), "area": "Bar", "role": "Barkeeper", "count": 1},
        ],
    )

    # ── 2. WISKA Hoppmann (Produktion) ───────────────────────────────────────
    _build_business(
        db, "WISKA Hoppmann", models.IndustryType.factory,
        area_names=["Produktion", "Verpackung", "Lager", "Qualitätskontrolle"],
        role_names=["Maschinenführer", "Verpacker", "Lagerist", "QS-Prüfer"],
        employees=[
            ("Klaus", ["Maschinenführer"], ["Produktion"], 38, 42, S),
            ("Petra", ["Maschinenführer"], ["Produktion"], 38, 42, N),
            ("Jörg", ["Verpacker"], ["Verpackung"], 35, 40, N),
            ("Sabine", ["Lagerist"], ["Lager"], 35, 40, N),
            ("Murat", ["QS-Prüfer"], ["Qualitätskontrolle"], 38, 42, S),
        ],
        requirements=[
            # Frühschicht
            {"days": MOFR, "start": time(6, 0), "end": time(14, 0), "area": "Produktion", "role": "Maschinenführer", "count": 2},
            {"days": MOFR, "start": time(6, 0), "end": time(14, 0), "area": "Verpackung", "role": "Verpacker", "count": 1},
            {"days": MOFR, "start": time(6, 0), "end": time(14, 0), "area": "Qualitätskontrolle", "role": "QS-Prüfer", "count": 1},
            # Spätschicht
            {"days": MOFR, "start": time(14, 0), "end": time(22, 0), "area": "Produktion", "role": "Maschinenführer", "count": 2},
            {"days": MOFR, "start": time(14, 0), "end": time(22, 0), "area": "Lager", "role": "Lagerist", "count": 1},
        ],
    )

    # ── 3. Goldies Itzstedt (Gastronomie / Pizza & Lieferung) ────────────────
    _build_business(
        db, "Goldies Itzstedt", models.IndustryType.restaurant,
        area_names=["Küche", "Service", "Lieferung", "Kasse"],
        role_names=["Pizzabäcker", "Kellner", "Fahrer", "Kassierer"],
        employees=[
            ("Gino", ["Pizzabäcker"], ["Küche"], 40, 45, S),
            ("Luca", ["Pizzabäcker"], ["Küche"], 35, 40, N),
            ("Mia", ["Kellner", "Kassierer"], ["Service", "Kasse"], 25, 35, N),
            ("Deniz", ["Fahrer"], ["Lieferung"], 20, 30, J),
            ("Jonas", ["Fahrer", "Kellner"], ["Lieferung", "Service"], 30, 40, N),
        ],
        requirements=[
            {"days": "daily", "start": time(16, 0), "end": time(23, 0), "area": "Küche", "role": "Pizzabäcker", "count": 2},
            {"days": "daily", "start": time(17, 0), "end": time(23, 0), "area": "Lieferung", "role": "Fahrer", "count": 2},
            {"days": "daily", "start": time(16, 0), "end": time(22, 0), "area": "Service", "role": "Kellner", "count": 1},
            # Wochenende Spätschicht über Mitternacht
            {"days": [4, 5], "start": time(22, 0), "end": time(1, 0), "area": "Lieferung", "role": "Fahrer", "count": 1},
        ],
    )

    # ── 4. A & M Transporte (Logistik / Stückgut) ────────────────────────────
    _build_business(
        db, "A & M Transporte", models.IndustryType.logistics,
        area_names=["Disposition", "Fuhrpark", "Lager", "Verladung"],
        role_names=["Disponent", "LKW-Fahrer", "Lagerist", "Verlader"],
        employees=[
            ("Andreas", ["Disponent"], ["Disposition"], 40, 45, S),
            ("Marko", ["LKW-Fahrer"], ["Fuhrpark"], 40, 48, N),
            ("Stefan", ["LKW-Fahrer"], ["Fuhrpark"], 40, 48, N),
            ("Dirk", ["Verlader"], ["Verladung"], 35, 40, J),
            ("Heiko", ["Lagerist"], ["Lager"], 38, 42, N),
        ],
        requirements=[
            {"days": MOSA, "start": time(6, 0), "end": time(15, 0), "area": "Disposition", "role": "Disponent", "count": 1},
            {"days": MOSA, "start": time(5, 0), "end": time(13, 0), "area": "Fuhrpark", "role": "LKW-Fahrer", "count": 2},
            {"days": MOSA, "start": time(5, 0), "end": time(12, 0), "area": "Verladung", "role": "Verlader", "count": 1},
            {"days": MOFR, "start": time(8, 0), "end": time(16, 0), "area": "Lager", "role": "Lagerist", "count": 1},
        ],
    )

    # ── 5. Autohaus Wadood (Werkstatt & Verkauf) ─────────────────────────────
    _build_business(
        db, "Autohaus Wadood", models.IndustryType.automotive,
        area_names=["Werkstatt", "Verkauf", "Ersatzteile", "Serviceannahme"],
        role_names=["KFZ-Mechatroniker", "Verkäufer", "Serviceberater", "Lagerist"],
        employees=[
            ("Wadood", ["Verkäufer"], ["Verkauf"], 40, 45, S),
            ("Kevin", ["KFZ-Mechatroniker"], ["Werkstatt"], 38, 42, N),
            ("Tobias", ["KFZ-Mechatroniker"], ["Werkstatt"], 38, 42, J),
            ("Nina", ["Serviceberater"], ["Serviceannahme"], 35, 40, N),
            ("Lars", ["Lagerist"], ["Ersatzteile"], 35, 40, N),
        ],
        requirements=[
            {"days": MOFR, "start": time(8, 0), "end": time(17, 0), "area": "Werkstatt", "role": "KFZ-Mechatroniker", "count": 2},
            {"days": MOFR, "start": time(7, 30), "end": time(16, 30), "area": "Serviceannahme", "role": "Serviceberater", "count": 1},
            {"days": MOSA, "start": time(9, 0), "end": time(18, 0), "area": "Verkauf", "role": "Verkäufer", "count": 1},
            {"days": MOFR, "start": time(8, 0), "end": time(17, 0), "area": "Ersatzteile", "role": "Lagerist", "count": 1},
        ],
    )

    # ── Verfügbarkeiten & Abwesenheiten für Demo Bistro (aktuelle Woche) ──────
    # Nur wenn Demo Bistro in diesem Durchlauf neu angelegt wurde
    if bistro is None:
        db.commit()
        print("[Seed] Fehlende Beispielbetriebe ergänzt (falls vorhanden).")
        return

    today = date.today()
    week_start = today - timedelta(days=today.weekday())
    emps = {e.name: e for e in db.query(models.Employee).filter_by(business_id=bistro.id).all()}
    avail_data = [
        ("Ali", 0, True, time(9, 0), time(23, 0)),
        ("Ali", 1, True, time(9, 0), time(23, 0)),
        ("Ali", 2, False, None, None),
        ("Lena", 0, True, time(9, 0), time(16, 0)),
        ("Lena", 1, True, time(9, 0), time(16, 0)),
        ("Max", 0, True, time(14, 0), time(23, 0)),
    ]
    for name, off, avail, frm, until in avail_data:
        if name in emps:
            db.add(models.Availability(
                employee_id=emps[name].id, date=week_start + timedelta(off),
                is_available=avail, available_from=frm, available_until=until,
            ))
    if "Sara" in emps:
        db.add(models.Absence(
            employee_id=emps["Sara"].id, absence_type=models.AbsenceType.sick,
            start_date=week_start + timedelta(3), end_date=week_start + timedelta(3),
            comment="Erkältung", approved=True,
        ))

    db.commit()
    print("[Seed] Demo-Daten angelegt: Demo Bistro, WISKA Hoppmann, Goldies Itzstedt, A & M Transporte, Autohaus Wadood.")
