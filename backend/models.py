from sqlalchemy import (
    Column, Integer, String, Float, Boolean, Date, Time, DateTime,
    ForeignKey, Text, Enum as SAEnum
)
from sqlalchemy.orm import relationship, declarative_base
from datetime import datetime
import enum

Base = declarative_base()


class IndustryType(str, enum.Enum):
    restaurant = "restaurant"
    retail = "retail"
    factory = "factory"


class ExperienceLevel(str, enum.Enum):
    junior = "junior"
    normal = "normal"
    senior = "senior"


class AbsenceType(str, enum.Enum):
    vacation = "vacation"
    sick = "sick"
    school = "school"
    other = "other"


class Business(Base):
    __tablename__ = "businesses"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    industry = Column(SAEnum(IndustryType), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    opening_hours = relationship("OpeningHour", back_populates="business", cascade="all, delete-orphan")
    areas = relationship("Area", back_populates="business", cascade="all, delete-orphan")
    roles = relationship("Role", back_populates="business", cascade="all, delete-orphan")
    employees = relationship("Employee", back_populates="business", cascade="all, delete-orphan")
    shift_requirements = relationship("ShiftRequirement", back_populates="business", cascade="all, delete-orphan")
    generated_shifts = relationship("GeneratedShift", back_populates="business", cascade="all, delete-orphan")


class OpeningHour(Base):
    __tablename__ = "opening_hours"

    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id"), nullable=False)
    weekday = Column(Integer, nullable=False)  # 0=Monday, 6=Sunday
    open_time = Column(Time, nullable=True)
    close_time = Column(Time, nullable=True)
    is_closed = Column(Boolean, default=False)

    business = relationship("Business", back_populates="opening_hours")


class Area(Base):
    __tablename__ = "areas"

    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id"), nullable=False)
    name = Column(String(100), nullable=False)

    business = relationship("Business", back_populates="areas")
    employee_areas = relationship("EmployeeArea", back_populates="area", cascade="all, delete-orphan")
    shift_requirements = relationship("ShiftRequirement", back_populates="area")


class Role(Base):
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id"), nullable=False)
    name = Column(String(100), nullable=False)

    business = relationship("Business", back_populates="roles")
    employee_roles = relationship("EmployeeRole", back_populates="role", cascade="all, delete-orphan")
    shift_requirements = relationship("ShiftRequirement", back_populates="role")


class Employee(Base):
    __tablename__ = "employees"

    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id"), nullable=False)
    name = Column(String(200), nullable=False)
    target_hours_per_week = Column(Float, default=40.0)
    max_hours_per_week = Column(Float, default=48.0)
    preferred_days_off = Column(String(50), default="")  # comma-separated weekday numbers
    qualifications = Column(Text, default="")
    experience_level = Column(SAEnum(ExperienceLevel), default=ExperienceLevel.normal)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    business = relationship("Business", back_populates="employees")
    employee_roles = relationship("EmployeeRole", back_populates="employee", cascade="all, delete-orphan")
    employee_areas = relationship("EmployeeArea", back_populates="employee", cascade="all, delete-orphan")
    availabilities = relationship("Availability", back_populates="employee", cascade="all, delete-orphan")
    absences = relationship("Absence", back_populates="employee", cascade="all, delete-orphan")
    shift_assignments = relationship("ShiftAssignment", back_populates="employee")


class EmployeeRole(Base):
    __tablename__ = "employee_roles"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    role_id = Column(Integer, ForeignKey("roles.id"), nullable=False)

    employee = relationship("Employee", back_populates="employee_roles")
    role = relationship("Role", back_populates="employee_roles")


class EmployeeArea(Base):
    __tablename__ = "employee_areas"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    area_id = Column(Integer, ForeignKey("areas.id"), nullable=False)

    employee = relationship("Employee", back_populates="employee_areas")
    area = relationship("Area", back_populates="employee_areas")


class Availability(Base):
    __tablename__ = "availability"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    date = Column(Date, nullable=False)
    is_available = Column(Boolean, default=True)
    available_from = Column(Time, nullable=True)
    available_until = Column(Time, nullable=True)
    preferred_shift = Column(String(100), default="")
    comment = Column(Text, default="")

    employee = relationship("Employee", back_populates="availabilities")


class Absence(Base):
    __tablename__ = "absences"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    absence_type = Column(SAEnum(AbsenceType), nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    comment = Column(Text, default="")
    approved = Column(Boolean, default=False)

    employee = relationship("Employee", back_populates="absences")


class ShiftRequirement(Base):
    __tablename__ = "shift_requirements"

    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id"), nullable=False)
    area_id = Column(Integer, ForeignKey("areas.id"), nullable=False)
    role_id = Column(Integer, ForeignKey("roles.id"), nullable=True)
    # Either a specific date or a recurring weekday (0=Monday)
    specific_date = Column(Date, nullable=True)
    weekday = Column(Integer, nullable=True)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    required_count = Column(Integer, default=1)
    is_active = Column(Boolean, default=True)

    business = relationship("Business", back_populates="shift_requirements")
    area = relationship("Area", back_populates="shift_requirements")
    role = relationship("Role", back_populates="shift_requirements")


class GeneratedShift(Base):
    __tablename__ = "generated_shifts"

    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id"), nullable=False)
    requirement_id = Column(Integer, ForeignKey("shift_requirements.id"), nullable=True)
    area_id = Column(Integer, ForeignKey("areas.id"), nullable=False)
    role_id = Column(Integer, ForeignKey("roles.id"), nullable=True)
    date = Column(Date, nullable=False)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    required_count = Column(Integer, default=1)
    assigned_count = Column(Integer, default=0)
    is_understaffed = Column(Boolean, default=False)
    understaffed_reason = Column(Text, default="")
    week_start = Column(Date, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    business = relationship("Business", back_populates="generated_shifts")
    area = relationship("Area")
    role = relationship("Role")
    assignments = relationship("ShiftAssignment", back_populates="shift", cascade="all, delete-orphan")


class ShiftAssignment(Base):
    __tablename__ = "shift_assignments"

    id = Column(Integer, primary_key=True, index=True)
    shift_id = Column(Integer, ForeignKey("generated_shifts.id"), nullable=False)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    assigned_at = Column(DateTime, default=datetime.utcnow)

    shift = relationship("GeneratedShift", back_populates="assignments")
    employee = relationship("Employee", back_populates="shift_assignments")
