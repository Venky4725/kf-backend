# app/routers/roadmaps.py

from uuid import UUID
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.schemas.roadmap import (
    RoadmapImportRequest, 
    RoadmapBulkImportResponse, 
    WeeklyRoadmapResponse, 
    WeeklyRoadmapShortResponse,
    RoadmapPreviewRequest,
    RoadmapPreviewResponse
)
from app.services.roadmap_service import roadmap_service

router = APIRouter(prefix="/roadmaps", tags=["Roadmaps"])


@router.post("/import", response_model=RoadmapBulkImportResponse, status_code=status.HTTP_201_CREATED)
def import_roadmap(
    payload: RoadmapImportRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if current_user.role not in ["ADMIN", "TECHNICAL_LEAD"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Admins and Tech Leads can import roadmaps"
        )
    return roadmap_service.import_roadmap(db, payload, current_user.id)


@router.post("/preview", response_model=RoadmapPreviewResponse)
def preview_roadmap(
    payload: RoadmapPreviewRequest,
    current_user=Depends(get_current_user),
):
    if current_user.role not in ["ADMIN", "TECHNICAL_LEAD"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Admins and Tech Leads can preview roadmaps"
        )
    entries = roadmap_service.preview_roadmap(payload.content)
    return {
        "entries": entries,
        "entries_count": len(entries)
    }


@router.get("", response_model=List[WeeklyRoadmapShortResponse])
def list_roadmaps(
    batch_id: Optional[UUID] = None,
    role: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    # Enforce role-based filtering for interns
    if current_user.role == "INTERN":
        # Interns can only see roadmaps for their batch
        effective_batch_id = batch_id or current_user.batch_id
        if not effective_batch_id:
             return []
        
        # Fetch both specific role and ALL roadmaps
        from sqlalchemy import or_
        from app.models.roadmap import WeeklyRoadmap
        from app.utils.role_utils import normalize_role
        
        normalized_intern_role = normalize_role(current_user.intern_role)
        query = db.query(WeeklyRoadmap).filter(
            WeeklyRoadmap.batch_id == effective_batch_id,
            or_(
                WeeklyRoadmap.role == normalized_intern_role,
                WeeklyRoadmap.role.in_(["GENERAL", "ALL"])
            )
        )
        return query.order_by(WeeklyRoadmap.created_at.desc()).all()

    if batch_id:
        if role:
            from app.utils.role_utils import normalize_role
            role = normalize_role(role)
        return roadmap_service.list_by_batch(db, batch_id, role)
    return roadmap_service.list(db)


@router.get("/{roadmap_id}", response_model=WeeklyRoadmapResponse)
def get_roadmap(
    roadmap_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    roadmap = roadmap_service.get_full(db, roadmap_id)
    # Permission check for Interns
    if current_user.role == "INTERN":
        if roadmap.batch_id != current_user.batch_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only access roadmaps from your own batch"
            )
        # Optional: strictly check role too?
        if roadmap.role:
            from app.utils.role_utils import normalize_role
            normalized_intern_role = normalize_role(current_user.intern_role)
            if roadmap.role not in (normalized_intern_role, "GENERAL", "ALL"):
                 raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You can only access roadmaps for your specific role"
                )
    return roadmap


@router.delete("/{roadmap_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_roadmap(
    roadmap_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if current_user.role not in ["ADMIN", "TECHNICAL_LEAD"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Admins and Tech Leads can delete roadmaps"
        )
    roadmap_service.delete(db, roadmap_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
