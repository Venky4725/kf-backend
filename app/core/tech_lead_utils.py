# app/core/tech_lead_utils.py
"""
Utility functions for Technical Lead access control.
Handles multi-batch TL assignment (first_tech_lead_id, second_tech_lead_id, third_tech_lead_id).
"""

from sqlalchemy.orm import Session
from sqlalchemy import or_
from uuid import UUID
from typing import List


def get_tech_lead_batch_ids(db: Session, tech_lead_id: UUID) -> List[UUID]:
    """
    Get all batch IDs where the tech lead is assigned (as first, second, or third TL).
    
    Args:
        db: Database session
        tech_lead_id: UUID of the technical lead
    
    Returns:
        List of batch UUIDs where the TL is assigned
    """
    from app.models.batch import Batch
    
    batches = db.query(Batch).filter(
        or_(
            Batch.first_tech_lead_id == tech_lead_id,
            Batch.second_tech_lead_id == tech_lead_id,
            Batch.third_tech_lead_id == tech_lead_id
        )
    ).all()
    
    return [batch.id for batch in batches]


def is_tech_lead_for_batch(db: Session, tech_lead_id: UUID, batch_id: UUID) -> bool:
    """
    Check if a tech lead is assigned to a specific batch (in any TL position).
    
    Args:
        db: Database session
        tech_lead_id: UUID of the technical lead
        batch_id: UUID of the batch to check
    
    Returns:
        True if TL is assigned to the batch, False otherwise
    """
    from app.models.batch import Batch
    
    batch = db.query(Batch).filter(
        Batch.id == batch_id,
        or_(
            Batch.first_tech_lead_id == tech_lead_id,
            Batch.second_tech_lead_id == tech_lead_id,
            Batch.third_tech_lead_id == tech_lead_id
        )
    ).first()
    
    return batch is not None


def is_tech_lead_for_intern(db: Session, tech_lead_id: UUID, intern_id: UUID) -> bool:
    """
    Check if a tech lead has access to a specific intern.
    TL has access if the intern is in any batch where the TL is assigned.
    
    Args:
        db: Database session
        tech_lead_id: UUID of the technical lead
        intern_id: UUID of the intern
    
    Returns:
        True if TL has access to the intern, False otherwise
    """
    from app.models.profile import Profile
    
    # Get intern's batch
    intern = db.get(Profile, intern_id)
    if not intern or not intern.batch_id:
        return False
    
    # Check if TL is assigned to intern's batch
    return is_tech_lead_for_batch(db, tech_lead_id, intern.batch_id)


def get_tech_lead_batch_filter(tech_lead_id: UUID):
    """
    Get SQLAlchemy filter for batches where TL is assigned.
    Use this in queries that need to filter by TL assignment.
    
    Args:
        tech_lead_id: UUID of the technical lead
    
    Returns:
        SQLAlchemy OR filter for all three TL positions
    """
    from app.models.batch import Batch
    
    return or_(
        Batch.first_tech_lead_id == tech_lead_id,
        Batch.second_tech_lead_id == tech_lead_id,
        Batch.third_tech_lead_id == tech_lead_id
    )
