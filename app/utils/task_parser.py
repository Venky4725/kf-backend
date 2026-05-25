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

def parse_weekly_plan(text: str) -> list[dict[str, Any]]:
    """
    Parses a Weekly Learning Plan raw text into a structured list of dictionaries.
    Uses BLOCK-BASED parsing triggered by Day headers.
    """
    if not text:
        return []

    # Detect day rows
    day_regex = re.compile(r"^(Mon|Tue|Wed|Thu|Fri|Sat|Sun)\s+[A-Za-z]+\s+\d+", re.IGNORECASE)
    
    # Headers to ignore
    ignore_headers = {
        "topic / theme", "key activities & exercises", "daily outcome",
        "topic", "theme", "key activities", "activities", "outcome", "day", "date"
    }

    raw_lines = text.strip().split('\n')
    lines = []
    
    is_markdown_table = any(line.strip().startswith('|') for line in raw_lines)
    is_tab_separated = any('\t' in line for line in raw_lines)
    
    for line in raw_lines:
        clean_line = line.strip()
        if not clean_line:
            continue
            
        # Ignore markdown table separators
        if re.match(r'^[\-\s\|:]+$', clean_line) and '|' in clean_line:
            continue
            
        if is_markdown_table and clean_line.startswith('|') and clean_line.endswith('|'):
            # It's a markdown table row, split by | and yield cells
            cells = [c.strip() for c in clean_line.split('|')[1:-1]]
            lines.extend(cells)
        elif is_tab_separated and '\t' in clean_line:
            # It's a tab separated row
            cells = [c.strip() for c in clean_line.split('\t')]
            lines.extend(cells)
        else:
            lines.append(clean_line)

    # Filter out exact header matches
    filtered_lines = [l for l in lines if l.lower() not in ignore_headers]
    
    blocks = []
    current_block = []
    
    for line in filtered_lines:
        if day_regex.match(line):
            if current_block:
                blocks.append(current_block)
            current_block = [line]
        elif current_block:
            current_block.append(line)
            
    if current_block:
        blocks.append(current_block)
        
    results = []
    for i, block in enumerate(blocks):
        day = block[0]
        topic = ""
        activities = ""
        outcome = ""
        
        if len(block) >= 4:
            topic = block[1]
            outcome = block[-1]
            activities = "\n".join(block[2:-1])
        elif len(block) == 3:
            topic = block[1]
            outcome = block[2]
            activities = ""
        elif len(block) == 2:
            topic = block[1]
            outcome = ""
            activities = ""
            
        results.append({
            "day": day,
            "topic": topic,
            "activities": activities,
            "outcome": outcome,
            "order_index": i
        })
        
    return results

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
    Delegates to the newly rewritten block-based parser.
    """
    return parse_weekly_plan(content)

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

if __name__ == "__main__":
    example_text = """
    Topic / Theme
    Key Activities & Exercises
    Daily Outcome
    Mon May 26
    Docker — Containerise Everything
    Docker concepts: images, containers...
    Containerise the complete full-stack application
    
    Tue May 27
    CI/CD — GitHub Actions
    GitHub Actions workflow...
    Fully automated CI/CD pipeline
    """
    import json
    print("Testing block-based parser:")
    print(json.dumps(parse_weekly_plan(example_text), indent=2))
