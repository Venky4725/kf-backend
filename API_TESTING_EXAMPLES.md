# API Testing Examples - Evaluation RBAC

## Authentication
All requests require JWT token in Authorization header:
```
Authorization: Bearer <your_jwt_token>
```

## Update Evaluation Endpoint

### Endpoint
```
PUT /api/evaluations/{evaluation_id}
```

### ADMIN - Update All Fields (Success)
```json
PUT /api/evaluations/123e4567-e89b-12d3-a456-426614174000
Content-Type: application/json
Authorization: Bearer <admin_token>

{
  "week_number": 5,
  "score": 4.5,
  "feedback": "Excellent progress this week",
  "intern_id": "987e6543-e21b-12d3-a456-426614174000",
  "reviewed_by": "456e7890-e12b-12d3-a456-426614174000"
}
```

**Expected Response:** `200 OK`
```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "intern_id": "987e6543-e21b-12d3-a456-426614174000",
  "reviewed_by": "456e7890-e12b-12d3-a456-426614174000",
  "week_number": 5,
  "score": 4.5,
  "feedback": "Excellent progress this week",
  "created_at": "2026-05-01T10:00:00Z",
  "updated_at": "2026-05-12T14:30:00Z"
}
```

### TECHNICAL_LEAD - Update Allowed Fields (Success)
```json
PUT /api/evaluations/123e4567-e89b-12d3-a456-426614174000
Content-Type: application/json
Authorization: Bearer <techlead_token>

{
  "week_number": 6,
  "score": 4.8,
  "feedback": "Great improvement in code quality"
}
```

**Expected Response:** `200 OK`
```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "intern_id": "987e6543-e21b-12d3-a456-426614174000",
  "reviewed_by": "456e7890-e12b-12d3-a456-426614174000",
  "week_number": 6,
  "score": 4.8,
  "feedback": "Great improvement in code quality",
  "created_at": "2026-05-01T10:00:00Z",
  "updated_at": "2026-05-12T14:35:00Z"
}
```

### TECHNICAL_LEAD - Attempt to Update Restricted Fields (Failure)
```json
PUT /api/evaluations/123e4567-e89b-12d3-a456-426614174000
Content-Type: application/json
Authorization: Bearer <techlead_token>

{
  "week_number": 6,
  "score": 4.8,
  "intern_id": "999e9999-e99b-99d9-a999-999999999999"
}
```

**Expected Response:** `403 Forbidden`
```json
{
  "detail": "Tech Leads cannot change the intern or reviewer of an evaluation"
}
```

### TECHNICAL_LEAD - Attempt to Update Evaluation Outside Assigned Batch (Failure)
```json
PUT /api/evaluations/999e9999-e99b-99d9-a999-999999999999
Content-Type: application/json
Authorization: Bearer <techlead_token>

{
  "week_number": 6,
  "score": 4.8,
  "feedback": "Good work"
}
```

**Expected Response:** `403 Forbidden`
```json
{
  "detail": "Tech Lead can only update evaluations in their assigned batches"
}
```

### Validation Error - Invalid Week Number
```json
PUT /api/evaluations/123e4567-e89b-12d3-a456-426614174000
Content-Type: application/json
Authorization: Bearer <admin_token>

{
  "week_number": 0,
  "score": 4.5
}
```

**Expected Response:** `422 Unprocessable Entity`
```json
{
  "detail": [
    {
      "type": "value_error",
      "loc": ["body", "week_number"],
      "msg": "Week number must be greater than or equal to 1",
      "input": 0
    }
  ]
}
```

### Validation Error - Invalid Score Range
```json
PUT /api/evaluations/123e4567-e89b-12d3-a456-426614174000
Content-Type: application/json
Authorization: Bearer <admin_token>

{
  "score": 6.0
}
```

**Expected Response:** `422 Unprocessable Entity`
```json
{
  "detail": [
    {
      "type": "value_error",
      "loc": ["body", "score"],
      "msg": "Score must be between 0 and 5",
      "input": 6.0
    }
  ]
}
```

## Delete Evaluation Endpoint

### Endpoint
```
DELETE /api/evaluations/{evaluation_id}
```

### ADMIN - Delete Any Evaluation (Success)
```
DELETE /api/evaluations/123e4567-e89b-12d3-a456-426614174000
Authorization: Bearer <admin_token>
```

**Expected Response:** `204 No Content`
(Empty response body)

### TECHNICAL_LEAD - Delete Evaluation in Assigned Batch (Success)
```
DELETE /api/evaluations/123e4567-e89b-12d3-a456-426614174000
Authorization: Bearer <techlead_token>
```

**Expected Response:** `204 No Content`
(Empty response body)

### TECHNICAL_LEAD - Attempt to Delete Evaluation Outside Assigned Batch (Failure)
```
DELETE /api/evaluations/999e9999-e99b-99d9-a999-999999999999
Authorization: Bearer <techlead_token>
```

**Expected Response:** `403 Forbidden`
```json
{
  "detail": "Tech Lead can only delete evaluations in their assigned batches"
}
```

### INTERN - Attempt to Delete Evaluation (Failure)
```
DELETE /api/evaluations/123e4567-e89b-12d3-a456-426614174000
Authorization: Bearer <intern_token>
```

**Expected Response:** `403 Forbidden`
```json
{
  "detail": "You do not have permission to delete evaluations"
}
```

### No Authentication (Failure)
```
DELETE /api/evaluations/123e4567-e89b-12d3-a456-426614174000
```

**Expected Response:** `401 Unauthorized`
```json
{
  "detail": "Authentication credentials were not provided."
}
```

### Evaluation Not Found
```
DELETE /api/evaluations/000e0000-e00b-00d0-a000-000000000000
Authorization: Bearer <admin_token>
```

**Expected Response:** `404 Not Found`
```json
{
  "detail": "Evaluation not found"
}
```

## Testing with cURL

### Update Evaluation (ADMIN)
```bash
curl -X PUT "http://localhost:8000/api/evaluations/123e4567-e89b-12d3-a456-426614174000" \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "week_number": 5,
    "score": 4.5,
    "feedback": "Excellent progress"
  }'
```

### Update Evaluation (TECHNICAL_LEAD)
```bash
curl -X PUT "http://localhost:8000/api/evaluations/123e4567-e89b-12d3-a456-426614174000" \
  -H "Authorization: Bearer YOUR_TECHLEAD_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "week_number": 6,
    "score": 4.8,
    "feedback": "Great improvement"
  }'
```

### Delete Evaluation (ADMIN)
```bash
curl -X DELETE "http://localhost:8000/api/evaluations/123e4567-e89b-12d3-a456-426614174000" \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN"
```

### Delete Evaluation (TECHNICAL_LEAD)
```bash
curl -X DELETE "http://localhost:8000/api/evaluations/123e4567-e89b-12d3-a456-426614174000" \
  -H "Authorization: Bearer YOUR_TECHLEAD_TOKEN"
```

## Testing with Postman

### Setup
1. Create a new request collection
2. Add environment variables:
   - `base_url`: `http://localhost:8000`
   - `admin_token`: Your admin JWT token
   - `techlead_token`: Your technical lead JWT token
   - `intern_token`: Your intern JWT token

### Test Scenarios

#### Scenario 1: ADMIN Full Access
1. **Update with all fields** → Should succeed
2. **Update intern_id** → Should succeed
3. **Update reviewed_by** → Should succeed
4. **Delete any evaluation** → Should succeed

#### Scenario 2: TECHNICAL_LEAD Restricted Access
1. **Update week_number, score, feedback** → Should succeed (if in assigned batch)
2. **Attempt to update intern_id** → Should fail with 403
3. **Attempt to update reviewed_by** → Should fail with 403
4. **Attempt to update evaluation in different batch** → Should fail with 403
5. **Delete evaluation in assigned batch** → Should succeed
6. **Attempt to delete evaluation in different batch** → Should fail with 403

#### Scenario 3: Validation Tests
1. **week_number = 0** → Should fail with 422
2. **week_number = -1** → Should fail with 422
3. **score = -0.5** → Should fail with 422
4. **score = 5.5** → Should fail with 422
5. **week_number = 1** → Should succeed
6. **score = 0** → Should succeed
7. **score = 5** → Should succeed

#### Scenario 4: Security Tests
1. **No Authorization header** → Should fail with 401
2. **Invalid token** → Should fail with 401
3. **Expired token** → Should fail with 401
4. **INTERN role attempting update** → Should fail with 403

## Expected HTTP Status Codes

| Scenario | Status Code | Description |
|----------|-------------|-------------|
| Successful update | 200 | OK |
| Successful delete | 204 | No Content |
| Validation error | 422 | Unprocessable Entity |
| Missing authentication | 401 | Unauthorized |
| Invalid/expired token | 401 | Unauthorized |
| Insufficient permissions | 403 | Forbidden |
| Batch restriction violation | 403 | Forbidden |
| Evaluation not found | 404 | Not Found |
| Intern not found | 404 | Not Found |
| Server error | 500 | Internal Server Error |

## Security Testing Checklist

✅ Test with no authentication token
✅ Test with invalid/malformed token
✅ Test with expired token
✅ Test ADMIN accessing all evaluations
✅ Test TECHNICAL_LEAD accessing own batch evaluations
✅ Test TECHNICAL_LEAD attempting to access other batch evaluations
✅ Test TECHNICAL_LEAD attempting to modify restricted fields
✅ Test INTERN attempting to update/delete evaluations
✅ Test payload manipulation (extra fields in request)
✅ Test SQL injection attempts in feedback field
✅ Test XSS attempts in feedback field
✅ Test invalid UUID formats
✅ Test boundary values (week_number=1, score=0, score=5)
✅ Test out-of-range values (week_number=0, score=-1, score=6)

## Notes

- All timestamps are in UTC
- UUIDs must be valid UUID v4 format
- Feedback field is optional and will be trimmed of whitespace
- Partial updates are supported (only send fields you want to update)
- The service layer enforces all restrictions regardless of what the client sends
- Frontend visibility controls are NOT sufficient - all security is server-side
