# Backend Maintenance Scripts

This directory contains scripts for backend maintenance, testing, and troubleshooting.

## Quick Start

### 1. Health Check (Run First)
```bash
python scripts/quick_health_check.py
```
Performs rapid health checks to ensure the backend is working correctly.

### 2. Database Migration (If Needed)
```bash
python scripts/backend_stabilization_migration.py
```
Runs database migrations to add missing columns, indexes, and enum values.

### 3. Stability Tests (Verify Fixes)
```bash
python scripts/test_backend_stability.py
```
Comprehensive test suite to validate all backend functionality.

---

## Script Descriptions

### `quick_health_check.py`
**Purpose:** Quick health check of the backend system

**What it checks:**
- Database connection
- Required tables exist
- Critical columns exist
- Enum values (attendance_status)
- Foreign key constraints
- Performance indexes
- Data integrity

**When to use:**
- After deployment
- Before running tests
- When troubleshooting issues
- As part of monitoring

**Output:**
- ✅ Green checkmarks for passing checks
- ❌ Red X for failing checks
- ⚠️  Yellow warning for non-critical issues

---

### `backend_stabilization_migration.py`
**Purpose:** Database migration for backend stabilization

**What it does:**
- Adds `notifications.edited_at` column
- Ensures `attendance_status` enum includes LATE
- Verifies foreign key constraints
- Adds performance indexes
- Validates data integrity

**When to use:**
- After pulling latest backend changes
- When deploying to new environment
- When database schema is out of sync

**Safety:**
- Uses `IF NOT EXISTS` clauses
- Non-destructive operations
- Can be run multiple times safely

**Output:**
- Step-by-step migration progress
- Success/failure for each operation
- Summary of changes made

---

### `test_backend_stability.py`
**Purpose:** Comprehensive backend functionality tests

**What it tests:**
- Intern creation (with batch_id and batch_name)
- Batch tech lead assignment (single and multiple)
- Tech lead display format (A/B, A only, Unassigned)
- Notification system (sender tracking, listing)
- Attendance system (status validation, LATE support)
- API response consistency

**When to use:**
- After making backend changes
- Before deploying to production
- When troubleshooting specific features
- As part of CI/CD pipeline

**Output:**
- ✅ PASS for successful tests
- ❌ FAIL for failed tests with error details
- Summary with pass/fail count

---

### Legacy Scripts (Existing)

#### `add_attendance_unique_constraint.py`
Adds unique constraint to attendance table (user_id, day).

#### `add_late_status_to_enum.py`
Adds LATE status to attendance_status enum.

#### `assign_tech_leads_to_batches.py`
Helper script to assign tech leads to batches.

#### `check_attendance_schema.py`
Checks attendance table schema.

#### `check_profile_constraints.py`
Checks profile table constraints.

#### `clean_duplicate_attendance.py`
Removes duplicate attendance records.

#### `diagnose_409_error.py`
Diagnoses 409 Conflict errors.

#### `fix_tech_lead_batch_assignment.py`
Fixes tech lead batch assignments.

#### `test_attendance_endpoints.py`
Tests attendance API endpoints.

#### `test_dashboard_endpoints.py`
Tests dashboard API endpoints.

#### `test_late_status.py`
Tests LATE status functionality.

---

## Recommended Workflow

### Initial Setup
```bash
# 1. Check health
python scripts/quick_health_check.py

# 2. Run migrations if needed
python scripts/backend_stabilization_migration.py

# 3. Verify with tests
python scripts/test_backend_stability.py
```

### After Code Changes
```bash
# 1. Run tests
python scripts/test_backend_stability.py

# 2. Check health
python scripts/quick_health_check.py
```

### Troubleshooting
```bash
# 1. Check health to identify issues
python scripts/quick_health_check.py

# 2. Run specific diagnostic scripts
python scripts/diagnose_409_error.py
python scripts/check_attendance_schema.py

# 3. Run migrations if needed
python scripts/backend_stabilization_migration.py

# 4. Verify fix with tests
python scripts/test_backend_stability.py
```

---

## Common Issues and Solutions

### Issue: "Unassigned" showing for batches with tech leads
**Solution:**
```bash
# The batch enrichment fix is already in the code
# Just restart the application
```

### Issue: LATE status not working
**Solution:**
```bash
# Run migration to add LATE to enum
python scripts/backend_stabilization_migration.py
```

### Issue: Duplicate attendance records
**Solution:**
```bash
# Clean duplicates and add constraint
python scripts/clean_duplicate_attendance.py
python scripts/add_attendance_unique_constraint.py
```

### Issue: Intern creation failing
**Solution:**
```bash
# Check profile constraints
python scripts/check_profile_constraints.py

# Run health check
python scripts/quick_health_check.py
```

---

## Environment Variables

All scripts use the same environment variables as the main application:

```bash
DATABASE_URL=postgresql+psycopg2://user:pass@localhost:5432/dbname
```

Set in `.env` file or export before running scripts.

---

## Exit Codes

All scripts follow standard exit code conventions:
- `0` - Success
- `1` - Failure

This allows integration with CI/CD pipelines:
```bash
python scripts/test_backend_stability.py && echo "Tests passed" || echo "Tests failed"
```

---

## Logging

All scripts use the application's logging configuration:
- INFO: Normal operations
- WARNING: Non-critical issues
- ERROR: Failures
- DEBUG: Detailed information (set LOG_LEVEL=DEBUG)

---

## Contributing

When adding new scripts:
1. Follow the naming convention: `verb_noun.py`
2. Add docstring with purpose and usage
3. Use the application's logger
4. Return proper exit codes
5. Update this README

---

## Support

For issues with scripts:
1. Check script output for error messages
2. Review `BACKEND_AUDIT_REPORT.txt`
3. Check application logs
4. Run health check to identify root cause

---

## Script Dependencies

All scripts require:
- Python 3.10+
- SQLAlchemy
- Application dependencies (see `requirements.txt`)

Install with:
```bash
pip install -r requirements.txt
```
