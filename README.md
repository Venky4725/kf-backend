# Knowledge Factory Backend

FastAPI backend for Knowledge Factory internship management system.

## Quick Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
cp .env.example .env  # Edit with your values

# Run migrations
python scripts/add_late_status_to_enum.py

# Start server
uvicorn app.main:app --reload
```

## Attendance Fix

Fixed LATE status enum error. Run migration:

```bash
python scripts/add_late_status_to_enum.py
```

## Clean Before Push

```bash
# Windows
.\cleanup_cache.ps1

# Linux/Mac
chmod +x cleanup_cache.sh
./cleanup_cache.sh
```

## Scripts

- `scripts/add_late_status_to_enum.py` - Add LATE to enum
- `scripts/check_attendance_schema.py` - Check schema
- `scripts/test_late_status.py` - Test LATE status
- `scripts/clean_duplicate_attendance.py` - Clean duplicates
- `scripts/add_attendance_unique_constraint.py` - Add constraint

See `scripts/README.md` for details.
