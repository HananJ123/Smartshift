from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_
from typing import List, Optional
from datetime import date

import models
import schemas


# ── Business ──────────────────────────────────────────────────────────────────

def get_businesses(db: Session) -> List[models.Business]:
    return db.query(models.Business).options(
        joinedload(models.Business.opening_hours)
    ).all()


def get_business(db: Session, business_id: int) -> Optional[models.Business]:
    return db.query(models.Business).options(
        joinedload(models.Business.opening_hours),
        joinedload(models.Business.areas),
        joinedload(models.Business.roles),
    ).filter(models.Business.id == business_id).first()


def create_business(db: Session, data: schemas.BusinessCreate) -> models.Business:
    business = models.Business(name=data.name, industry=data.industry)
    db.add(business)
    db.flush()

    for oh in (data.opening_hours or []):
        db.add(models.OpeningHour(business_id=business.id, **oh.dict()))

    # Create default areas based on industry
    default_areas = {
        models.IndustryType.restaurant: ["Service", "Küche", "Bar", "Kasse"],
        models.IndustryType.retail: ["Kasse", "Verkauf", "Lager", "Warenannahme"],
        models.IndustryType.factory: ["Produktion", "Verpackung", "Lager", "Qualitätskontrolle"],
    }
    default_roles = {
        models.IndustryType.restaurant: ["Kellner", "Koch", "Barkeeper", "Kassierer"],
        models.IndustryType.retail: ["Kassierer", "Verkäufer", "Lagerist", "Filialleiter"],
        models.IndustryType.factory: ["Maschinenführer", "Verpacker", "Lagerist", "QS-Prüfer"],
    }

    for area_name in default_areas.get(data.industry, []):
        db.add(models.Area(business_id=business.id, name=area_name))
    for role_name in default_roles.get(data.industry, []):
        db.add(models.Role(business_id=business.id, name=role_name))

    db.commit()
    db.refresh(business)
    return business


def update_business(db: Session, business_id: int, data: schemas.BusinessUpdate) -> Optional[models.Business]:
    business = db.query(models.Business).filter(models.Business.id == business_id).first()
    if not business:
        return None
    for field, value in data.dict(exclude_none=True).items():
        setattr(business, field, value)
    db.commit()
    db.refresh(business)
    return business


def delete_business(db: Session, business_id: int) -> bool:
    business = db.query(models.Business).filter(models.Business.id == business_id).first()
    if not business:
        return False
    db.delete(business)
    db.commit()
    return True


# ── Areas & Roles ──────────────────────────────────────────────────────────────

def get_areas(db: Session, business_id: int) -> List[models.Area]:
    return db.query(models.Area).filter(models.Area.business_id == business_id).all()


def create_area(db: Session, business_id: int, data: schemas.AreaCreate) -> models.Area:
    area = models.Area(business_id=business_id, name=data.name)
    db.add(area)
    db.commit()
    db.refresh(area)
    return area


def delete_area(db: Session, area_id: int) -> bool:
    area = db.query(models.Area).filter(models.Area.id == area_id).first()
    if not area:
        return False
    db.delete(area)
    db.commit()
    return True


def get_roles(db: Session, business_id: int) -> List[models.Role]:
    return db.query(models.Role).filter(models.Role.business_id == business_id).all()


def create_role(db: Session, business_id: int, data: schemas.RoleCreate) -> models.Role:
    role = models.Role(business_id=business_id, name=data.name)
    db.add(role)
    db.commit()
    db.refresh(role)
    return role


def delete_role(db: Session, role_id: int) -> bool:
    role = db.query(models.Role).filter(models.Role.id == role_id).first()
    if not role:
        return False
    db.delete(role)
    db.commit()
    return True


# ── Employees ──────────────────────────────────────────────────────────────────

def get_employees(db: Session, business_id: int) -> List[models.Employee]:
    return db.query(models.Employee).options(
        joinedload(models.Employee.employee_roles).joinedload(models.EmployeeRole.role),
        joinedload(models.Employee.employee_areas).joinedload(models.EmployeeArea.area),
    ).filter(models.Employee.business_id == business_id).all()


def get_employee(db: Session, employee_id: int) -> Optional[models.Employee]:
    return db.query(models.Employee).options(
        joinedload(models.Employee.employee_roles).joinedload(models.EmployeeRole.role),
        joinedload(models.Employee.employee_areas).joinedload(models.EmployeeArea.area),
    ).filter(models.Employee.id == employee_id).first()


def create_employee(db: Session, business_id: int, data: schemas.EmployeeCreate) -> models.Employee:
    emp = models.Employee(
        business_id=business_id,
        name=data.name,
        target_hours_per_week=data.target_hours_per_week,
        max_hours_per_week=data.max_hours_per_week,
        preferred_days_off=data.preferred_days_off,
        qualifications=data.qualifications,
        experience_level=data.experience_level,
    )
    db.add(emp)
    db.flush()

    for role_id in data.role_ids:
        db.add(models.EmployeeRole(employee_id=emp.id, role_id=role_id))
    for area_id in data.area_ids:
        db.add(models.EmployeeArea(employee_id=emp.id, area_id=area_id))

    db.commit()
    db.refresh(emp)
    return get_employee(db, emp.id)


def update_employee(db: Session, employee_id: int, data: schemas.EmployeeUpdate) -> Optional[models.Employee]:
    emp = db.query(models.Employee).filter(models.Employee.id == employee_id).first()
    if not emp:
        return None

    update_data = data.dict(exclude_none=True)
    role_ids = update_data.pop("role_ids", None)
    area_ids = update_data.pop("area_ids", None)

    for field, value in update_data.items():
        setattr(emp, field, value)

    if role_ids is not None:
        db.query(models.EmployeeRole).filter(models.EmployeeRole.employee_id == employee_id).delete()
        for role_id in role_ids:
            db.add(models.EmployeeRole(employee_id=employee_id, role_id=role_id))

    if area_ids is not None:
        db.query(models.EmployeeArea).filter(models.EmployeeArea.employee_id == employee_id).delete()
        for area_id in area_ids:
            db.add(models.EmployeeArea(employee_id=employee_id, area_id=area_id))

    db.commit()
    return get_employee(db, employee_id)


def delete_employee(db: Session, employee_id: int) -> bool:
    emp = db.query(models.Employee).filter(models.Employee.id == employee_id).first()
    if not emp:
        return False
    db.delete(emp)
    db.commit()
    return True


# ── Availability ───────────────────────────────────────────────────────────────

def get_availabilities(db: Session, business_id: int, start: Optional[date] = None, end: Optional[date] = None):
    q = db.query(models.Availability).join(models.Employee).filter(
        models.Employee.business_id == business_id
    )
    if start:
        q = q.filter(models.Availability.date >= start)
    if end:
        q = q.filter(models.Availability.date <= end)
    return q.all()


def get_employee_availabilities(db: Session, employee_id: int):
    return db.query(models.Availability).filter(
        models.Availability.employee_id == employee_id
    ).order_by(models.Availability.date).all()


def upsert_availability(db: Session, data: schemas.AvailabilityCreate) -> models.Availability:
    existing = db.query(models.Availability).filter(
        and_(
            models.Availability.employee_id == data.employee_id,
            models.Availability.date == data.date,
        )
    ).first()

    if existing:
        for field, value in data.dict().items():
            setattr(existing, field, value)
        db.commit()
        db.refresh(existing)
        return existing

    avail = models.Availability(**data.dict())
    db.add(avail)
    db.commit()
    db.refresh(avail)
    return avail


def delete_availability(db: Session, availability_id: int) -> bool:
    avail = db.query(models.Availability).filter(models.Availability.id == availability_id).first()
    if not avail:
        return False
    db.delete(avail)
    db.commit()
    return True


# ── Absences ───────────────────────────────────────────────────────────────────

def get_absences(db: Session, business_id: int):
    return db.query(models.Absence).join(models.Employee).filter(
        models.Employee.business_id == business_id
    ).order_by(models.Absence.start_date).all()


def get_employee_absences(db: Session, employee_id: int):
    return db.query(models.Absence).filter(
        models.Absence.employee_id == employee_id
    ).order_by(models.Absence.start_date).all()


def create_absence(db: Session, data: schemas.AbsenceCreate) -> models.Absence:
    absence = models.Absence(**data.dict())
    db.add(absence)
    db.commit()
    db.refresh(absence)
    return absence


def update_absence(db: Session, absence_id: int, data: schemas.AbsenceUpdate) -> Optional[models.Absence]:
    absence = db.query(models.Absence).filter(models.Absence.id == absence_id).first()
    if not absence:
        return None
    for field, value in data.dict(exclude_none=True).items():
        setattr(absence, field, value)
    db.commit()
    db.refresh(absence)
    return absence


def delete_absence(db: Session, absence_id: int) -> bool:
    absence = db.query(models.Absence).filter(models.Absence.id == absence_id).first()
    if not absence:
        return False
    db.delete(absence)
    db.commit()
    return True


# ── Shift Requirements ─────────────────────────────────────────────────────────

def get_shift_requirements(db: Session, business_id: int):
    return db.query(models.ShiftRequirement).options(
        joinedload(models.ShiftRequirement.area),
        joinedload(models.ShiftRequirement.role),
    ).filter(models.ShiftRequirement.business_id == business_id).all()


def create_shift_requirement(db: Session, business_id: int, data: schemas.ShiftRequirementCreate) -> models.ShiftRequirement:
    req = models.ShiftRequirement(business_id=business_id, **data.dict())
    db.add(req)
    db.commit()
    db.refresh(req)
    return req


def update_shift_requirement(db: Session, req_id: int, data: schemas.ShiftRequirementUpdate) -> Optional[models.ShiftRequirement]:
    req = db.query(models.ShiftRequirement).filter(models.ShiftRequirement.id == req_id).first()
    if not req:
        return None
    for field, value in data.dict(exclude_none=True).items():
        setattr(req, field, value)
    db.commit()
    db.refresh(req)
    return req


def delete_shift_requirement(db: Session, req_id: int) -> bool:
    req = db.query(models.ShiftRequirement).filter(models.ShiftRequirement.id == req_id).first()
    if not req:
        return False
    db.delete(req)
    db.commit()
    return True


# ── Generated Shifts ───────────────────────────────────────────────────────────

def get_generated_shifts(db: Session, business_id: int, week_start: Optional[date] = None):
    q = db.query(models.GeneratedShift).options(
        joinedload(models.GeneratedShift.area),
        joinedload(models.GeneratedShift.role),
        joinedload(models.GeneratedShift.assignments).joinedload(models.ShiftAssignment.employee),
    ).filter(models.GeneratedShift.business_id == business_id)

    if week_start:
        q = q.filter(models.GeneratedShift.week_start == week_start)

    return q.order_by(models.GeneratedShift.date, models.GeneratedShift.start_time).all()


def delete_generated_shifts(db: Session, business_id: int, week_start: date) -> int:
    shifts = db.query(models.GeneratedShift).filter(
        and_(
            models.GeneratedShift.business_id == business_id,
            models.GeneratedShift.week_start == week_start,
        )
    ).all()
    count = len(shifts)
    for s in shifts:
        db.delete(s)
    db.commit()
    return count
