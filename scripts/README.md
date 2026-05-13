# Database Migration and Testing Scripts

This directory contains scripts for managing attendance database migrations and testing attendance endpoints.

## Scripts Overview

### 1. `check_attendance_schema.py` ⭐ NEW
Diagnostic tool to check the current attendance table schema and enum status.

**Purpose:**
- Checks if attendance table exists
- Shows all column definitions
- Checks if attendance_status enum exists
- Shows current enum values
- Identifies if LATE status is missing
- Shows sample attendance records

**Usage:**
```bash
python scripts/check_attendance_schema.py
```

**When to run:**
- Before running migrations
- When diagnosing enum-related errors
- To verify database schema

**Output:**
```
============================================================
ATTENDANCE SCHEMA DIAGNOSTIC
============================================================

1. Checking if attendance table exists...
✅ Attendance table exists

2. Attendance table columns:
   - id: UUID (nullable=False)
   - user_id: UUID (nullable=False)
   - day: DATE (nullable=False)
   - status: VARCHAR (nullable=False)
   - created_at: TIMESTAMP (nullable=True)

3. Checking for attendance_status enum type...
✅ attendance_status enum type exists
   Enum values: PRESENT, ABSENT, LEAVE
   ⚠️  LATE is MISSING - this is the problem!

4. Checking attendance.status column type...
   Column: status
   Data type: USER-DEFINED
   UDT name: attendance_status
   
   ⚠️  Column is using attendance_status ENUM type
   This means the enum MUST include LATE value
   
   ACTION REQUIRED:
   Run: python scripts/add_late_status_to_enum.py
```

---

### 2. `add_late_status_to_enum.py` ⭐ NEW
Adds 'LATE' status to the attendance_status enum type.

**Purpose:**
- Fixes the production error: `invalid input value for enum attendance_status: "LATE"`
- Checks if attendance_status enum exists
- Adds LATE value to the enum if missing
- Creates the enum if it doesn't exist
- Verifies the migration

**Usage:**
```bash
python scripts/add_late_status_to_enum.py
```

**When to run:**
- When you get enum validation errors for LATE status
- After running `check_attendance_schema.py` and confirming LATE is missing
- Before deploying code that uses LATE status

**Output:**
```
============================================================
ATTENDANCE STATUS ENUM MIGRATION
============================================================

Step 1: Checking if attendance_status enum exists...
✅ attendance_status enum exists

Step 2: Checking current enum values...
Current values: PRESENT, ABSENT, LEAVE

Step 3: Adding LATE value to enum...
✅ Successfully added LATE to attendance_status enum

Step 4: Verifying migration...
Updated values: PRESENT, ABSENT, LEAVE, LATE

============================================================
✅ MIGRATION COMPLETED SUCCESSFULLY!
============================================================

The attendance_status enum now includes:
  - PRESENT
  - ABSENT
  - LEAVE
  - LATE

You can now create attendance records with status='LATE'
```

**Safety:**
- Idempotent: Safe to run multiple times
- Uses `ADD VALUE IF NOT EXISTS` (PostgreSQL 9.1+)
- Creates enum if it doesn't exist
- Verifies changes after migration

---

### 3. `clean_duplicate_attendance.py`
Removes duplicate attendance records before adding the unique constraint.

**Purpose:**
- Identifies duplicate attendance records (same user + same day)
- Keeps the most recent record for each user+day combination
- Deletes older duplicate records

**Usage:**
```bash
python scripts/clean_duplicate_attendance.py
```

**When to run:**
- Before adding the unique constraint
- If you suspect duplicate records exist in the database

**Output:**
- Shows count of duplicate combinations found
- Asks for confirmation before deleting
- Reports number of records deleted

---

### 4. `add_attendance_unique_constraint.py`
Adds a unique constraint to the attendance table to prevent future duplicates.

**Purpose:**
- Adds database-level constraint: `UNIQUE (user_id, day)`
- Prevents duplicate attendance records at the database level
- Ensures data integrity

**Usage:**
```bash
python scripts/add_attendance_unique_constraint.py
```

**When to run:**
- After cleaning duplicates with `clean_duplicate_attendance.py`
- Only needs to be run once

**Prerequisites:**
- No duplicate records in the database
- Run `clean_duplicate_attendance.py` first if duplicates exist

**Output:**
- Checks if constraint already exists
- Checks for duplicate records
- Adds constraint if safe to do so
- Reports success or failure

---

### 5. `test_attendance_endpoints.py`
Comprehensive test suite for all attendance endpoints and features.

**Purpose:**
- Tests distribution analytics endpoint
- Tests individual intern analytics endpoint
- Tests pending attendance endpoint
- Tests attendance listing with enhanced fields
- Tests duplicate prevention logic

**Usage:**
```bash
python scripts/test_attendance_endpoints.py
```

**When to run:**
- After implementing attendance fixes
- After database migrations
- Before deploying to production
- Regularly to verify system health

**Tests Performed:**

#### Distribution Analytics
- Fetches attendance distribution (counts by status)
- Verifies percentages add up to 100%
- Tests date range filtering
- Checks data format for pie charts

#### Individual Analytics
- Gets analytics for a sample intern
- Verifies attendance percentage calculation
- Checks trend data format
- Validates all count fields

#### Pending Attendance
- Lists interns for attendance marking
- Verifies `has_attendance` flag accuracy
- Tests date filtering
- Checks batch information

#### Attendance Listing
- Fetches attendance records
- Verifies enhanced fields (user_name, batch_name)
- Tests date filtering
- Checks response format

#### Duplicate Prevention
- Creates attendance record
- Attempts to create duplicate
- Verifies existing record is updated instead
- Cleans up test data

**Output:**
- Detailed test results for each endpoint
- Sample data from responses
- Pass/fail status for each test
- Summary of all tests

---

## Migration Workflow

### Critical Fix: Add LATE Status to Enum

If you're experiencing the error: `invalid input value for enum attendance_status: "LATE"`

#### Step 1: Diagnose the Issue
```bash
python scripts/check_attendance_schema.py
```

This will show you:
- Current enum values
- Whether LATE is missing
- Column type information

#### Step 2: Fix the Enum
```bash
python scripts/add_late_status_to_enum.py
```

This will:
- Add LATE to the attendance_status enum
- Verify the change
- Show updated enum values

#### Step 3: Restart Application
```bash
# Restart your FastAPI application to pick up changes
```

#### Step 4: Test
```bash
python scripts/test_attendance_endpoints.py
```

---

## Full Migration Workflow (New Setup)

### Step 1: Check Schema
```bash
python scripts/check_attendance_schema.py
```

### Step 2: Fix Enum (if needed)
```bash
python scripts/add_late_status_to_enum.py
```

### Step 3: Clean Duplicates
```bash
python scripts/clean_duplicate_attendance.py
```

**Expected Output:**
```
============================================================
Clean Duplicate Attendance Records
============================================================

🔍 Checking for duplicate attendance records...
⚠️  Found 5 duplicate user+day combinations
   - User abc123... on 2026-05-10: 2 records
   - User def456... on 2026-05-11: 3 records
   ...

❓ Delete older duplicate records? (yes/no): yes

✅ Deleted 8 duplicate records
✅ Kept the most recent record for each user+day combination

============================================================
✅ Cleanup completed successfully!
============================================================

Next step: Run the migration script to add unique constraint
  python scripts/add_attendance_unique_constraint.py
```

### Step 4: Add Unique Constraint
```bash
python scripts/add_attendance_unique_constraint.py
```

**Expected Output:**
```
============================================================
Add Attendance Unique Constraint
============================================================

🔍 Checking if constraint already exists...
✅ No duplicates found

➕ Adding unique constraint...
✅ Unique constraint added successfully!

Constraint details:
  - Name: uq_attendance_user_day
  - Columns: (user_id, day)
  - Effect: Prevents duplicate attendance for same user on same day

============================================================
✅ Migration completed successfully!
============================================================
```

### Step 5: Test Everything
```bash
python scripts/test_attendance_endpoints.py
```

**Expected Output:**
```
============================================================
Attendance Endpoints Test Suite
============================================================

============================================================
TEST: Attendance Distribution Analytics
============================================================

📊 Distribution (All Batches):
   Present: 150 (89.82%)
   Absent: 10 (5.99%)
   Late: 5 (2.99%)
   Leave: 2 (1.20%)
   Total: 167

✅ Percentages add up to 100%
✅ Distribution analytics working correctly

... (more tests) ...

============================================================
TEST SUMMARY
============================================================
✅ PASS - Distribution Analytics
✅ PASS - Individual Analytics
✅ PASS - Pending Attendance
✅ PASS - Attendance Listing
✅ PASS - Duplicate Prevention

============================================================
✅ ALL TESTS PASSED
============================================================
```

---

## Troubleshooting

### Error: "Found duplicate user+day combinations"
**Solution:** Run `clean_duplicate_attendance.py` first to remove duplicates.

### Error: "Constraint already exists"
**Solution:** The constraint is already in place. No action needed.

### Error: "No interns found in database"
**Solution:** Ensure you have test data in the database. The test script needs at least one intern to run properly.

### Error: "Connection refused"
**Solution:** Check that your database is running and the `DATABASE_URL` in `.env` is correct.

### Error: "Permission denied"
**Solution:** Ensure the database user has permission to alter tables and delete records.

---

## Database Schema Changes

### Before Migration
```sql
CREATE TABLE attendance (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES profiles(id),
    day DATE NOT NULL,
    status VARCHAR NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE
);
```

### After Migration
```sql
CREATE TABLE attendance (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES profiles(id),
    day DATE NOT NULL,
    status VARCHAR NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE,
    CONSTRAINT uq_attendance_user_day UNIQUE (user_id, day)
);
```

---

## Safety Notes

1. **Backup First:** Always backup your database before running migration scripts.

2. **Test Environment:** Run scripts in a test environment first before production.

3. **Duplicate Handling:** The cleanup script keeps the most recent record. If you need different logic, modify the script.

4. **Rollback:** To remove the constraint:
   ```sql
   ALTER TABLE attendance DROP CONSTRAINT uq_attendance_user_day;
   ```

5. **Idempotent:** All scripts are safe to run multiple times. They check current state before making changes.

---

## Next Steps After Migration

1. ✅ Run all three scripts in order
2. ✅ Verify all tests pass
3. ✅ Update frontend to use new analytics endpoints
4. ✅ Monitor for any issues in production
5. ✅ Document any custom modifications

---

## Support

For issues or questions:
1. Check the test output for specific error messages
2. Review the database logs
3. Verify environment variables in `.env`
4. Check database connection and permissions
