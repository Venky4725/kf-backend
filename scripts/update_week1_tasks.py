"""Idempotent updater for Week 1 of the Full Stack track.
Re-run any time — it matches by (tech_stack, week_number, day_index) and updates
title + description in place. Safe to run after every plan rewrite.

Usage:
    python scripts/update_week1_tasks.py
"""
import sys
import os

# allow running from repo root or backend/
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.session import SessionLocal
from app.models.models import WeeklyPlan, Task

TECH_STACK = "Full Stack"
WEEK_NUMBER = 1
PLAN_TITLE = "Python Fundamentals – Part I"
PLAN_DESCRIPTION = (
    "Week 1 (Mon Mar 30 – Sat Apr 4, 2026): Set up your Python environment and "
    "master the fundamentals — syntax, control flow, data structures, OOP, file "
    "handling, and a first taste of NumPy & Pandas. Program runs Mon–Sat."
)

# Each entry: (day_index, day_label, title, activities, outcome)
# Day 1 = Mon, Day 6 = Sat. Sundays are off.
WEEK1 = [
    (
        1, "Mon Mar 30",
        "Orientation + Python Setup",
        "Batch intro, install Python/VS Code/Jupyter, Hello World, variables, data types.",
        "Environment ready, basics understood.",
    ),
    (
        2, "Tue Mar 31",
        "Control Flow & Functions",
        "if/else, loops, list comprehensions, defining & calling functions, scope.",
        "Write logical programs using control flow.",
    ),
    (
        3, "Wed Apr 1",
        "Data Structures",
        "Lists, tuples, sets, dicts; CRUD ops; nested structures; practice problems.",
        "Use all core data structures confidently.",
    ),
    (
        4, "Thu Apr 2",
        "OOP in Python",
        "Classes, objects, inheritance, polymorphism, encapsulation; mini-project: Bank Account class.",
        "Design programs using OOP.",
    ),
    (
        5, "Fri Apr 3",
        "File Handling & Exceptions",
        "Read/write CSV & JSON, try/except, custom exceptions, logging basics.",
        "Handle real-world data files & errors.",
    ),
    (
        6, "Sat Apr 4",
        "NumPy & Pandas Intro",
        "Arrays, vectorized ops, DataFrames, read CSV, basic EDA on a sample dataset.",
        "Perform basic data manipulation.",
    ),
]


def task_description(day_label: str, activities: str, outcome: str) -> str:
    return (
        f"📅 {day_label}\n\n"
        f"🛠 Activities & Exercises:\n{activities}\n\n"
        f"🎯 Learning Outcome:\n{outcome}"
    )


def main() -> None:
    db = SessionLocal()
    try:
        plan = db.query(WeeklyPlan).filter(
            WeeklyPlan.tech_stack == TECH_STACK,
            WeeklyPlan.week_number == WEEK_NUMBER,
        ).first()
        if not plan:
            print(f"❌ No plan found for {TECH_STACK} week {WEEK_NUMBER}. Create it first via the admin UI.")
            sys.exit(1)

        plan.title = PLAN_TITLE
        plan.description = PLAN_DESCRIPTION

        existing = {t.day_index: t for t in db.query(Task).filter(Task.plan_id == plan.id).all()}
        touched = 0
        created = 0

        for day_index, day_label, title, activities, outcome in WEEK1:
            desc = task_description(day_label, activities, outcome)
            t = existing.get(day_index)
            if t:
                t.title = title
                t.description = desc
                touched += 1
            else:
                db.add(Task(plan_id=plan.id, day_index=day_index, title=title, description=desc))
                created += 1

        db.commit()
        print(f"✅ Plan updated: {plan.title}")
        print(f"   Updated {touched} task(s), created {created} task(s).")
    finally:
        db.close()


if __name__ == "__main__":
    main()
