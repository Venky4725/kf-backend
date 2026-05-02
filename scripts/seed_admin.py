"""
DEV SEED — populates the database with one user per role plus enough sample
data for every dashboard to render with content.

All three test users share the same password: Pass@123

Logins (all use password "Pass@123"):
    Admin :  pravalikan@coastalseven.com
    TL    :  tl.pravalikan@coastalseven.com
    Intern:  intern.pravalikan@coastalseven.com

Why three emails for one human?
    The users table enforces UNIQUE on email (correct — sessions and tokens
    key off it). To test all three views you need three rows. The role
    prefix makes it obvious which view you'll land in.

Usage:
    cd backend
    python -m scripts.seed_admin
"""
from datetime import date, timedelta
from app.db.session import SessionLocal, engine, Base
from app.models import models  # noqa: ensures models are registered
from app.models.models import (
    User, UserRole, UserStatus, Batch, WeeklyPlan, Task,
    Attendance, AttendanceStatus,
)
from app.core.security import hash_password


PASSWORD = "Pass@123"
ADMIN_EMAIL  = "pravalikan@coastalseven.com"
TL_EMAIL     = "tl.pravalikan@coastalseven.com"
INTERN_EMAIL = "intern.pravalikan@coastalseven.com"


def get_or_create_user(db, *, email, name, role, **extra):
    user = db.query(User).filter(User.email == email).first()
    if user:
        # Ensure the password and ACTIVE status are correct on every run
        user.password_hash = hash_password(PASSWORD)
        user.status = UserStatus.ACTIVE
        for k, v in extra.items():
            setattr(user, k, v)
        return user, False
    user = User(
        email=email,
        name=name,
        role=role,
        status=UserStatus.ACTIVE,
        password_hash=hash_password(PASSWORD),
        **extra,
    )
    db.add(user)
    db.flush()
    return user, True


def main():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        # ── 1. Admin
        admin, _ = get_or_create_user(
            db, email=ADMIN_EMAIL, name="Pravalika N (Admin)", role=UserRole.ADMIN,
        )

        # ── 2. Technical Lead
        tl, _ = get_or_create_user(
            db, email=TL_EMAIL, name="Pravalika N (TL)", role=UserRole.TECHNICAL_LEAD,
        )

        # ── 3. Batches (Guntur) — tech stack determined after interns are uploaded
        batch = db.query(Batch).filter(Batch.tl_id == tl.id).first()
        if not batch:
            batch = Batch(
                name="Guntur Batch 2026",
                district="Guntur",
                tech_stack="Multi-Stack",  # Will be segregated after interns are uploaded
                start_date=date(2026, 5, 1),  # internship starts May 1, 2026
                duration_weeks=8,
                tl_id=tl.id,
            )
            db.add(batch)
            db.flush()

        # ── 3b. Create a second batch in Ananthapur
        ananthapur_batch = db.query(Batch).filter(Batch.district == "Ananthapur").first()
        if not ananthapur_batch:
            ananthapur_batch = Batch(
                name="Ananthapur Batch 2026",
                district="Ananthapur",
                tech_stack="Multi-Stack",  # Will be segregated after interns are uploaded
                start_date=date(2026, 5, 8),
                duration_weeks=8,
                tl_id=tl.id,
            )
            db.add(ananthapur_batch)
            db.flush()

        # ── 4. Intern (linked to the batch) — tech stack will be assigned later
        intern, _ = get_or_create_user(
            db, email=INTERN_EMAIL, name="Pravalika N (Intern)", role=UserRole.INTERN,
            tech_stack="Frontend", batch_id=batch.id,  # Example: can be Frontend, Backend, AI/ML, etc.
        )

        # ── 5. Weekly plans across multiple stacks
        plans_data = [
            # Frontend track
            (1, "Frontend", "Week 1: HTML, CSS & Responsive Design",
                ["Setup dev environment", "Build responsive landing page", "CSS Grid & Flexbox"]),
            (2, "Frontend", "Week 2: JavaScript & DOM Manipulation",
                ["ES6 syntax", "Event handling", "Build interactive components"]),
            (3, "Frontend", "Week 3: React Fundamentals",
                ["Components & Props", "Hooks & State", "Build a todo app"]),
            (4, "Frontend", "Week 4: Advanced React",
                ["Context API", "Custom Hooks", "Performance optimization"]),

            # Backend track
            (1, "Backend", "Week 1: Node.js & Express Basics",
                ["Setup Node environment", "Express server", "Routing fundamentals"]),
            (2, "Backend", "Week 2: Databases & ORM",
                ["SQL basics", "Database design", "Query optimization"]),
            (3, "Backend", "Week 3: APIs & Authentication",
                ["REST principles", "JWT tokens", "Security best practices"]),
            (4, "Backend", "Week 4: Advanced Backend",
                ["Caching strategies", "Microservices", "Deployment"]),

            # AI/ML track
            (1, "AI/ML", "Week 1: Python & Data Fundamentals",
                ["Python basics", "NumPy & Pandas", "Data exploration"]),
            (2, "AI/ML", "Week 2: Data Visualization & Analysis",
                ["Matplotlib & Seaborn", "Statistical analysis", "Data storytelling"]),
            (3, "AI/ML", "Week 3: Machine Learning Basics",
                ["Supervised learning", "Model training", "Evaluation metrics"]),
            (4, "AI/ML", "Week 4: Advanced ML & Deployment",
                ["Deep learning intro", "Model optimization", "Production deployment"]),
        ]
        for week_num, stack, title, tasks in plans_data:
            existing = db.query(WeeklyPlan).filter(
                WeeklyPlan.week_number == week_num, WeeklyPlan.tech_stack == stack
            ).first()
            if existing:
                continue
            plan = WeeklyPlan(
                week_number=week_num, tech_stack=stack, title=title,
                description=f"Curriculum for week {week_num}.", created_by=admin.id,
            )
            db.add(plan)
            db.flush()
            for i, t in enumerate(tasks, 1):
                db.add(Task(plan_id=plan.id, title=t, day_index=i))

        # ── 6. Attendance — mark intern present on every weekday since batch start
        # (only if batch has actually started)
        today = date.today()
        if batch.start_date <= today:
            d = batch.start_date
            while d <= today:
                if d.weekday() < 6:
                    exists = db.query(Attendance).filter(
                        Attendance.user_id == intern.id, Attendance.day == d
                    ).first()
                    if not exists:
                        db.add(Attendance(
                            user_id=intern.id, day=d, status=AttendanceStatus.PRESENT,
                        ))
                d += timedelta(days=1)

        # ── 7. Sample announcement (so the dashboard has visible content)
        from app.models.models import Announcement
        if not db.query(Announcement).first():
            db.add(Announcement(
                title="Welcome to Knowledge Factory!",
                body="The Guntur internship begins May 1, 2026. Check your weekly plans and check in daily.",
                kind="ANNOUNCEMENT",
                created_by=admin.id,
            ))
            db.add(Announcement(
                title="Hackathon: Build-a-Thon 2026",
                body="A 24-hour build-a-thon will be held in week 4. Form teams of 3-4 and prepare your idea pitch.",
                kind="HACKATHON",
                starts_on=date(2026, 5, 22),
                ends_on=date(2026, 5, 23),
                created_by=admin.id,
            ))

        db.commit()

        print("=" * 68)
        print("  Knowledge Factory — dev seed complete")
        print("=" * 68)
        print(f"  Password (all three accounts): {PASSWORD}")
        print()
        print(f"  Admin login :  {ADMIN_EMAIL}")
        print(f"  TL    login :  {TL_EMAIL}")
        print(f"  Intern login:  {INTERN_EMAIL}")
        print()
        print(f"  Batch       : {batch.name}")
        print(f"  District    : {batch.district}")
        print(f"  Stack       : {batch.tech_stack}")
        print(f"  Starts      : {batch.start_date}  (internship not yet started)")
        print()
        print("  Open http://localhost:5173 after starting both servers.")
        print("=" * 68)

    finally:
        db.close()


if __name__ == "__main__":
    main()
