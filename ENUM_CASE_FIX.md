# Fix: PostgreSQL Enum Case Mismatch

## Date: May 5, 2026

---

## 🚨 PROBLEM

### Symptom
```
ERROR: invalid input value for enum attendance_status: "LATE"
DETAIL: Valid values are: present, absent, late, leave
```

### Impact
- ❌ 500 Internal Server Error
- ❌ Cannot create attendance
- ❌ Cannot update attendance
- ❌ Database rejects uppercase values

---

## 🔍 ROOT CAUSE

### Database vs Backend Mismatch

**PostgreSQL Enum** (lowercase):
```sql
CREATE TYPE attendance_status AS ENUM ('present', 'absent', 'late', 'leave');
```

**Backend Code** (uppercase):
```python
# ❌ WRONG
valid_statuses = {"PRESENT", "ABSENT", "LATE", "LEAVE"}
normalized = v.strip().upper()  # Converts to uppercase
```

**Result**: Database rejects uppercase values!

---

## ✅ SOLUTION

### Normalize to Lowercase (Match Database)

Change all status normalization from **uppercase** to **lowercase**.

---

## 📝 CHANGES APPLIED

### 1. Updated Schema Validators
**File**: `app/schemas/attendance.py`

**Before** (WRONG):
```python
@field_validator('status')
@classmethod
def validate_status(cls, v: str) -> str:
    normalized = v.strip().upper()  # ❌ Uppercase
    valid_statuses = {"PRESENT", "ABSENT", "LATE", "LEAVE"}  # ❌ Uppercase
    
    if normalized not in valid_statuses:
        raise ValueError(...)
    
    return normalized  # ❌ Returns uppercase
```

**After** (CORRECT):
```python
@field_validator('status')
@classmethod
def validate_status(cls, v: str) -> str:
    """Normalize and validate status - MUST BE LOWERCASE for PostgreSQL enum"""
    normalized = v.strip().lower()  # ✅ Lowercase
    valid_statuses = {"present", "absent", "late", "leave"}  # ✅ Lowercase
    
    if normalized not in valid_statuses:
        raise ValueError(f"Status must be one of: {', '.join(sorted(valid_statuses))}")
    
    return normalized  # ✅ Returns lowercase
```

---

### 2. Updated Service Constants
**File**: `app/services/attendance_service.py`

**Before** (WRONG):
```python
VALID_ATTENDANCE_STATUSES = {"PRESENT", "ABSENT", "LEAVE", "LATE"}  # ❌ Uppercase
```

**After** (CORRECT):
```python
# CRITICAL: Database enum values are LOWERCASE
VALID_ATTENDANCE_STATUSES = {"present", "absent", "leave", "late"}  # ✅ Lowercase
```

---

### 3. Updated Filter Logic
**File**: `app/services/attendance_service.py`

**Before** (WRONG):
```python
if status:
    normalized_status = status.strip().upper()  # ❌ Uppercase
    if normalized_status in VALID_ATTENDANCE_STATUSES:
        query = query.filter(Attendance.status == normalized_status)
```

**After** (CORRECT):
```python
if status:
    normalized_status = status.strip().lower()  # ✅ Lowercase
    if normalized_status in VALID_ATTENDANCE_STATUSES:
        query = query.filter(Attendance.status == normalized_status)
```

---

### 4. Updated _normalize_status Method
**File**: `app/services/attendance_service.py`

**Before** (WRONG):
```python
def _normalize_status(self, status: str) -> str:
    normalized = status.strip().upper()  # ❌ Uppercase
    if normalized not in VALID_ATTENDANCE_STATUSES:
        raise ValidationError(...)
    return normalized
```

**After** (CORRECT):
```python
def _normalize_status(self, status: str) -> str:
    """Normalize status to lowercase to match PostgreSQL enum"""
    normalized = status.strip().lower()  # ✅ Lowercase
    if normalized not in VALID_ATTENDANCE_STATUSES:
        raise ValidationError(...)
    return normalized
```

---

## 🎯 HOW IT WORKS NOW

### Request Flow

```python
# 1. Frontend sends (any case)
{
  "status": "PRESENT"  // or "present" or "Present"
}

# 2. Validator normalizes to lowercase
@field_validator('status')
def validate_status(cls, v: str) -> str:
    return v.strip().lower()  # "present"

# 3. Database accepts lowercase
INSERT INTO attendance (status) VALUES ('present');  # ✅ Works!
```

---

## 📊 SUPPORTED INPUT FORMATS

### All These Work Now ✅

```json
// Uppercase (converted to lowercase)
{"status": "PRESENT"}  → "present" ✅

// Lowercase (kept as-is)
{"status": "present"}  → "present" ✅

// Mixed case (converted to lowercase)
{"status": "Present"}  → "present" ✅
{"status": "pReSeNt"}  → "present" ✅

// With whitespace (trimmed and converted)
{"status": " PRESENT "}  → "present" ✅
```

### Database Stores Lowercase

```sql
SELECT status FROM attendance;
-- Result:
-- present
-- absent
-- late
-- leave
```

---

## 🧪 TESTING

### Test 1: Create Attendance (Uppercase Input)
```bash
curl -X POST "http://localhost:8000/api/attendance" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "uuid",
    "date": "2026-05-05",
    "status": "PRESENT"
  }'
```

**Expected**: 201 Created ✅
```json
{
  "status": "present"  // ✅ Lowercase in response
}
```

---

### Test 2: Create Attendance (Lowercase Input)
```bash
curl -X POST "http://localhost:8000/api/attendance" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "uuid",
    "date": "2026-05-05",
    "status": "present"
  }'
```

**Expected**: 201 Created ✅

---

### Test 3: Invalid Status
```bash
curl -X POST "http://localhost:8000/api/attendance" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "uuid",
    "date": "2026-05-05",
    "status": "invalid"
  }'
```

**Expected**: 422 Unprocessable Entity ❌
```json
{
  "detail": [
    {
      "loc": ["body", "status"],
      "msg": "Status must be one of: absent, late, leave, present",
      "type": "value_error"
    }
  ]
}
```

---

### Test 4: Filter by Status
```bash
curl -X GET "http://localhost:8000/api/attendance?status=present" \
  -H "Authorization: Bearer <token>"
```

**Expected**: 200 OK ✅
Returns all attendance with status "present"

---

## 📋 VALID STATUS VALUES

### Database Enum Definition
```sql
CREATE TYPE attendance_status AS ENUM (
    'present',  -- ✅ Lowercase
    'absent',   -- ✅ Lowercase
    'late',     -- ✅ Lowercase
    'leave'     -- ✅ Lowercase
);
```

### Backend Constants
```python
VALID_ATTENDANCE_STATUSES = {
    "present",  # ✅ Lowercase
    "absent",   # ✅ Lowercase
    "late",     # ✅ Lowercase
    "leave"     # ✅ Lowercase
}
```

### Frontend Can Send Any Case
```javascript
// All these work:
{ status: "PRESENT" }  // ✅
{ status: "present" }  // ✅
{ status: "Present" }  // ✅
```

---

## 🎓 KEY LESSONS

### 1. Match Database Enum Case
```python
# Database enum is lowercase
CREATE TYPE status AS ENUM ('present', 'absent');

# Backend must normalize to lowercase
normalized = v.strip().lower()  # ✅
```

### 2. Case-Insensitive Input
```python
# Accept any case from frontend
"PRESENT" → "present"  # ✅
"Present" → "present"  # ✅
"present" → "present"  # ✅
```

### 3. Consistent Normalization
```python
# Normalize in ONE place (validator)
@field_validator('status')
def validate_status(cls, v: str) -> str:
    return v.strip().lower()  # ✅
```

---

## 🔍 DEBUGGING

### Check Database Enum
```sql
-- Check enum definition
SELECT enumlabel 
FROM pg_enum 
WHERE enumtypid = 'attendance_status'::regtype;

-- Result should be:
-- present
-- absent
-- late
-- leave
```

### Check Stored Values
```sql
-- Check what's actually stored
SELECT DISTINCT status FROM attendance;

-- Should all be lowercase:
-- present
-- absent
-- late
-- leave
```

---

## ⚠️ IMPORTANT NOTES

### 1. Database Enum is Case-Sensitive
```sql
-- ✅ Works
INSERT INTO attendance (status) VALUES ('present');

-- ❌ Fails
INSERT INTO attendance (status) VALUES ('PRESENT');
-- ERROR: invalid input value for enum
```

### 2. Always Normalize Before Saving
```python
# ✅ CORRECT
status = payload.status.lower()
attendance.status = status

# ❌ WRONG
attendance.status = payload.status  # Might be uppercase!
```

### 3. Frontend Unchanged
Frontend can continue sending any case:
```javascript
// All these work now:
{ status: "PRESENT" }
{ status: "present" }
{ status: "Present" }
```

---

## 📊 COMPARISON

### Before Fix
```
Frontend: {"status": "PRESENT"}
    ↓
Backend: Normalizes to "PRESENT"
    ↓
Database: Rejects "PRESENT"
    ↓
Result: 500 Error ❌
```

### After Fix
```
Frontend: {"status": "PRESENT"}
    ↓
Backend: Normalizes to "present"
    ↓
Database: Accepts "present"
    ↓
Result: 201 Created ✅
```

---

## ✅ EXPECTED RESULTS

### API Response
```json
{
  "id": "uuid",
  "user_id": "uuid",
  "day": "2026-05-05",
  "status": "present",  // ✅ Lowercase
  "user_name": "John Doe",
  "batch_name": "Python Batch 1"
}
```

### Database Record
```sql
SELECT * FROM attendance WHERE id = 'uuid';

-- status column shows:
-- present  (lowercase)
```

---

## 🚀 DEPLOYMENT

### No Breaking Changes
- ✅ Frontend unchanged (accepts any case)
- ✅ Backward compatible
- ✅ Existing data unaffected (if already lowercase)
- ✅ No database migration needed

### Deployment Steps
1. Deploy updated code
2. Restart application
3. Test with uppercase input
4. Verify lowercase in database

---

## 🎯 SUMMARY

**Problem**: PostgreSQL enum rejects uppercase values

**Root Cause**: Backend normalized to uppercase, database expects lowercase

**Solution**: 
1. Change normalization from `.upper()` to `.lower()`
2. Update constants to lowercase
3. Update all validation logic

**Impact**:
- ✅ No more 500 errors
- ✅ Database accepts values
- ✅ Frontend unchanged
- ✅ Case-insensitive input

**Status**: ✅ **FIXED**

---

## 🧪 QUICK TEST

```bash
# Should work now!
curl -X POST "http://localhost:8000/api/attendance" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "your-intern-uuid",
    "date": "2026-05-05",
    "status": "PRESENT"
  }'
```

**Expected**: 201 Created with `"status": "present"` ✅
