from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import date, time, datetime
from models import IndustryType, ExperienceLevel, AbsenceType


# --- Business ---

class OpeningHourBase(BaseModel):
    weekday: int = Field(..., ge=0, le=6)
    open_time: Optional[time] = None
    close_time: Optional[time] = None
    is_closed: bool = False


class OpeningHourCreate(OpeningHourBase):
    pass


class OpeningHourOut(OpeningHourBase):
    id: int
    business_id: int

    class Config:
        from_attributes = True


class BusinessCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    industry: IndustryType
    opening_hours: Optional[List[OpeningHourCreate]] = []


class BusinessUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    industry: Optional[IndustryType] = None


class BusinessOut(BaseModel):
    id: int
    name: str
    industry: IndustryType
    created_at: datetime
    opening_hours: List[OpeningHourOut] = []

    class Config:
        from_attributes = True


# --- Area & Role ---

class AreaCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)


class AreaOut(BaseModel):
    id: int
    business_id: int
    name: str

    class Config:
        from_attributes = True


class RoleCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)


class RoleOut(BaseModel):
    id: int
    business_id: int
    name: str

    class Config:
        from_attributes = True


# --- Employee ---

class EmployeeCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    target_hours_per_week: float = Field(40.0, ge=0, le=168)
    max_hours_per_week: float = Field(48.0, ge=0, le=168)
    preferred_days_off: str = ""
    qualifications: str = ""
    experience_level: ExperienceLevel = ExperienceLevel.normal
    role_ids: List[int] = []
    area_ids: List[int] = []


class EmployeeUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    target_hours_per_week: Optional[float] = Field(None, ge=0, le=168)
    max_hours_per_week: Optional[float] = Field(None, ge=0, le=168)
    preferred_days_off: Optional[str] = None
    qualifications: Optional[str] = None
    experience_level: Optional[ExperienceLevel] = None
    is_active: Optional[bool] = None
    role_ids: Optional[List[int]] = None
    area_ids: Optional[List[int]] = None


class EmployeeOut(BaseModel):
    id: int
    business_id: int
    name: str
    target_hours_per_week: float
    max_hours_per_week: float
    preferred_days_off: str
    qualifications: str
    experience_level: ExperienceLevel
    is_active: bool
    roles: List[RoleOut] = []
    areas: List[AreaOut] = []

    class Config:
        from_attributes = True


# --- Availability ---

class AvailabilityCreate(BaseModel):
    employee_id: int
    date: date
    is_available: bool = True
    available_from: Optional[time] = None
    available_until: Optional[time] = None
    preferred_shift: str = ""
    comment: str = ""


class AvailabilityUpdate(BaseModel):
    is_available: Optional[bool] = None
    available_from: Optional[time] = None
    available_until: Optional[time] = None
    preferred_shift: Optional[str] = None
    comment: Optional[str] = None


class AvailabilityOut(BaseModel):
    id: int
    employee_id: int
    date: date
    is_available: bool
    available_from: Optional[time]
    available_until: Optional[time]
    preferred_shift: str
    comment: str

    class Config:
        from_attributes = True


# --- Absence ---

class AbsenceCreate(BaseModel):
    employee_id: int
    absence_type: AbsenceType
    start_date: date
    end_date: date
    comment: str = ""

    @validator("end_date")
    def end_after_start(cls, v, values):
        if "start_date" in values and v < values["start_date"]:
            raise ValueError("end_date must be >= start_date")
        return v


class AbsenceUpdate(BaseModel):
    absence_type: Optional[AbsenceType] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    comment: Optional[str] = None
    approved: Optional[bool] = None


class AbsenceOut(BaseModel):
    id: int
    employee_id: int
    absence_type: AbsenceType
    start_date: date
    end_date: date
    comment: str
    approved: bool

    class Config:
        from_attributes = True


# --- Shift Requirement ---

class ShiftRequirementCreate(BaseModel):
    area_id: int
    role_id: Optional[int] = None
    specific_date: Optional[date] = None
    weekday: Optional[int] = Field(None, ge=0, le=6)
    start_time: time
    end_time: time
    required_count: int = Field(1, ge=1, le=50)
    is_active: bool = True

    @validator("end_time")
    def end_after_start(cls, v, values):
        if "start_time" in values and v <= values["start_time"]:
            raise ValueError("end_time must be after start_time")
        return v


class ShiftRequirementUpdate(BaseModel):
    area_id: Optional[int] = None
    role_id: Optional[int] = None
    specific_date: Optional[date] = None
    weekday: Optional[int] = Field(None, ge=0, le=6)
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    required_count: Optional[int] = Field(None, ge=1, le=50)
    is_active: Optional[bool] = None


class ShiftRequirementOut(BaseModel):
    id: int
    business_id: int
    area_id: int
    role_id: Optional[int]
    specific_date: Optional[date]
    weekday: Optional[int]
    start_time: time
    end_time: time
    required_count: int
    is_active: bool
    area: Optional[AreaOut] = None
    role: Optional[RoleOut] = None

    class Config:
        from_attributes = True


# --- Generated Shift & Assignments ---

class ShiftAssignmentOut(BaseModel):
    id: int
    shift_id: int
    employee_id: int
    employee: Optional[EmployeeOut] = None

    class Config:
        from_attributes = True


class GeneratedShiftOut(BaseModel):
    id: int
    business_id: int
    area_id: int
    role_id: Optional[int]
    date: date
    start_time: time
    end_time: time
    required_count: int
    assigned_count: int
    is_understaffed: bool
    understaffed_reason: str
    area: Optional[AreaOut] = None
    role: Optional[RoleOut] = None
    assignments: List[ShiftAssignmentOut] = []

    class Config:
        from_attributes = True


# --- Scheduler ---

class ScheduleRequest(BaseModel):
    week_start: date  # Monday of the week to schedule


class ScheduleResult(BaseModel):
    shifts_created: int
    assignments_made: int
    understaffed_count: int
    warnings: List[str] = []


# --- Gemini Assistant ---

class GeminiAnalysisRequest(BaseModel):
    week_start: date


class GeminiAnalysisResult(BaseModel):
    analysis: str
    available: bool
