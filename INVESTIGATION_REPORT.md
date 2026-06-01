# Backend Filtering Issues - Investigation Report

**Date:** June 1, 2026  
**Investigator:** Kiro AI Assistant

---

## ISSUE 1: FULLSTACK Intern Filtering Not Working ✅ FIXED

### Root Cause
The profile service was using **raw `tech_stack` comparison** instead of **normalized `intern_role`** when filtering profiles.

**Problem Location:** `app/services/profile_service.py` line 240

```python
# BEFORE (BROKEN):
if tech_stack:
    query = query.filter(Profile.tech_stack.ilike(tech_stack))
```

### Why AIML Works But FULLSTACK Doesn't
- **AIML variations** are more consistent: "AI/ML", "AIML", "AI-ML"
- **FULLSTACK variations** are inconsistent: "Full Stack" (with space), "FULLSTACK" (no space), "MERN Stack", "Django Full Stack"
- The `normalize_role()` function correctly handles all variations, but wasn't being used in profile filtering

### The Fix Applied ✅

**File:** `app/services/profile_service.py`

```python
# AFTER (FIXED):
if tech_stack:
    # CRITICAL FIX: Filter by normalized intern_role instead of raw tech_stack
    # This ensures FULLSTACK matches "Full Stack", "MERN Stack", etc.
    from app.utils.role_utils import normalize_role
    normalized_tech_stack = normalize_role(tech_stack)
    logger.info(f"Filtering by tech_stack: '{tech_stack}' -> normalized: '{normalized_tech_stack}'")
    query = query.filter(Profile.intern_role == normalized_tech_stack)
```

### Additional Improvements ✅

1. **Enhanced Logging** - Added comprehensive logging to track:
   - Original tech_stack value
   - Normalized role value
   - Batch ID
   - Number of interns returned
   - Each profile's details (name, role, intern_role, tech_stack, batch)

2. **Normalized intern_role filtering** - Also fixed the `intern_role` parameter to use normalization:
   ```python
   if intern_role:
       from app.utils.role_utils import normalize_role
       normalized_intern_role = normalize_role(intern_role)
       logger.info(f"Filtering by intern_role: '{intern_role}' -> normalized: '{normalized_intern_role}'")
       query = query.filter(Profile.intern_role == normalized_intern_role)
   ```

### Files Changed
- ✅ `app/services/profile_service.py` - Fixed filtering logic and added logging

### Endpoints Affected
- ✅ `GET /profiles` - List profiles with role/tech_stack filtering
- ✅ All profile queries that use `tech_stack` or `intern_role` parameters

### Testing Recommendations

1. **Test FULLSTACK filtering:**
   ```bash
   GET /profiles?batch_id=<KF-Cohort-6-UUID>&tech_stack=FULLSTACK
   ```
   Should return all interns with:
   - `intern_role = "FULLSTACK"`
   - Regardless of their `tech_stack` value ("Full Stack", "MERN Stack", etc.)

2. **Test AIML filtering:**
   ```bash
   GET /profiles?batch_id=<KF-Cohort-6-UUID>&tech_stack=AIML
   ```
   Should return all interns with:
   - `intern_role = "AIML"`
   - Regardless of their `tech_stack` value ("AI/ML", "AIML", etc.)

3. **Check logs:**
   Look for these log entries:
   ```
   === list_profiles called ===
   Filters: role=INTERN, intern_role=None, batch_id=<uuid>, tech_stack=FULLSTACK
   Filtering by tech_stack: 'FULLSTACK' -> normalized: 'FULLSTACK'
   === Query returned X profiles ===
     - John Doe | Role: INTERN | Intern Role: FULLSTACK | Tech Stack: Full Stack | Batch: <uuid>
     - Jane Smith | Role: INTERN | Intern Role: FULLSTACK | Tech Stack: MERN Stack | Batch: <uuid>
   ```

---

## ISSUE 2: Notification Module Batch Loading - "All Batches" ⚠️ FRONTEND ISSUE

### Investigation Result
After comprehensive investigation, the string **"All Batches" does NOT exist in the backend code**.

### Evidence

1. **Notification Service** (`app/services/notification_service.py`):
   - Does NOT include batch information in notification responses
   - Response fields: `id`, `user_id`, `sender_id`, `sender_name`, `is_sender`, `title`, `message`, `type`, `is_read`, `is_broadcast`, `created_at`, `edited_at`
   - **No batch-related fields**

2. **Notification Schema** (`app/schemas/notification.py`):
   - `NotificationCreate` - No batch field
   - `NotificationBroadcast` - No batch field
   - `NotificationResponse` - No batch field

3. **Batch Service** (`app/services/batch_service.py`):
   - Returns proper batch objects with actual names
   - Default value for `tech_leads_display` is `"Unassigned"`, NOT `"All Batches"`

4. **Batch Router** (`app/routers/batches.py`):
   - `GET /batches` - Returns list of batch objects with actual names
   - `GET /batches/available-for-evaluations` - Returns filtered batches for dropdowns
   - Correctly filters by role:
     - **ADMIN**: All batches
     - **TECHNICAL_LEAD**: Only assigned batches

### Backend Batch Endpoints Working Correctly ✅

```python
# GET /batches
# Returns:
[
  {
    "id": "uuid",
    "name": "KF-Cohort-5",  # ← Actual batch name
    "tech_stack": "AIML",
    "start_date": "2024-01-01",
    "tech_leads_display": "John Doe/Jane Smith",
    ...
  },
  {
    "id": "uuid",
    "name": "KF-Cohort-6",  # ← Actual batch name
    "tech_stack": "Full Stack",
    "start_date": "2024-02-01",
    "tech_leads_display": "Bob Wilson",
    ...
  }
]
```

### Conclusion: Frontend Issue

The "All Batches" string is coming from the **frontend**:

1. **Possible Causes:**
   - Frontend default/placeholder value when batches haven't loaded
   - Hardcoded dropdown option in frontend code
   - Frontend state initialization issue
   - Frontend not calling the correct batch listing endpoint
   - Frontend not handling the batch response correctly

2. **Frontend Should:**
   - Call `GET /batches` or `GET /batches/available-for-evaluations`
   - Parse the response array and extract `name` field from each batch
   - Display actual batch names: "KF-Cohort-5", "KF-Cohort-6", etc.

### Backend Verification Steps

1. **Test batch listing endpoint:**
   ```bash
   # As ADMIN
   GET /batches
   # Should return all batches with actual names
   
   # As TECHNICAL_LEAD
   GET /batches
   # Should return only assigned batches with actual names
   ```

2. **Check response structure:**
   ```json
   [
     {
       "id": "uuid",
       "name": "KF-Cohort-5",  // ← This should be displayed
       "tech_stack": "AIML",
       "tech_leads_display": "John Doe",
       ...
     }
   ]
   ```

3. **Verify RBAC:**
   - ADMIN sees all batches
   - TECHNICAL_LEAD sees only their assigned batches
   - Response includes actual batch names, never "All Batches"

### Recommendation

**Check the frontend code** where notification batch names are displayed:
- Look for hardcoded "All Batches" string
- Verify the API endpoint being called
- Check how the batch response is parsed
- Ensure the `name` field is being extracted correctly

---

## Summary

### Issue 1: FULLSTACK Filtering ✅ FIXED
- **Root Cause:** Raw tech_stack comparison instead of normalized intern_role
- **Fix Applied:** Use `normalize_role()` and filter by `intern_role` field
- **Files Changed:** `app/services/profile_service.py`
- **Status:** FIXED with comprehensive logging

### Issue 2: "All Batches" ⚠️ FRONTEND ISSUE
- **Root Cause:** Frontend issue, not backend
- **Backend Status:** Working correctly, returns actual batch names
- **Action Required:** Investigate frontend code
- **Backend Endpoints:** All working correctly

---

## Files Modified

1. **app/services/profile_service.py**
   - Fixed `tech_stack` filtering to use normalized `intern_role`
   - Fixed `intern_role` filtering to use normalization
   - Added comprehensive logging for debugging
   - Added result logging to track returned profiles

---

## Next Steps

1. ✅ **Deploy the backend changes** for Issue 1
2. ⚠️ **Investigate frontend** for Issue 2:
   - Search for "All Batches" string in frontend code
   - Check notification module batch dropdown implementation
   - Verify API calls to `/batches` endpoint
   - Ensure proper parsing of batch response

3. **Monitor logs** after deployment:
   - Check for "Filtering by tech_stack" log entries
   - Verify normalized values are correct
   - Confirm correct number of profiles returned

4. **Test both roles:**
   - FULLSTACK filtering should now work
   - AIML filtering should continue to work
   - Both should return correct interns from specified batch
