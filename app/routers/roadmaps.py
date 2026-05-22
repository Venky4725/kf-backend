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
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if batch_id:
        return roadmap_service.list_by_batch(db, batch_id)
    return roadmap_service.list(db)


@router.get("/{roadmap_id}", response_model=WeeklyRoadmapResponse)
def get_roadmap(
    roadmap_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return roadmap_service.get_full(db, roadmap_id)


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
