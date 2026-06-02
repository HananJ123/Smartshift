import os
import sys
import csv
import io
from datetime import date, timedelta
from typing import List, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

# Load .env from project root
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(BASE_DIR, ".env"))

import models
import schemas
import crud
import scheduler as sched
import gemini_assistant
from database import init_db, get_db, SessionLocal
from seed import seed_demo_data

app = FastAPI(title="Smartshift API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup():
    init_db()
    db = SessionLocal()
    try:
        seed_demo_data(db)
    finally:
        db.close()


# ── Static frontend ────────────────────────────────────────────────────────────

FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")
app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


@app.get("/", include_in_schema=False)
def root():
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))


# ── Businesses ─────────────────────────────────────────────────────────────────

@app.get("/api/businesses", response_model=List[schemas.BusinessOut])
def list_businesses(db: Session = Depends(get_db)):
    return crud.get_businesses(db)


@app.post("/api/businesses", response_model=schemas.BusinessOut, status_code=201)
def create_business(data: schemas.BusinessCreate, db: Session = Depends(get_db)):
    return crud.create_business(db, data)


@app.get("/api/businesses/{business_id}", response_model=schemas.BusinessOut)
def get_business(business_id: int, db: Session = Depends(get_db)):
    b = crud.get_business(db, business_id)
    if not b:
        raise HTTPException(404, "Betrieb nicht gefunden")
    return b


@app.put("/api/businesses/{business_id}", response_model=schemas.BusinessOut)
def update_business(business_id: int, data: schemas.BusinessUpdate, db: Session = Depends(get_db)):
    b = crud.update_business(db, business_id, data)
    if not b:
        raise HTTPException(404, "Betrieb nicht gefunden")
    return b


@app.delete("/api/businesses/{business_id}")
def delete_business(business_id: int, db: Session = Depends(get_db)):
    if not crud.delete_business(db, business_id):
        raise HTTPException(404, "Betrieb nicht gefunden")
    return {"ok": True}


# ── Areas ──────────────────────────────────────────────────────────────────────

@app.get("/api/businesses/{business_id}/areas", response_model=List[schemas.AreaOut])
def list_areas(business_id: int, db: Session = Depends(get_db)):
    return crud.get_areas(db, business_id)


@app.post("/api/businesses/{business_id}/areas", response_model=schemas.AreaOut, status_code=201)
def create_area(business_id: int, data: schemas.AreaCreate, db: Session = Depends(get_db)):
    return crud.create_area(db, business_id, data)


@app.delete("/api/areas/{area_id}")
def delete_area(area_id: int, db: Session = Depends(get_db)):
    if not crud.delete_area(db, area_id):
        raise HTTPException(404, "Bereich nicht gefunden")
    return {"ok": True}


# ── Roles ──────────────────────────────────────────────────────────────────────

@app.get("/api/businesses/{business_id}/roles", response_model=List[schemas.RoleOut])
def list_roles(business_id: int, db: Session = Depends(get_db)):
    return crud.get_roles(db, business_id)


@app.post("/api/businesses/{business_id}/roles", response_model=schemas.RoleOut, status_code=201)
def create_role(business_id: int, data: schemas.RoleCreate, db: Session = Depends(get_db)):
    return crud.create_role(db, business_id, data)


@app.delete("/api/roles/{role_id}")
def delete_role(role_id: int, db: Session = Depends(get_db)):
    if not crud.delete_role(db, role_id):
        raise HTTPException(404, "Rolle nicht gefunden")
    return {"ok": True}


# ── Employees ──────────────────────────────────────────────────────────────────

@app.get("/api/businesses/{business_id}/employees", response_model=List[schemas.EmployeeOut])
def list_employees(business_id: int, db: Session = Depends(get_db)):
    return crud.get_employees(db, business_id)


@app.post("/api/businesses/{business_id}/employees", response_model=schemas.EmployeeOut, status_code=201)
def create_employee(business_id: int, data: schemas.EmployeeCreate, db: Session = Depends(get_db)):
    return crud.create_employee(db, business_id, data)


@app.get("/api/employees/{employee_id}", response_model=schemas.EmployeeOut)
def get_employee(employee_id: int, db: Session = Depends(get_db)):
    emp = crud.get_employee(db, employee_id)
    if not emp:
        raise HTTPException(404, "Mitarbeiter nicht gefunden")
    return emp


@app.put("/api/employees/{employee_id}", response_model=schemas.EmployeeOut)
def update_employee(employee_id: int, data: schemas.EmployeeUpdate, db: Session = Depends(get_db)):
    emp = crud.update_employee(db, employee_id, data)
    if not emp:
        raise HTTPException(404, "Mitarbeiter nicht gefunden")
    return emp


@app.delete("/api/employees/{employee_id}")
def delete_employee(employee_id: int, db: Session = Depends(get_db)):
    if not crud.delete_employee(db, employee_id):
        raise HTTPException(404, "Mitarbeiter nicht gefunden")
    return {"ok": True}


# ── Availability ───────────────────────────────────────────────────────────────

@app.get("/api/businesses/{business_id}/availabilities", response_model=List[schemas.AvailabilityOut])
def list_availabilities(
    business_id: int,
    start: Optional[date] = Query(None),
    end: Optional[date] = Query(None),
    db: Session = Depends(get_db),
):
    return crud.get_availabilities(db, business_id, start, end)


@app.get("/api/employees/{employee_id}/availabilities", response_model=List[schemas.AvailabilityOut])
def employee_availabilities(employee_id: int, db: Session = Depends(get_db)):
    return crud.get_employee_availabilities(db, employee_id)


@app.post("/api/availabilities", response_model=schemas.AvailabilityOut, status_code=201)
def upsert_availability(data: schemas.AvailabilityCreate, db: Session = Depends(get_db)):
    return crud.upsert_availability(db, data)


@app.delete("/api/availabilities/{availability_id}")
def delete_availability(availability_id: int, db: Session = Depends(get_db)):
    if not crud.delete_availability(db, availability_id):
        raise HTTPException(404, "Verfügbarkeit nicht gefunden")
    return {"ok": True}


# ── Absences ───────────────────────────────────────────────────────────────────

@app.get("/api/businesses/{business_id}/absences", response_model=List[schemas.AbsenceOut])
def list_absences(business_id: int, db: Session = Depends(get_db)):
    return crud.get_absences(db, business_id)


@app.get("/api/employees/{employee_id}/absences", response_model=List[schemas.AbsenceOut])
def employee_absences(employee_id: int, db: Session = Depends(get_db)):
    return crud.get_employee_absences(db, employee_id)


@app.post("/api/absences", response_model=schemas.AbsenceOut, status_code=201)
def create_absence(data: schemas.AbsenceCreate, db: Session = Depends(get_db)):
    return crud.create_absence(db, data)


@app.put("/api/absences/{absence_id}", response_model=schemas.AbsenceOut)
def update_absence(absence_id: int, data: schemas.AbsenceUpdate, db: Session = Depends(get_db)):
    absence = crud.update_absence(db, absence_id, data)
    if not absence:
        raise HTTPException(404, "Abwesenheit nicht gefunden")
    return absence


@app.delete("/api/absences/{absence_id}")
def delete_absence(absence_id: int, db: Session = Depends(get_db)):
    if not crud.delete_absence(db, absence_id):
        raise HTTPException(404, "Abwesenheit nicht gefunden")
    return {"ok": True}


# ── Shift Requirements ─────────────────────────────────────────────────────────

@app.get("/api/businesses/{business_id}/shift-requirements", response_model=List[schemas.ShiftRequirementOut])
def list_shift_requirements(business_id: int, db: Session = Depends(get_db)):
    return crud.get_shift_requirements(db, business_id)


@app.post("/api/businesses/{business_id}/shift-requirements", response_model=schemas.ShiftRequirementOut, status_code=201)
def create_shift_requirement(business_id: int, data: schemas.ShiftRequirementCreate, db: Session = Depends(get_db)):
    return crud.create_shift_requirement(db, business_id, data)


@app.put("/api/shift-requirements/{req_id}", response_model=schemas.ShiftRequirementOut)
def update_shift_requirement(req_id: int, data: schemas.ShiftRequirementUpdate, db: Session = Depends(get_db)):
    req = crud.update_shift_requirement(db, req_id, data)
    if not req:
        raise HTTPException(404, "Schichtanforderung nicht gefunden")
    return req


@app.delete("/api/shift-requirements/{req_id}")
def delete_shift_requirement(req_id: int, db: Session = Depends(get_db)):
    if not crud.delete_shift_requirement(db, req_id):
        raise HTTPException(404, "Schichtanforderung nicht gefunden")
    return {"ok": True}


# ── Schedule Generation ────────────────────────────────────────────────────────

@app.post("/api/businesses/{business_id}/schedule/generate", response_model=schemas.ScheduleResult)
def generate_schedule(business_id: int, request: schemas.ScheduleRequest, db: Session = Depends(get_db)):
    b = crud.get_business(db, business_id)
    if not b:
        raise HTTPException(404, "Betrieb nicht gefunden")
    try:
        result = sched.generate_schedule(db, business_id, request.week_start)
        return result
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.get("/api/businesses/{business_id}/schedule", response_model=List[schemas.GeneratedShiftOut])
def get_schedule(
    business_id: int,
    week_start: Optional[date] = Query(None),
    db: Session = Depends(get_db),
):
    return crud.get_generated_shifts(db, business_id, week_start)


@app.delete("/api/businesses/{business_id}/schedule")
def delete_schedule(
    business_id: int,
    week_start: date = Query(...),
    db: Session = Depends(get_db),
):
    count = crud.delete_generated_shifts(db, business_id, week_start)
    return {"deleted": count}


# ── Export ─────────────────────────────────────────────────────────────────────

@app.get("/api/businesses/{business_id}/schedule/export/csv")
def export_csv(
    business_id: int,
    week_start: Optional[date] = Query(None),
    db: Session = Depends(get_db),
):
    shifts = crud.get_generated_shifts(db, business_id, week_start)

    output = io.StringIO()
    writer = csv.writer(output, delimiter=";")
    writer.writerow(["Datum", "Bereich", "Rolle", "Start", "Ende", "Benötigt", "Zugeteilt", "Status", "Mitarbeiter", "Grund"])

    for shift in shifts:
        employees_str = ", ".join(a.employee.name for a in shift.assignments if a.employee)
        status = "UNTERBESETZT" if shift.is_understaffed else "OK"
        writer.writerow([
            shift.date.strftime("%d.%m.%Y"),
            shift.area.name if shift.area else "",
            shift.role.name if shift.role else "",
            shift.start_time.strftime("%H:%M"),
            shift.end_time.strftime("%H:%M"),
            shift.required_count,
            shift.assigned_count,
            status,
            employees_str,
            shift.understaffed_reason,
        ])

    output.seek(0)
    filename = f"schichtplan_{week_start or 'gesamt'}.csv"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv; charset=utf-8-sig",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ── Gemini Assistant ───────────────────────────────────────────────────────────

@app.post("/api/businesses/{business_id}/gemini-analysis", response_model=schemas.GeminiAnalysisResult)
def gemini_analysis(business_id: int, request: schemas.GeminiAnalysisRequest, db: Session = Depends(get_db)):
    shifts = crud.get_generated_shifts(db, business_id, request.week_start)

    if not shifts:
        return schemas.GeminiAnalysisResult(
            analysis="Kein Schichtplan für diese Woche gefunden. Bitte zuerst einen Plan generieren.",
            available=False,
        )

    # Build summary (anonymized enough — only first name used)
    employee_hours: dict = {}
    shifts_summary = []
    for shift in shifts:
        for assignment in shift.assignments:
            if assignment.employee:
                name = assignment.employee.name
                dur = sched._shift_duration(shift.start_time, shift.end_time)
                employee_hours[name] = employee_hours.get(name, 0) + dur

        shifts_summary.append({
            "date": shift.date.isoformat(),
            "area": shift.area.name if shift.area else "?",
            "role": shift.role.name if shift.role else None,
            "start_time": shift.start_time.strftime("%H:%M"),
            "end_time": shift.end_time.strftime("%H:%M"),
            "required_count": shift.required_count,
            "assigned_count": shift.assigned_count,
            "is_understaffed": shift.is_understaffed,
            "understaffed_reason": shift.understaffed_reason,
        })

    summary = {
        "week_start": request.week_start.isoformat(),
        "shifts_created": len(shifts),
        "assignments_made": sum(s["assigned_count"] for s in shifts_summary),
        "understaffed_count": sum(1 for s in shifts_summary if s["is_understaffed"]),
        "shifts": shifts_summary,
        "employee_hours": employee_hours,
    }

    result = gemini_assistant.analyze_schedule(summary)
    return schemas.GeminiAnalysisResult(**result)
