# Verification and Testing Guide - Attendance Batch Names

## Date: May 5, 2026

---

## ✅ IMPLEMENTATION VERIFIED

All fixes have been correctly implemented:

### 1. Column Name ✅
- ✅ All `Batch.tech_lead_id` replaced with `Batch.team_lead_id`
- ✅ No remaining incorrect references

### 2. Relationships ✅
- ✅ `Attendance.profile` relationship defined with `lazy="joined"`
- ✅ `Profile.batch` relationship defined with `lazy="joined"`

### 3. joinedload() ✅
- ✅ Used in `list_attendance` query
- ✅ Used in `create_attendance` (new record)
- ✅ Used in `create_attendance` (update existing)

### 4. Enhanced Logging ✅
- ✅ Debug logs added to track relationship loading
- ✅ Error logs for when relationships fail to load

---

## 🧪 TESTING INSTRUCTIONS

### Prerequisites
1. Ensure database has test data:
   - At least 1 batch with a team lead
   - At least 2 interns assigned to that batch
   - At least 3 attendance records for those interns

### Test 1: List Attendance (Admin)
```bash
# Login as Admin
POST /api/auth/login
{
  "email": "admin@example.com",
  "password": "password"
}

# Get attendance list
GET /api/attendance
Authorization: Bearer <admin_token>

# Expected Result:
# - Status: 200 OK
# - All attendance records returned
# - Each record has "batch_name" field populated
# - No "Unassigned" or null batch_name (for interns with batches)
```

**Expected Response**:
```json
[
  {
    "id": "uuid",
    "user_id": "uuid",
    "day": "2026-05-05",
    "status": "PRESENT",
    "created_at": "2026-05-05T10:00:00Z",
    "user_name": "John Doe",
    "batch_name": "Python Batch 1"  // ✅ Should be visible
  }
]
```

---

### Test 2: List Attendance (Tech Lead)
```bash
# Login as Tech Lead
POST /api/auth/login
{
  "email": "techlead@example.com",
  "password": "password"
}

# Get attendance list
GET /api/attendance
Authorization: Bearer <techlead_token>

# Expected Result:
# - Status: 200 OK
# - Only attendance for interns in Tech Lead's batch
# - Each record has "batch_name" field populated
# - batch_name matches Tech Lead's batch
```

**Expected Response**:
```json
[
  {
    "id": "uuid",
    "user_id": "uuid",
    "day": "2026-05-05",
    "status": "PRESENT",
    "user_name": "John Doe",
    "batch_name": "Python Batch 1"  // ✅ Tech Lead's batch
  }
]
```

---

### Test 3: Create Attendance
```bash
# Login as Tech Lead
POST /api/auth/login
{
  "email": "techlead@example.com",
  "password": "password"
}

# Create attendance
POST /api/attendance
Authorization: Bearer <techlead_token>
Content-Type: application/json

{
  "user_id": "intern_uuid",
  "day": "2026-05-05",
  "status": "PRESENT"
}

# Expected Result:
# - Status: 201 Created
# - Response includes batch_name
# - batch_name is NOT null or "Unassigned"
```

**Expected Response**:
```json
{
  "id": "new_uuid",
  "user_id": "intern_uuid",
  "day": "2026-05-05",
  "status": "PRESENT",
  "created_at": "2026-05-05T10:00:00Z",
  "user_name": "John Doe",
  "batch_name": "Python Batch 1"  // ✅ Should be visible
}
```

---

### Test 4: Update Existing Attendance (Duplicate Day)
```bash
# Create attendance for same user and day again
POST /api/attendance
Authorization: Bearer <techlead_token>
Content-Type: application/json

{
  "user_id": "intern_uuid",
  "day": "2026-05-05",  // Same day as before
  "status": "LATE"       // Different status
}

# Expected Result:
# - Status: 201 Created (updates existing)
# - Response includes batch_name
# - Status updated to "LATE"
```

**Expected Response**:
```json
{
  "id": "same_uuid_as_before",
  "user_id": "intern_uuid",
  "day": "2026-05-05",
  "status": "LATE",  // ✅ Updated
  "user_name": "John Doe",
  "batch_name": "Python Batch 1"  // ✅ Still visible
}
```

---

## 📊 LOG VERIFICATION

### Check Application Logs

When you run the tests, check the logs for these messages:

#### Successful Relationship Loading:
```
INFO: list_attendance called by <user_id> (TECHNICAL_LEAD)
INFO: Processing attendance <attendance_id>
INFO:   - attendance.profile exists: True
INFO:   - user_name: John Doe
INFO:   - batch_id: <batch_uuid>
INFO:   - attendance.profile.batch exists: True
INFO:   - ✅ batch_name: Python Batch 1
```

#### Failed Relationship Loading (Should NOT see this):
```
ERROR:   - ❌ Batch relationship NOT loaded! user_id=<user_id>, batch_id=<batch_id>
ERROR:   - This should not happen with joinedload!
```

If you see ERROR logs, it means joinedload is not working correctly.

---

## 🔍 SQL QUERY VERIFICATION

### Enable SQL Logging

Add to your application startup or test file:
```python
import logging
logging.basicConfig()
logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)
```

### Expected SQL Query

When you call `GET /api/attendance`, you should see a single SQL query like:

```sql
SELECT 
    attendance.id,
    attendance.user_id,
    attendance.day,
    attendance.status,
    attendance.created_at,
    profile_1.id AS profile_1_id,
    profile_1.name AS profile_1_name,
    profile_1.email AS profile_1_email,
    profile_1.batch_id AS profile_1_batch_id,
    batch_1.id AS batch_1_id,
    batch_1.name AS batch_1_name,
    batch_1.tech_stack AS batch_1_tech_stack
FROM attendance
INNER JOIN profiles AS profile_1 ON attendance.user_id = profile_1.id
INNER JOIN batches AS batch_1 ON profile_1.batch_id = batch_1.id
WHERE batches.team_lead_id = ?
ORDER BY attendance.day DESC, attendance.created_at DESC
LIMIT ? OFFSET ?
```

**Key Points**:
- ✅ Single query (no N+1 problem)
- ✅ INNER JOINs to profiles and batches
- ✅ Selects batch.name (batch_1_name)
- ✅ Correct WHERE clause with team_lead_id

---

## 🐛 TROUBLESHOOTING

### Issue 1: batch_name is null
**Symptoms**: Response has `"batch_name": null`

**Possible Causes**:
1. Intern has no batch assigned (`batch_id` is NULL)
2. Batch relationship not loaded
3. joinedload not working

**Debug Steps**:
```python
# Check logs for:
ERROR:   - ❌ Batch relationship NOT loaded!

# If you see this, check:
1. Is joinedload imported? (from sqlalchemy.orm import joinedload)
2. Is joinedload in the query? (.options(joinedload(...)))
3. Are relationships defined in models?
```

**Solution**:
- Verify intern has batch_id in database
- Check logs to see if relationship is loaded
- Verify joinedload is in query

---

### Issue 2: "Unassigned" appears in UI
**Symptoms**: UI shows "Unassigned" instead of batch name

**Possible Causes**:
1. Frontend is displaying "Unassigned" when batch_name is null
2. Backend returning null for batch_name

**Debug Steps**:
```bash
# Check API response directly
curl -X GET "http://localhost:8000/api/attendance" \
  -H "Authorization: Bearer <token>" | jq

# Look for batch_name field
```

**Solution**:
- If API returns null: Backend issue (check logs)
- If API returns batch name: Frontend issue (check UI code)

---

### Issue 3: AttributeError in logs
**Symptoms**: `AttributeError: 'Batch' has no attribute 'tech_lead_id'`

**Cause**: Still using wrong column name

**Solution**:
```bash
# Search for remaining incorrect references
grep -r "tech_lead_id" app/services/

# Should return no matches
# If it does, replace with team_lead_id
```

---

### Issue 4: No attendance records returned
**Symptoms**: Empty array `[]` returned

**Possible Causes**:
1. Tech Lead has no batches assigned
2. No attendance records exist
3. INNER JOIN excluding records

**Debug Steps**:
```python
# Check logs for:
WARNING: Tech Lead <user_id> is not assigned to any batches

# Check database:
SELECT * FROM batches WHERE team_lead_id = '<user_id>';
SELECT * FROM attendance WHERE user_id IN (
    SELECT id FROM profiles WHERE batch_id IN (
        SELECT id FROM batches WHERE team_lead_id = '<user_id>'
    )
);
```

**Solution**:
- Assign Tech Lead to a batch
- Create attendance records for interns in that batch

---

## ✅ SUCCESS CRITERIA

### All tests pass if:
- ✅ `GET /api/attendance` returns 200
- ✅ All records have `batch_name` populated (not null)
- ✅ No "Unassigned" in responses
- ✅ Tech Lead sees only their batch attendance
- ✅ Logs show "✅ batch_name: <name>"
- ✅ No ERROR logs about relationships not loading
- ✅ Single SQL query with JOINs (no N+1)
- ✅ Response time < 500ms

---

## 📋 QUICK CHECKLIST

Before testing:
- [ ] Database has test data (batches, interns, attendance)
- [ ] Tech Lead is assigned to a batch (team_lead_id set)
- [ ] Interns have batch_id set
- [ ] Application is running

During testing:
- [ ] Test as Admin (see all attendance)
- [ ] Test as Tech Lead (see only their batch)
- [ ] Test create attendance
- [ ] Test update attendance (duplicate day)
- [ ] Check logs for relationship loading
- [ ] Check SQL queries (single query with JOINs)

After testing:
- [ ] All batch_name fields populated
- [ ] No "Unassigned" labels
- [ ] No ERROR logs
- [ ] Performance is good (< 500ms)

---

## 🎯 EXPECTED OUTCOMES

### Positive Outcomes ✅
- Batch names visible in all responses
- No "Unassigned" labels
- Single query per request
- Fast response times
- Clean logs with success messages

### Negative Outcomes ❌ (Should NOT happen)
- batch_name is null
- "Unassigned" appears
- ERROR logs about relationships
- Multiple queries (N+1 problem)
- Slow response times

---

## 📞 SUPPORT

If issues persist after following this guide:

1. **Check Implementation**:
   - Verify all code changes are deployed
   - Restart application to load new code
   - Clear any caches

2. **Check Database**:
   - Verify foreign keys are set correctly
   - Check that batches exist
   - Verify team_lead_id is set

3. **Check Logs**:
   - Look for ERROR messages
   - Check SQL queries
   - Verify relationships are loading

4. **Review Documentation**:
   - `JOINEDLOAD_FIX.md` - Detailed explanation
   - `FINAL_COMPLETE_SUMMARY.md` - Complete overview

---

**Status**: ✅ **READY FOR TESTING**

Test the endpoints and verify batch names appear correctly!
