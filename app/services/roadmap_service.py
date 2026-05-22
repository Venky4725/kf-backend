# app/services/roadmap_service.py

import logging
from uuid import UUID
from typing import List, Optional, Dict, Any

from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.roadmap import WeeklyRoadmap, RoadmapEntry
from app.schemas.roadmap import RoadmapImportRequest, RoadmapBulkImportResponse
from app.services.base import CRUDService

logger = logging.getLogger(__name__)


class RoadmapService(CRUDService[WeeklyRoadmap]):
    model = WeeklyRoadmap
    resource_name = "WeeklyRoadmap"
    table_name = "weekly_roadmaps"

    def import_roadmap(self, db: Session, payload: RoadmapImportRequest, current_user_id: UUID) -> RoadmapBulkImportResponse:
        """Parses raw text and creates a WeeklyRoadmap with entries."""
        try:
            entries_data = self._parse_roadmap_content(payload.content)
            
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
                    day_label=data["day_label"],
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
                entries_count=len(entries_data)
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

    def _parse_roadmap_content(self, content: str) -> List[Dict[str, Any]]:
        """
        Parses block-based roadmap text.
        Format:
        Day
        Topic
        Activities (can be multiline)
        Outcome (can be multiline)
        
        Blocks are usually separated by more than one newline or clear patterns.
        """
        if not content:
            return []

        # Split content into lines and filter empty ones for initial detection
        all_lines = [line.strip() for line in content.split('\n')]
        
        # A block should have at least 2 lines (Day and Topic)
        # We'll use a simple state-based parser to handle multiline activities/outcomes
        
        entries = []
        current_block = []
        
        # Heuristic: A new block starts with a day-like string (Mon, Tue, Wed, Thu, Fri, Sat, Sun, Day X)
        day_patterns = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun", "Day", "Week"]
        
        lines = [line for line in all_lines if line] # Get non-empty lines
        
        i = 0
        while i < len(lines):
            line = lines[i]
            
            # If we see a day-like line, we assume a new block starts
            if any(line.startswith(p) for p in day_patterns):
                # Process previous block if it exists
                if current_block:
                    entries.append(self._format_block(current_block))
                current_block = [line]
            else:
                current_block.append(line)
            i += 1
            
        # Add the last block
        if current_block:
            entries.append(self._format_block(current_block))
            
        return [e for e in entries if e["topic"]] # Filter out headers if they were caught

    def _format_block(self, lines: List[str]) -> Dict[str, Any]:
        """Converts a list of lines into a roadmap entry dictionary."""
        # Minimum requirement: Day and Topic
        if len(lines) < 2:
            return {"day_label": "", "topic": "", "activities": "", "outcome": ""}
            
        day_label = lines[0]
        topic = lines[1]
        
        activities = ""
        outcome = ""
        
        # If there are more lines, try to split them into activities and outcome
        if len(lines) > 2:
            # Look for keywords like "Outcome", "Expected", "Target" to split
            outcome_start_idx = -1
            for j in range(2, len(lines)):
                if any(kw in lines[j] for kw in ["Outcome", "Expected", "Target", "Goal"]):
                    outcome_start_idx = j
                    break
            
            if outcome_start_idx != -1:
                activities = "\n".join(lines[2:outcome_start_idx])
                outcome = "\n".join(lines[outcome_start_idx:])
            else:
                # If no outcome keyword, split roughly in half or put all in activities
                activities = "\n".join(lines[2:])
                
        return {
            "day_label": day_label,
            "topic": topic,
            "activities": activities,
            "outcome": outcome
        }


roadmap_service = RoadmapService()
