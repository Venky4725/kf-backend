# app/services/roadmap_service.py

import logging
from uuid import UUID
from typing import List, Optional, Dict, Any

from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.roadmap import WeeklyRoadmap, RoadmapEntry
from app.schemas.roadmap import RoadmapImportRequest, RoadmapBulkImportResponse
from app.services.base import CRUDService
from app.utils.task_parser import parse_roadmap_to_entries

logger = logging.getLogger(__name__)


class RoadmapService(CRUDService[WeeklyRoadmap]):
    model = WeeklyRoadmap
    resource_name = "WeeklyRoadmap"
    table_name = "weekly_roadmaps"

    def import_roadmap(self, db: Session, payload: RoadmapImportRequest, current_user_id: UUID) -> RoadmapBulkImportResponse:
        """Parses raw text and creates a WeeklyRoadmap with entries."""
        try:
            entries_data = parse_roadmap_to_entries(payload.content)
            
            if not entries_data:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No valid roadmap entries found in content."
                )

            # Create the roadmap
            roadmap = WeeklyRoadmap(
                title=payload.title,
                batch_id=payload.batch_id,
                created_by=current_user_id
            )
            db.add(roadmap)
            db.flush()

            # Create entries
            for i, data in enumerate(entries_data):
                entry = RoadmapEntry(
                    roadmap_id=roadmap.id,
                    day_label=data["day"],
                    topic=data["topic"],
                    activities=data["activities"],
                    outcome=data["outcome"],
                    sort_order=i
                )
                db.add(entry)

            db.commit()
            db.refresh(roadmap)

            return RoadmapBulkImportResponse(
                roadmap_id=roadmap.id,
                entries_count=len(roadmap.entries),
                entries=roadmap.entries
            )
        except HTTPException:
            db.rollback()
            raise
        except Exception as e:
            db.rollback()
            logger.error(f"Error importing roadmap: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to import roadmap: {str(e)}"
            )

    def preview_roadmap(self, content: str) -> List[Dict[str, Any]]:
        """Parses raw text and returns a list of entries without saving."""
        return parse_roadmap_to_entries(content)

    def list_by_batch(self, db: Session, batch_id: UUID) -> List[WeeklyRoadmap]:
        return db.query(WeeklyRoadmap).filter(WeeklyRoadmap.batch_id == batch_id).order_by(WeeklyRoadmap.created_at.desc()).all()

    def get_full(self, db: Session, roadmap_id: UUID) -> WeeklyRoadmap:
        roadmap = db.query(WeeklyRoadmap).filter(WeeklyRoadmap.id == roadmap_id).first()
        if not roadmap:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Roadmap not found"
            )
        return roadmap


roadmap_service = RoadmapService()
