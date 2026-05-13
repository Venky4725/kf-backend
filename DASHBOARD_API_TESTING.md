# Dashboard API Testing Guide

## Problem
Frontend crashes before making dashboard API calls. Need to verify backend dashboard endpoints exist and work correctly.

## Backend URL
```
https://kf-backend-production-48e5.up.railway.app/docs
```

---

## Dashboard Endpoints Added

### 1. GET `/attendance/dashboard/summary`
**Purpose:** Overall dashboard statistics

**Query Parameters:**
- `batch_id` (optional): Filter by batch
- `start_date` (optional): Start date (YYYY-MM-DD)
- `end_date` (optional): End date (YYYY-MM-DD)

**Response:**
```json
{
  "total_records": 167,
  "present": 150,
  "absent": 10,
  "late": 5,
  "leave": 2,
  "attendance_rate": 92.81,
  "distribution": {
    "present_count": 150,
    "absent_count": 10,
    "late_count": 5,
    "leave_count": 2,
    "total_count": 167,
    "present_percentage": 89.82,
    "absent_percentage": 5.99,
    "late_percentage": 2.99,
    "leave_percentage": 1.20
  }
}
```

---

### 2. GET `/attendance/dashboard/distribution`
**Purpose:** Pie chart data

**Query Parameters:**
- `batch_id` (optional): Filter by batch
- `start_date` (optional): Start date
- `end_date` (optional): End date

**Response:**
```json
{
  "present_count": 150,
  "absent_count": 10,
  "late_count": 5,
  "leave_count": 2,
  "total_count": 167,
  "present_percentage": 89.82,
  "absent_percentage": 5.99,
  "late_percentage": 2.99,
  "leave_percentage": 1.20
}
```

---

### 3. GET `/attendance/dashboard/trends`
**Purpose:** Time series data for charts

**Query Parameters:**
- `batch_id` (optional): Filter by batch
- `start_date` (optional): Start date
- `end_date` (optional): End date
- `days` (optional): Number of days (default 30)

**Response:**
```json
{
  "start_date": "2026-04-13",
  "end_date": "2026-05-13",
  "trends": [
    {
      "date": "2026-04-13",
      "present": 20,
      "absent": 2,
      "late": 1,
      "leave": 0,
      "total": 23
    },
    {
      "date": "2026-04-14",
      "present": 22,
      "absent": 1,
      "late": 0,
      "leave": 0,
      "total": 23
    }
  ]
}
```

---

### 4. GET `/attendance/dashboard/batch-wise`
**Purpose:** Batch comparison data

**Query Parameters:**
- `start_date` (optional): Start date
- `end_date` (optional): End date

**Response:**
```json
{
  "batches": [
    {
      "batch_id": "uuid",
      "batch_name": "Batch A",
      "present": 50,
      "absent": 3,
      "late": 2,
      "leave": 1,
      "total": 56,
      "attendance_rate": 92.86
    },
    {
      "batch_id": "uuid",
      "batch_name": "Batch B",
      "present": 100,
      "absent": 7,
      "late": 3,
      "leave": 1,
      "total": 111,
      "attendance_rate": 92.79
    }
  ]
}
```

---

### 5. GET `/attendance/dashboard/intern/{intern_id}`
**Purpose:** Individual intern analytics

**Path Parameters:**
- `intern_id` (required): UUID of intern

**Query Parameters:**
- `start_date` (optional): Start date
- `end_date` (optional): End date

**Response:**
```json
{
  "intern_id": "uuid",
  "intern_name": "John Doe",
  "batch_id": "uuid",
  "batch_name": "Batch A",
  "present_count": 20,
  "absent_count": 2,
  "late_count": 3,
  "leave_count": 1,
  "total_days": 26,
  "attendance_percentage": 88.46,
  "trend": [
    {
      "date": "2026-04-13",
      "present": 1,
      "absent": 0,
      "late": 0,
      "leave": 0,
      "total": 1
    }
  ]
}
```

---

## RBAC (Role-Based Access Control)

### ADMIN
- ✅ Can access all dashboard endpoints
- ✅ Can see all batches and interns
- ✅ No filtering applied

### TECHNICAL_LEAD
- ✅ Can access all dashboard endpoints
- ⚠️  Only sees data for batches they lead
- ⚠️  Filtered by `first_tech_lead_id` or `second_tech_lead_id`

### INTERN
- ❌ Cannot access batch-wise or summary endpoints
- ✅ Can only access their own intern analytics
- ⚠️  Returns 403 if trying to access other interns

---

## Testing with Swagger UI

### Step 1: Open Swagger
```
https://kf-backend-production-48e5.up.railway.app/docs
```

### Step 2: Authenticate
1. Click **"Authorize"** button (top right)
2. Login to get token:
   - Go to `/auth/login` endpoint
   - Click "Try it out"
   - Enter credentials:
     ```json
     {
       "email": "admin@example.com",
       "password": "your-password"
     }
     ```
   - Click "Execute"
   - Copy the `access_token` from response
3. Paste token in Authorization dialog
4. Click "Authorize"

### Step 3: Test Dashboard Endpoints

#### Test Summary
1. Find `/attendance/dashboard/summary`
2. Click "Try it out"
3. Optional: Set date range
4. Click "Execute"
5. Verify response:
   - Status: 200
   - Has `total_records`
   - Has `attendance_rate`
   - Has `distribution` object

#### Test Distribution
1. Find `/attendance/dashboard/distribution`
2. Click "Try it out"
3. Click "Execute"
4. Verify response:
   - Status: 200
   - Has all count fields
   - Has all percentage fields
   - Percentages add up to ~100%

#### Test Trends
1. Find `/attendance/dashboard/trends`
2. Click "Try it out"
3. Set `days` to 30
4. Click "Execute"
5. Verify response:
   - Status: 200
   - Has `trends` array
   - Each trend has date and counts

#### Test Batch-wise
1. Find `/attendance/dashboard/batch-wise`
2. Click "Try it out"
3. Click "Execute"
4. Verify response:
   - Status: 200
   - Has `batches` array
   - Each batch has attendance_rate

---

## Testing with Python Script

### Setup
```bash
# Install requests
pip install requests

# Edit credentials in script
nano scripts/test_dashboard_endpoints.py
# Update ADMIN_EMAIL and ADMIN_PASSWORD
```

### Run Tests
```bash
python scripts/test_dashboard_endpoints.py
```

### Expected Output
```
============================================================
ATTENDANCE DASHBOARD ENDPOINT TESTS
============================================================
Base URL: https://kf-backend-production-48e5.up.railway.app

============================================================
LOGGING IN
============================================================
Email: admin@example.com

✅ Login successful
User: Admin Name (ADMIN)
Token: eyJhbGciOiJIUzI1NiIs...

------------------------------------------------------------
TEST: Dashboard Summary
------------------------------------------------------------
Method: GET
Path: /attendance/dashboard/summary

Status: 200
Response time: 0.45s

✅ SUCCESS

Response structure:
  total_records: int = 167
  present: int = 150
  absent: int = 10
  late: int = 5
  leave: int = 2
  attendance_rate: float = 92.81
  distribution:
    present_count: int = 150
    ...

============================================================
TEST SUMMARY
============================================================

Passed: 7/7

✅ ALL TESTS PASSED

Dashboard endpoints are working correctly!
```

---

## Testing with cURL

### Get Token
```bash
TOKEN=$(curl -X POST "https://kf-backend-production-48e5.up.railway.app/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"your-password"}' \
  | jq -r '.access_token')

echo $TOKEN
```

### Test Summary
```bash
curl -X GET "https://kf-backend-production-48e5.up.railway.app/attendance/dashboard/summary" \
  -H "Authorization: Bearer $TOKEN" \
  | jq
```

### Test Distribution
```bash
curl -X GET "https://kf-backend-production-48e5.up.railway.app/attendance/dashboard/distribution" \
  -H "Authorization: Bearer $TOKEN" \
  | jq
```

### Test Trends
```bash
curl -X GET "https://kf-backend-production-48e5.up.railway.app/attendance/dashboard/trends?days=30" \
  -H "Authorization: Bearer $TOKEN" \
  | jq
```

### Test Batch-wise
```bash
curl -X GET "https://kf-backend-production-48e5.up.railway.app/attendance/dashboard/batch-wise" \
  -H "Authorization: Bearer $TOKEN" \
  | jq
```

---

## Common Issues

### Issue: 404 Not Found
**Cause:** Endpoint doesn't exist or wrong path
**Solution:** 
- Verify endpoint path in Swagger UI
- Check if router is registered in main.py
- Restart application after code changes

### Issue: 401 Unauthorized
**Cause:** Missing or invalid token
**Solution:**
- Login again to get fresh token
- Check token format: `Bearer <token>`
- Verify token hasn't expired

### Issue: 403 Forbidden
**Cause:** RBAC restriction
**Solution:**
- Check user role (ADMIN, TECHNICAL_LEAD, INTERN)
- Verify user has access to requested data
- Tech leads can only see their batches

### Issue: 422 Validation Error
**Cause:** Invalid query parameters
**Solution:**
- Check date format: YYYY-MM-DD
- Verify UUID format for batch_id/intern_id
- Check required parameters

### Issue: 500 Internal Server Error
**Cause:** Backend error
**Solution:**
- Check Railway logs
- Look for Python exceptions
- Verify database connection
- Check for missing data

---

## Monitoring Railway Logs

### View Logs
1. Go to Railway dashboard
2. Select your project
3. Click on backend service
4. Click "Logs" tab

### What to Look For
```
INFO - GET /attendance/dashboard/summary
INFO - User abc123... (ADMIN) accessing dashboard
INFO - Distribution query returned 167 records
```

### Error Patterns
```
ERROR - DataError: invalid input value for enum
ERROR - Profile not found
ERROR - Batch relationship not loaded
```

---

## Verification Checklist

- [ ] All 5 dashboard endpoints exist in Swagger
- [ ] Authentication works (can get token)
- [ ] Summary endpoint returns correct structure
- [ ] Distribution endpoint returns percentages
- [ ] Trends endpoint returns time series data
- [ ] Batch-wise endpoint returns all batches
- [ ] Intern endpoint returns individual analytics
- [ ] ADMIN can access all endpoints
- [ ] TECHNICAL_LEAD sees only their batches
- [ ] Response times are acceptable (< 2s)
- [ ] No 500 errors in Railway logs
- [ ] LATE status is included in all responses

---

## Next Steps

### If All Tests Pass
1. ✅ Backend dashboard APIs are working
2. ✅ Focus on frontend debugging
3. ✅ Check frontend API calls match backend paths
4. ✅ Verify frontend error handling

### If Tests Fail
1. ❌ Check which endpoints are missing
2. ❌ Review error messages
3. ❌ Check Railway logs for exceptions
4. ❌ Verify database has data
5. ❌ Run migration scripts if needed

---

## Report Template

```
DASHBOARD API TEST REPORT
Date: 2026-05-13
Tester: [Your Name]
Environment: Production (Railway)

ENDPOINT STATUS:
✅ /attendance/dashboard/summary - Working
✅ /attendance/dashboard/distribution - Working
✅ /attendance/dashboard/trends - Working
✅ /attendance/dashboard/batch-wise - Working
✅ /attendance/dashboard/intern/{id} - Working

RESPONSE VALIDATION:
✅ All responses have correct structure
✅ All responses include LATE status
✅ Percentages add up to 100%
✅ Dates are in ISO format
✅ UUIDs are valid

RBAC VALIDATION:
✅ ADMIN can access all endpoints
✅ TECHNICAL_LEAD filtered correctly
✅ INTERN restricted appropriately

PERFORMANCE:
✅ Average response time: 0.5s
✅ No timeouts
✅ No 500 errors

CONCLUSION:
✅ Backend dashboard APIs are fully functional
✅ Ready for frontend integration
```

---

**Status:** ✅ Dashboard endpoints implemented and ready for testing
