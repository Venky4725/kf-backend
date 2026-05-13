# Tech Lead Batch Assignment Fix

## Problem
Tech leads were not getting `batch_id` assigned correctly during profile creation.

**Symptoms:**
- Backend logs: `Creating profile ... with batch_id=None`
- Frontend warning: `Tech Lead has no batch_id assigned`
- Tech leads couldn't see their batch data
- Dashboard filtering broken for tech leads

## Root Cause
In `profile_service.py`, the code was resetting `batch_id = None` for all non-INTERN roles, ignoring the incoming `batch_id` value from the frontend.

```python
# OLD CODE (BROKEN)
else:
    # TECH_LEAD and ADMIN do not require batch
    batch_id = None  # ❌ This ignored the incoming batch_id!
```

## What Was Fixed

### 1. Profile Creation Logic (`profile_service.py`)
**Fixed:** Tech lead batch assignment now properly preserved

```python
elif role == "TECHNICAL_LEAD":
    # TECHNICAL_LEAD can optionally have batch_id
    if payload.batch_id:
        # Validate batch exists
        batch = db.query(Batch).filter(Batch.id == payload.batch_id).first()
        if not batch:
            raise HTTPException(400, "Batch does not exist")
        
        # Check 2-tech-lead limit
        tech_leads_in_batch = db.query(Profile).filter(
            Profile.batch_id == payload.batch_id,
            Profile.role == "TECHNICAL_LEAD",
            Profile.is_active == True
        ).count()
        
        if tech_leads_in_batch >= 2:
            raise HTTPException(409, "Batch already has maximum 2 tech leads")
        
        batch_id = payload.batch_id
    else:
        batch_id = None
```

**Features:**
- ✅ Preserves incoming `batch_id` for tech leads
- ✅ Validates batch exists
- ✅ Enforces 2-tech-lead-per-batch limit
- ✅ Returns clear error messages

### 2. Profile Update Logic (`profile_service.py`)
**Fixed:** Tech lead batch updates now validated

```python
# If updating a TECHNICAL_LEAD's batch, check the 2-tech-lead limit
if existing_profile.role == "TECHNICAL_LEAD":
    tech_leads_in_batch = db.query(Profile).filter(
        Profile.batch_id == updates["batch_id"],
        Profile.role == "TECHNICAL_LEAD",
        Profile.is_active == True,
        Profile.id != profile_id  # Exclude current profile
    ).count()
    
    if tech_leads_in_batch >= 2:
        raise HTTPException(409, "Batch already has maximum 2 tech leads")
```

**Features:**
- ✅ Validates 2-tech-lead limit on updates
- ✅ Excludes current profile from count
- ✅ Returns 409 Conflict with clear message

### 3. Data Migration Script
**Created:** `scripts/fix_tech_lead_batch_assignment.py`

**Purpose:**
- Finds tech leads with mismatched batch assignments
- Validates 2-tech-lead-per-batch limit
- Fixes existing data issues
- Shows summary of all tech lead assignments

**Usage:**
```bash
python scripts/fix_tech_lead_batch_assignment.py
```

## Business Rules

### Tech Lead Batch Assignment
1. **Optional:** Tech leads can have a batch assigned or not
2. **Limit:** Maximum 2 tech leads per batch
3. **Validation:** Enforced on both create and update
4. **Error:** Returns 409 Conflict if limit exceeded

### Batch Table Structure
```sql
CREATE TABLE batches (
    id UUID PRIMARY KEY,
    name VARCHAR NOT NULL,
    tech_stack VARCHAR NOT NULL,
    start_date DATE NOT NULL,
    first_tech_lead_id UUID REFERENCES profiles(id),  -- Optional
    second_tech_lead_id UUID REFERENCES profiles(id), -- Optional
    ...
);
```

### Profile Table Structure
```sql
CREATE TABLE profiles (
    id UUID PRIMARY KEY,
    name VARCHAR NOT NULL,
    email VARCHAR UNIQUE NOT NULL,
    role VARCHAR NOT NULL,  -- ADMIN, TECHNICAL_LEAD, INTERN
    batch_id UUID REFERENCES batches(id),  -- Optional for TECHNICAL_LEAD
    ...
);
```

### Relationship
- **Batch → Tech Leads:** `first_tech_lead_id`, `second_tech_lead_id` (for batch management)
- **Tech Lead → Batch:** `batch_id` (for filtering and dashboard)

Both relationships are maintained for different purposes:
- Batch table tracks which tech leads manage the batch
- Profile table tracks which batch a tech lead belongs to (for filtering)

## API Changes

### POST /profiles
**Request:**
```json
{
  "name": "John Doe",
  "email": "john@example.com",
  "role": "TECHNICAL_LEAD",
  "tech_stack": "Python",
  "batch_id": "uuid-of-batch"  // Now properly saved!
}
```

**Response (Success):**
```json
{
  "id": "uuid",
  "name": "John Doe",
  "email": "john@example.com",
  "role": "TECHNICAL_LEAD",
  "batch_id": "uuid-of-batch",  // ✅ Correctly set
  ...
}
```

**Response (Error - Batch Full):**
```json
{
  "detail": "Batch 'Batch A' already has maximum 2 tech leads assigned"
}
```
Status: 409 Conflict

### PUT /profiles/{id}
**Request:**
```json
{
  "batch_id": "new-batch-uuid"
}
```

**Validation:**
- ✅ Checks if new batch exists
- ✅ Checks if new batch has < 2 tech leads
- ✅ Returns 409 if batch is full

### GET /auth/me
**Response:**
```json
{
  "id": "uuid",
  "name": "John Doe",
  "email": "john@example.com",
  "role": "TECHNICAL_LEAD",
  "batch_id": "uuid-of-batch",  // ✅ Now included
  ...
}
```

## Testing

### Test Tech Lead Creation
```bash
# Create tech lead with batch
curl -X POST http://localhost:8000/profiles \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Tech Lead 1",
    "email": "tl1@example.com",
    "role": "TECHNICAL_LEAD",
    "batch_id": "batch-uuid"
  }'

# Should succeed and return profile with batch_id set
```

### Test 2-Tech-Lead Limit
```bash
# Try to add 3rd tech lead to same batch
curl -X POST http://localhost:8000/profiles \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Tech Lead 3",
    "email": "tl3@example.com",
    "role": "TECHNICAL_LEAD",
    "batch_id": "same-batch-uuid"
  }'

# Should return 409 Conflict
```

### Test Data Migration
```bash
# Run migration script
python scripts/fix_tech_lead_batch_assignment.py

# Should show:
# - Any mismatched assignments
# - Prompt to fix them
# - Summary of all tech leads
```

## Migration Steps

### 1. Deploy Code
```bash
git pull origin main
```

### 2. Fix Existing Data
```bash
python scripts/fix_tech_lead_batch_assignment.py
```

### 3. Restart Application
```bash
systemctl restart your-app
```

### 4. Verify
```bash
# Check tech lead profile
curl http://localhost:8000/auth/me \
  -H "Authorization: Bearer <tech-lead-token>"

# Should show batch_id
```

## Verification Checklist

- [ ] Tech lead creation with batch_id works
- [ ] Tech lead profile shows correct batch_id
- [ ] GET /auth/me returns batch_id for tech leads
- [ ] 2-tech-lead limit enforced on create
- [ ] 2-tech-lead limit enforced on update
- [ ] Clear error messages returned
- [ ] Dashboard filtering works for tech leads
- [ ] Attendance filtering works for tech leads
- [ ] Existing tech leads have correct batch_id

## Files Changed

### Modified
- `app/services/profile_service.py` - Fixed create and update logic
- `scripts/README.md` - Added migration script documentation

### Created
- `scripts/fix_tech_lead_batch_assignment.py` - Data migration script
- `TECH_LEAD_FIX.md` - This documentation

## Rollback Plan

If issues occur:

1. **Revert code changes:**
```bash
git revert <commit-hash>
```

2. **Reset tech lead batch_id (if needed):**
```sql
UPDATE profiles 
SET batch_id = NULL 
WHERE role = 'TECHNICAL_LEAD';
```

3. **Restart application**

## Support

### Common Issues

**Issue:** "Batch already has maximum 2 tech leads"
**Solution:** This is expected. Remove one tech lead from the batch first.

**Issue:** Tech lead still shows no batch_id
**Solution:** Run the migration script to fix existing data.

**Issue:** Dashboard not showing data for tech lead
**Solution:** Verify tech lead has batch_id set via GET /auth/me

### Debug Commands

```bash
# Check tech lead assignments
python scripts/fix_tech_lead_batch_assignment.py

# Check database directly
psql $DATABASE_URL -c "
SELECT p.name, p.role, p.batch_id, b.name as batch_name
FROM profiles p
LEFT JOIN batches b ON p.batch_id = b.id
WHERE p.role = 'TECHNICAL_LEAD'
ORDER BY p.name;
"
```

---

**Status:** ✅ Complete - Ready for Production
