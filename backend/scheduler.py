"""
Smartshift Scheduling Algorithm
================================
Heuristic-based shift assignment. No AI/ML involved.

Steps:
1. Load all shift requirements for the target week
2. For each requirement (sorted by date + time):
   a. Find all employees matching role/area constraints
   b. Filter out absent or unavailable employees
   c. Filter out employees already working at the same time
   d. Filter out employees who would exceed max weekly hours
   e. Sort candidates: fewer hours first, then by experience (senior > normal > junior)
   f. Assign top N candidates
3. Mark understaffed shifts and record reasons
4. Persist result to DB
"""

from datetime import date, time, timedelta, datetime
from typing import List, Dict, Tuple, Optional
from sqlalchemy.orm import Session, joinedload

import models
import crud


EXPERIENCE_PRIORITY = {
    models.ExperienceLevel.senior: 0,
    models.ExperienceLevel.normal: 1,
    models.ExperienceLevel.junior: 2,
}


def _time_to_hours(t: time) -> float:
    return t.hour + t.minute / 60


def _shift_duration(start: time, end: time) -> float:
    """Dauer in Stunden. Wenn end <= start, laeuft die Schicht ueber Mitternacht."""
    s = _time_to_hours(start)
    e = _time_to_hours(end)
    if e <= s:
        e += 24  # Schicht endet am Folgetag (z.B. 18:00-02:00)
    return e - s


def _shift_datetimes(d: date, start: time, end: time) -> Tuple[datetime, datetime]:
    """Wandelt Datum + Start/Endzeit in echte Start-/End-Zeitpunkte um.
    Bei Schichten ueber Mitternacht liegt das Ende am Folgetag."""
    start_dt = datetime.combine(d, start)
    end_dt = datetime.combine(d, end)
    if end_dt <= start_dt:
        end_dt += timedelta(days=1)
    return start_dt, end_dt


def _times_overlap(s1: time, e1: time, s2: time, e2: time) -> bool:
    """Return True if two time intervals overlap (exclusive boundaries)."""
    return s1 < e2 and s2 < e1


def _datetimes_overlap(s1: datetime, e1: datetime, s2: datetime, e2: datetime) -> bool:
    """True, wenn sich zwei Zeitraeume ueberschneiden (auch ueber Mitternacht)."""
    return s1 < e2 and s2 < e1


def _is_absent(employee: models.Employee, check_date: date) -> Tuple[bool, str]:
    for absence in employee.absences:
        if absence.start_date <= check_date <= absence.end_date:
            label = {
                models.AbsenceType.vacation: "Urlaub",
                models.AbsenceType.sick: "Krank",
                models.AbsenceType.school: "Schule/Uni",
                models.AbsenceType.other: "Abwesenheit",
            }.get(absence.absence_type, "Abwesend")
            return True, f"{label} ({absence.start_date}–{absence.end_date})"
    return False, ""


def _get_availability(employee: models.Employee, check_date: date) -> Optional[models.Availability]:
    for av in employee.availabilities:
        if av.date == check_date:
            return av
    return None


def _is_available_for_shift(employee: models.Employee, check_date: date, start: time, end: time) -> Tuple[bool, str]:
    avail = _get_availability(employee, check_date)

    if avail is not None:
        if not avail.is_available:
            return False, "Als nicht verfügbar eingetragen"
        if avail.available_from and avail.available_until:
            # Bei Schichten ueber Mitternacht nur den Teil bis Mitternacht pruefen
            seg_end = end if _time_to_hours(end) > _time_to_hours(start) else time(23, 59)
            if not _times_overlap(avail.available_from, avail.available_until, start, seg_end):
                return (
                    False,
                    f"Nur {avail.available_from.strftime('%H:%M')}–{avail.available_until.strftime('%H:%M')} verfügbar",
                )
    # No availability entry = assume available
    return True, ""


def _employee_role_ids(employee: models.Employee) -> List[int]:
    return [er.role_id for er in employee.employee_roles]


def _employee_area_ids(employee: models.Employee) -> List[int]:
    return [ea.area_id for ea in employee.employee_areas]


def generate_schedule(db: Session, business_id: int, week_start: date) -> Dict:
    """
    Main entry point. Generates shift assignments for the given week.
    Returns a summary dict with counts and warnings.
    """
    # Ensure week_start is a Monday
    if week_start.weekday() != 0:
        raise ValueError("week_start must be a Monday")

    week_end = week_start + timedelta(days=6)

    # Delete existing schedule for this week
    crud.delete_generated_shifts(db, business_id, week_start)

    # Load all employees with their relations eagerly
    employees: List[models.Employee] = db.query(models.Employee).options(
        joinedload(models.Employee.employee_roles),
        joinedload(models.Employee.employee_areas),
        joinedload(models.Employee.absences),
        joinedload(models.Employee.availabilities),
    ).filter(
        models.Employee.business_id == business_id,
        models.Employee.is_active == True,
    ).all()

    # Load shift requirements
    requirements: List[models.ShiftRequirement] = db.query(models.ShiftRequirement).filter(
        models.ShiftRequirement.business_id == business_id,
        models.ShiftRequirement.is_active == True,
    ).all()

    if not requirements:
        return {"shifts_created": 0, "assignments_made": 0, "understaffed_count": 0, "warnings": ["Keine Schichtanforderungen definiert."]}

    # Track weekly hours per employee: {employee_id: hours}
    weekly_hours: Dict[int, float] = {emp.id: 0.0 for emp in employees}

    # Track assignments per employee as real datetime ranges (handles overnight shifts)
    # {employee_id: [(start_dt, end_dt)]}
    daily_assignments: Dict[int, List[Tuple[datetime, datetime]]] = {emp.id: [] for emp in employees}

    # Expand requirements into concrete dates for the week
    def _in_range(d: date) -> bool:
        """Prüft optionalen Gültigkeitszeitraum der Anforderung."""
        if getattr(req, "valid_from", None) and d < req.valid_from:
            return False
        if getattr(req, "valid_until", None) and d > req.valid_until:
            return False
        return True

    concrete_reqs = []
    for req in requirements:
        if req.specific_date and week_start <= req.specific_date <= week_end:
            concrete_reqs.append((req.specific_date, req))
        elif getattr(req, "is_daily", False):
            # Gilt für jeden Tag der Woche (innerhalb des optionalen Zeitraums)
            for offset in range(7):
                d = week_start + timedelta(days=offset)
                if _in_range(d):
                    concrete_reqs.append((d, req))
        elif req.weekday is not None:
            target_date = week_start + timedelta(days=req.weekday)
            if _in_range(target_date):
                concrete_reqs.append((target_date, req))

    # Sort by date, then start_time — process earlier shifts first
    concrete_reqs.sort(key=lambda x: (x[0], x[1].start_time))

    total_assignments = 0
    understaffed_count = 0
    warnings = []
    shifts_created = 0

    for req_date, req in concrete_reqs:
        duration = _shift_duration(req.start_time, req.end_time)
        req_start_dt, req_end_dt = _shift_datetimes(req_date, req.start_time, req.end_time)

        # Find eligible employees for this requirement
        candidates = []
        rejection_reasons: Dict[str, int] = {}

        for emp in employees:
            # Check role match (if requirement specifies a role)
            if req.role_id and req.role_id not in _employee_role_ids(emp):
                rejection_reasons["Falsche Rolle"] = rejection_reasons.get("Falsche Rolle", 0) + 1
                continue

            # Check area match
            if req.area_id and req.area_id not in _employee_area_ids(emp):
                rejection_reasons["Falscher Bereich"] = rejection_reasons.get("Falscher Bereich", 0) + 1
                continue

            # Check absence
            absent, reason = _is_absent(emp, req_date)
            if absent:
                rejection_reasons[reason] = rejection_reasons.get(reason, 0) + 1
                continue

            # Check availability
            available, reason = _is_available_for_shift(emp, req_date, req.start_time, req.end_time)
            if not available:
                rejection_reasons[reason] = rejection_reasons.get(reason, 0) + 1
                continue

            # Check for time conflicts (with real datetimes, also across midnight)
            has_conflict = False
            for (a_start_dt, a_end_dt) in daily_assignments[emp.id]:
                if _datetimes_overlap(a_start_dt, a_end_dt, req_start_dt, req_end_dt):
                    has_conflict = True
                    break
            if has_conflict:
                rejection_reasons["Zeitkonflikt"] = rejection_reasons.get("Zeitkonflikt", 0) + 1
                continue

            # Check max weekly hours
            if weekly_hours[emp.id] + duration > emp.max_hours_per_week:
                rejection_reasons["Max. Wochenstunden erreicht"] = rejection_reasons.get("Max. Wochenstunden erreicht", 0) + 1
                continue

            candidates.append(emp)

        # Sort candidates: prioritize those with fewer hours, then by experience level
        candidates.sort(key=lambda e: (
            weekly_hours[e.id],                     # fewer hours first
            EXPERIENCE_PRIORITY[e.experience_level], # senior first for key roles
        ))

        # Prefer seniors for first slot if this is a critical area (first requirement of day)
        # This is handled by the experience sort above.

        # Assign top N candidates
        assigned_count = 0
        for emp in candidates[:req.required_count]:
            weekly_hours[emp.id] += duration
            daily_assignments[emp.id].append((req_start_dt, req_end_dt))
            assigned_count += 1

        is_understaffed = assigned_count < req.required_count
        understaffed_reason = ""
        if is_understaffed:
            understaffed_count += 1
            missing = req.required_count - assigned_count
            if rejection_reasons:
                reason_parts = [f"{count}x {reason}" for reason, count in rejection_reasons.items()]
                understaffed_reason = f"Fehlend: {missing} Person(en). Gründe: {'; '.join(reason_parts)}"
            else:
                understaffed_reason = f"Fehlend: {missing} Person(en). Nicht genug qualifizierte Mitarbeiter verfügbar."
            warnings.append(
                f"{req_date.strftime('%d.%m.%Y')} {req.start_time.strftime('%H:%M')}–{req.end_time.strftime('%H:%M')} "
                f"(Bereich {req.area_id}): {understaffed_reason}"
            )

        # Persist the generated shift
        shift = models.GeneratedShift(
            business_id=business_id,
            requirement_id=req.id,
            area_id=req.area_id,
            role_id=req.role_id,
            date=req_date,
            start_time=req.start_time,
            end_time=req.end_time,
            required_count=req.required_count,
            assigned_count=assigned_count,
            is_understaffed=is_understaffed,
            understaffed_reason=understaffed_reason,
            week_start=week_start,
        )
        db.add(shift)
        db.flush()

        # Persist assignments
        assigned_employees = candidates[:req.required_count]
        for emp in assigned_employees:
            db.add(models.ShiftAssignment(shift_id=shift.id, employee_id=emp.id))

        total_assignments += assigned_count
        shifts_created += 1

    db.commit()

    return {
        "shifts_created": shifts_created,
        "assignments_made": total_assignments,
        "understaffed_count": understaffed_count,
        "warnings": warnings,
    }
