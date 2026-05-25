import logging
from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from sqlalchemy import asc

from app.db.session import get_db
from app.models.task import Task
from app.models.weekly_plan import WeeklyPlanDay
from app.schemas.weekly_plan import WeeklyPlanDayResponse, WeeklyPlanCreateRequest
from app.utils.task_parser import parse_weekly_plan
from app.core.dependencies import get_current_user

router = APIRouter(
    prefix="/weekly-plans",
    tags=["Weekly Plans"],
)

logger = logging.getLogger(__name__)

@router.post("/parse", response_model=List[dict])
def parse_weekly_plan_text(content: str = Body(..., embed=True, description="Raw text of the weekly plan")):
    """
    Parses the raw text of a weekly plan into structured JSON.
    """
    try:
        parsed = parse_weekly_plan(content)
        return parsed
    except Exception as e:
        logger.error(f"Error parsing weekly plan: {e}")
        raise HTTPException(status_code=400, detail="Failed to parse weekly plan text.")

@router.post("", response_model=List[WeeklyPlanDayResponse])
def create_weekly_plan(
    request: WeeklyPlanCreateRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Creates a new weekly plan attached to a task.
    Replaces any existing plan for the task.
    """
    # Verify task exists
    task = db.query(Task).filter(Task.id == request.task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # Delete existing plan for this task
    db.query(WeeklyPlanDay).filter(WeeklyPlanDay.task_id == request.task_id).delete()

    created_days = []
    for day_data in request.days:
        new_day = WeeklyPlanDay(
            task_id=request.task_id,
            day=day_data.day,
            topic=day_data.topic,
            activities=day_data.activities,
            outcome=day_data.outcome,
            order_index=day_data.order_index
        )
        db.add(new_day)
        created_days.append(new_day)

    db.commit()
    for day in created_days:
        db.refresh(day)

    return created_days

@router.get("/{task_id}", response_model=List[WeeklyPlanDayResponse])
def get_weekly_plan(
    task_id: UUID,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Retrieves the weekly plan for a specific task.
    """
    # Verify task exists
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    days = db.query(WeeklyPlanDay).filter(
        WeeklyPlanDay.task_id == task_id
    ).order_by(asc(WeeklyPlanDay.order_index)).all()

    return days
