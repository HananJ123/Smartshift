"""
Seed the database with demo data for 'Demo Bistro'.
Only runs if no business exists yet.
"""

from datetime import date, time, timedelta
import models


def seed_demo_data(db):
    if db.query(models.Business).count() > 0:
        return  # already seeded

    # Create the demo business
    business = models.Business(
        name="Demo Bistro",
        industry=models.IndustryType.restaurant,
    )
    db.add(business)
    db.flush()

    # Opening hours (Mon–Sat open, Sun closed)
    WEEKDAYS = range(7)
    for wd in WEEKDAYS:
        if wd == 6:  # Sunday closed
            db.add(models.OpeningHour(business_id=business.id, weekday=wd, is_closed=True))
        else:
            db.add(models.OpeningHour(
                business_id=business.id, weekday=wd,
                open_time=time(9, 0), close_time=time(23, 0), is_closed=False,
            ))

    # Areas
    area_names = ["Service", "Küche", "Bar", "Kasse"]
    areas = {}
    for name in area_names:
        a = models.Area(business_id=business.id, name=name)
        db.add(a)
        db.flush()
        areas[name] = a

    # Roles
    role_names = ["Kellner", "Koch", "Barkeeper", "Kassierer"]
    roles = {}
    for name in role_names:
        r = models.Role(business_id=business.id, name=name)
        db.add(r)
        db.flush()
        roles[name] = r

    # Employees
    def make_employee(name, role_keys, area_keys, target, maximum, level):
        emp = models.Employee(
            business_id=business.id,
            name=name,
            target_hours_per_week=target,
            max_hours_per_week=maximum,
            experience_level=level,
        )
        db.add(emp)
        db.flush()
        for rk in role_keys:
            db.add(models.EmployeeRole(employee_id=emp.id, role_id=roles[rk].id))
        for ak in area_keys:
            db.add(models.EmployeeArea(employee_id=emp.id, area_id=areas[ak].id))
        return emp

    ali = make_employee("Ali", ["Kellner"], ["Service"], 30, 40, models.ExperienceLevel.normal)
    sara = make_employee("Sara", ["Koch"], ["Küche"], 25, 35, models.ExperienceLevel.senior)
    max_ = make_employee("Max", ["Kellner", "Barkeeper"], ["Service", "Bar"], 20, 30, models.ExperienceLevel.junior)
    lena = make_employee("Lena", ["Kassierer"], ["Kasse"], 15, 20, models.ExperienceLevel.normal)
    tom = make_employee("Tom", ["Koch"], ["Küche"], 30, 40, models.ExperienceLevel.normal)

    # Find the Monday of the current week
    today = date.today()
    week_start = today - timedelta(days=today.weekday())

    # Shift requirements: Mon–Sat, lunch + dinner
    def add_req(weekday, start, end, area_name, role_name, count):
        db.add(models.ShiftRequirement(
            business_id=business.id,
            area_id=areas[area_name].id,
            role_id=roles[role_name].id,
            weekday=weekday,
            start_time=start,
            end_time=end,
            required_count=count,
            is_active=True,
        ))

    for wd in range(6):  # Mon–Sat
        # Lunch
        add_req(wd, time(10, 0), time(15, 0), "Service", "Kellner", 2)
        add_req(wd, time(10, 0), time(15, 0), "Küche", "Koch", 1)
        add_req(wd, time(10, 0), time(15, 0), "Kasse", "Kassierer", 1)
        # Dinner
        add_req(wd, time(17, 0), time(22, 0), "Service", "Kellner", 3)
        add_req(wd, time(17, 0), time(22, 0), "Küche", "Koch", 2)
        add_req(wd, time(17, 0), time(22, 0), "Bar", "Barkeeper", 1)

    # Add some availability entries for the current week
    avail_data = [
        (ali, week_start + timedelta(0), True, time(9, 0), time(23, 0)),
        (ali, week_start + timedelta(1), True, time(9, 0), time(23, 0)),
        (ali, week_start + timedelta(2), False, None, None),  # Wednesday off
        (ali, week_start + timedelta(3), True, time(9, 0), time(23, 0)),
        (ali, week_start + timedelta(4), True, time(9, 0), time(23, 0)),
        (sara, week_start + timedelta(0), True, time(9, 0), time(23, 0)),
        (sara, week_start + timedelta(1), True, time(9, 0), time(23, 0)),
        (sara, week_start + timedelta(2), True, time(9, 0), time(23, 0)),
        (max_, week_start + timedelta(0), True, time(14, 0), time(23, 0)),  # only evening
        (max_, week_start + timedelta(1), True, time(9, 0), time(23, 0)),
        (max_, week_start + timedelta(2), True, time(9, 0), time(23, 0)),
        (lena, week_start + timedelta(0), True, time(9, 0), time(16, 0)),  # only mornings
        (lena, week_start + timedelta(1), True, time(9, 0), time(16, 0)),
        (lena, week_start + timedelta(2), True, time(9, 0), time(16, 0)),
        (tom, week_start + timedelta(0), True, time(9, 0), time(23, 0)),
        (tom, week_start + timedelta(1), True, time(9, 0), time(23, 0)),
        (tom, week_start + timedelta(2), True, time(9, 0), time(23, 0)),
        (tom, week_start + timedelta(3), True, time(9, 0), time(23, 0)),
    ]
    for emp, dt, is_avail, frm, until in avail_data:
        db.add(models.Availability(
            employee_id=emp.id,
            date=dt,
            is_available=is_avail,
            available_from=frm,
            available_until=until,
        ))

    # Sara is sick on Thursday
    db.add(models.Absence(
        employee_id=sara.id,
        absence_type=models.AbsenceType.sick,
        start_date=week_start + timedelta(3),
        end_date=week_start + timedelta(3),
        comment="Erkältung",
        approved=True,
    ))

    db.commit()
    print("[Seed] Demo-Daten für 'Demo Bistro' wurden angelegt.")
