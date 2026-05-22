import re
import logging
from datetime import date, datetime
from typing import Any, List, Dict

logger = logging.getLogger(__name__)

# Constants for parsing
MONTHS_RE = "(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|January|February|March|April|May|June|July|August|September|October|November|December)"
WEEKDAYS_RE = "(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun|Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)"
DATE_PATTERN = re.compile(rf"^(?:{WEEKDAYS_RE},?\s*)?{MONTHS_RE}\s+\d+", re.IGNORECASE)
FALLBACK_PATTERN = re.compile(r"^(Day|Session|Week)\s+\d+", re.IGNORECASE)

HEADER_KEYWORDS = {
    "day", "topic / theme", "key activities & exercises", "daily outcome",
    "topic/theme", "key activities", "outcome", "date", "activities", "theme"
}

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
    Parses a training roadmap into Tasks (for TaskService).
    """
    entries = parse_roadmap_to_entries(content)
    tasks = []
    for entry in entries:
        tasks.append({
            "title": entry["topic"],
            "description": _build_description(entry["activities"], entry["outcome"]),
            "due_date": _try_parse_date(entry["day"])
        })
    return tasks

def parse_roadmap_to_entries(content: str) -> list[dict[str, Any]]:
    """
    Core parsing logic that returns a list of dictionaries with:
    day, topic, activities, outcome
    Used for both WeeklyRoadmap and Task bulk import.
    """
    if not content:
        return []

    lines = content.strip().split('\n')
    # Detect tabular format
    pipe_count = sum(1 for line in lines if '|' in line)
    tab_count = sum(1 for line in lines if '\t' in line)
    
    if pipe_count > 1 or tab_count > 1:
        return _parse_roadmap_tabular_to_entries(content)
    else:
        return _parse_roadmap_block_robust(content)

def _parse_roadmap_block_robust(content: str) -> list[dict[str, Any]]:
    """Robust block-based parsing."""
    all_lines = [line.strip() for line in content.split('\n') if line.strip()]
    
    # Filter out exact header matches
    lines = [l for l in all_lines if l.lower() not in HEADER_KEYWORDS]
    
    if not lines:
        return []

    entries = []
    current_entry = None

    for line in lines:
        # Check if this line is a date line (starts a new block)
        is_date = DATE_PATTERN.match(line) or FALLBACK_PATTERN.match(line)
        
        if is_date:
            if current_entry:
                entries.append(_finalize_entry(current_entry))
            current_entry = {"day": line, "content_lines": []}
        elif current_entry:
            current_entry["content_lines"].append(line)
        # Lines before the first date are ignored (could be preamble)

    if current_entry:
        entries.append(_finalize_entry(current_entry))

    return entries

def _finalize_entry(entry_dict: Dict[str, Any]) -> Dict[str, Any]:
    """Finalizes an entry by splitting content lines into topic, activities, and outcome."""
    lines = entry_dict["content_lines"]
    day = entry_dict["day"]
    
    topic = lines[0] if lines else ""
    activities = ""
    outcome = ""
    
    if len(lines) > 1:
        # Search for outcome keywords to find split point
        outcome_start_idx = -1
        outcome_keywords = ["outcome", "expected", "target", "goal", "result"]
        for j in range(1, len(lines)):
            if any(kw in lines[j].lower() for kw in outcome_keywords):
                outcome_start_idx = j
                break
        
        if outcome_start_idx != -1:
            # We found an outcome marker
            activities = "\n".join(lines[1:outcome_start_idx])
            outcome = "\n".join(lines[outcome_start_idx:])
        else:
            # No marker found, split based on remaining count
            if len(lines) == 2:
                # Just Topic and one more line -> that line is Activities
                activities = lines[1]
            else:
                # Multiple lines: Topic, then some Activities, last one is Outcome
                activities = "\n".join(lines[1:-1])
                outcome = lines[-1]
                
    return {
        "day": day,
        "topic": topic,
        "activities": activities,
        "outcome": outcome
    }

def _parse_roadmap_tabular_to_entries(content: str) -> list[dict[str, Any]]:
    """Parses tabular format (pipes or tabs) into entries."""
    lines = content.strip().split('\n')
    entries = []
    
    # Detect delimiter: | or \t
    delimiter = '|'
    if '\t' in lines[0] and '|' not in lines[0]:
        delimiter = '\t'

    header_skipped = False
    
    for line in lines:
        if not line.strip():
            continue
            
        columns = [c.strip() for c in line.split(delimiter)]
        if len(columns) < 2:
            continue
            
        # Skip header rows
        if not header_skipped:
            if any(kw in columns[0].lower() or kw in columns[1].lower() for kw in HEADER_KEYWORDS):
                header_skipped = True
                continue
        
        # Skip markdown table separator |---|---|
        if all(re.match(r'^[\-\s\:]+$', c) for c in columns if c):
            continue

        entries.append({
            "day": columns[0],
            "topic": columns[1],
            "activities": columns[2] if len(columns) > 2 else "",
            "outcome": columns[3] if len(columns) > 3 else ""
        })
            
    return entries

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
    Attempts to parse a date string into a date object.
    """
    clean_date = date_str.strip()
    
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
            if dt.year == 1900:
                dt = dt.replace(year=current_year)
            return dt.date()
        except ValueError:
            continue
            
    logger.warning(f"Could not parse date: {date_str}")
    return None
