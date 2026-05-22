import re
import logging
from datetime import date, datetime
from typing import Any

logger = logging.getLogger(__name__)

def parse_simple_tasks(content: str) -> list[dict[str, Any]]:
    """
    Parses a simple task list.
    Handles:
    - Task 1: Title
    - 1. Title
    - - Title
    - * Title
    """
    if not content:
        return []

    lines = content.strip().split('\n')
    tasks = []
    
    # Regex to match common prefixes
    # 1. "Task 1: " or "Task 1 - "
    # 2. "1. " or "1) "
    # 3. "- " or "* "
    prefix_re = re.compile(r'^(\s*(Task\s+\d+[:\-]\s*|\d+[\.\)]\s*|[\-\*]\s*))', re.IGNORECASE)

    for line in lines:
        clean_line = line.strip()
        if not clean_line:
            continue
            
        # Remove prefix if found
        match = prefix_re.match(clean_line)
        if match:
            title = clean_line[match.end():].strip()
        else:
            title = clean_line
            
        if title:
            tasks.append({
                "title": title,
                "description": None,
                "due_date": None
            })
            
    return tasks

def parse_roadmap_tasks(content: str) -> list[dict[str, Any]]:
    """
    Parses a training roadmap. Supports both tabular and block-based formats.
    Tabular: Date | Topic | Activities | Outcome
    Block: 
        Line 1: Date
        Line 2: Topic
        Line 3: Activities
        Line 4: Outcome
    """
    if not content:
        return []

    # Detect format: if '|' is present in multiple lines, assume tabular
    lines = content.strip().split('\n')
    pipe_count = sum(1 for line in lines if '|' in line)
    
    if pipe_count > 1:
        return _parse_roadmap_tabular(content)
    else:
        return _parse_roadmap_block(content)

def _parse_roadmap_tabular(content: str) -> list[dict[str, Any]]:
    """Existing tabular parser logic."""
    lines = content.strip().split('\n')
    tasks = []
    
    # Detect delimiter: | or \t
    delimiter = '|'
    if '\t' in lines[0] and '|' not in lines[0]:
        delimiter = '\t'

    header_skipped = False
    
    for line in lines:
        if not line.strip():
            continue
            
        # Split by delimiter
        columns = [c.strip() for c in line.split(delimiter)]
        
        # Basic validation: need at least 2 columns (Date, Topic)
        if len(columns) < 2:
            continue
            
        # Skip header if it contains keywords
        if not header_skipped:
            header_keywords = ["day", "date", "topic", "activity", "outcome"]
            if any(kw in columns[0].lower() or kw in columns[1].lower() for kw in header_keywords):
                header_skipped = True
                continue
        
        # Also skip markdown table separator |---|---|
        if all(re.match(r'^[\-\s\:]+$', c) for c in columns if c):
            continue

        raw_date = columns[0]
        title = columns[1]
        
        activities = columns[2] if len(columns) > 2 else ""
        outcome = columns[3] if len(columns) > 3 else ""
        
        description = _build_description(activities, outcome)
        due_date = _try_parse_date(raw_date)

        if title:
            tasks.append({
                "title": title,
                "description": description,
                "due_date": due_date
            })
            
    return tasks

def _parse_roadmap_block(content: str) -> list[dict[str, Any]]:
    """
    Parses block-based roadmap.
    Line 1: Date
    Line 2: Title
    Line 3: Activities
    Line 4: Outcome
    """
    # Filter out empty lines to get continuous blocks of data
    lines = [line.strip() for line in content.split('\n') if line.strip()]
    tasks = []
    
    # Process in chunks of 4
    for i in range(0, len(lines), 4):
        chunk = lines[i:i+4]
        if len(chunk) < 2: # Need at least date and title
            continue
            
        raw_date = chunk[0]
        title = chunk[1]
        activities = chunk[2] if len(chunk) > 2 else ""
        outcome = chunk[3] if len(chunk) > 3 else ""
        
        description = _build_description(activities, outcome)
        due_date = _try_parse_date(raw_date)

        if title:
            tasks.append({
                "title": title,
                "description": description,
                "due_date": due_date
            })
            
    return tasks

def _build_description(activities: str, outcome: str) -> str | None:
    """Helper to build description from activities and outcome."""
    desc_parts = []
    if activities:
        desc_parts.append(f"Activities:\n{activities}")
    if outcome:
        desc_parts.append(f"Expected Outcome:\n{outcome}")
    
    return "\n\n".join(desc_parts) if desc_parts else None

def _try_parse_date(date_str: str) -> date | None:
    """
    Attempts to parse a date string like 'Thu Apr 2', 'Apr 2', '2024-04-02', etc.
    """
    # Clean up common noise
    clean_date = date_str.strip()
    
    # Common formats
    formats = [
        "%a %b %d",   # Thu Apr 2
        "%b %d",      # Apr 2
        "%d %b",      # 2 Apr
        "%Y-%m-%d",   # 2024-04-02
        "%d/%m/%Y",   # 02/04/2024
        "%m/%d/%Y",   # 04/02/2024
        "%d-%m-%Y",   # 02-04-2024
    ]
    
    current_year = date.today().year
    
    for fmt in formats:
        try:
            dt = datetime.strptime(clean_date, fmt)
            # If year wasn't parsed (defaulted to 1900), set to current year
            if dt.year == 1900:
                dt = dt.replace(year=current_year)
            return dt.date()
        except ValueError:
            continue
            
    # Try custom parsing for "April 2nd" etc. if needed
    # For now, return None if no match
    logger.warning(f"Could not parse date: {date_str}")
    return None
