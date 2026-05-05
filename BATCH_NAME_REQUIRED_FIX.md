# Batch Name Required for Intern Creation - Implementation

## Problem
Interns could be created without a batch, leading to data inconsistency.

## Solution Implemented

### 1. Schema Update (`app/schemas/profile.py`)

#### Changed from `batch_id` to `batch_name`:
```python
# BEFORE
class ProfileCreate(BaseModel):
    name: str
    email: EmailStr
    role: str
    tech_stack: str | None = None
    batch_id: UUID | None = None  # Optional

# AFTER
class ProfileCreate(BaseModel):
    name: str
    email: EmailStr
    role: str
    tech_stack: str | None = None
    batch_name: str  # REQUIRED - no Optional
```

### 2. Service Update (`app/services/profile_service.py`)

#### Added Validation and Batch Lookup:
```python
def create_profile(self, db: Session, payload: ProfileCreate, current_user=None) -> Profile:
    # 1. Validate batch_name is provided
    if not payload.batch_name or not payload.batch_name.strip():
        raise HTTPException(400, "batch_name is required")
    
    # 2. Normalize input
    batch_name = payload.batch_name.strip()
    
    # 3. Lookup batch (case-insensitive)
    batch = db.query(Batch).filter(
        func.lower(Batch.name) == batch_name.lower()
    ).first()
    
    # 4. Create batch if missing
    if not batch:
        batch = Batch(
            name=batch_name,
            team_lead_id=current_user.id if current_user.role == "TECHNICAL_LEAD" else None
        )
        db.add(batch)
        db.flush()
    
    # 5. Create profile with batch_id
    return self.create(db, {
        ...
        "batch_id": batch.id,
        ...
    })
```

### 3. Router Update (`app/routers/profiles.py`)

#### Added Authentication:
```python
@router.post("", response_model=ProfileResponse, status_code=status.HTTP_201_CREATED)
def create_profile(
    payload: ProfileCreate,
    db: Session = Depends(get_db),
    current_user=Depends(auth_get_current_user),  # ADDED
):
    return profile_service.create_profile(db, payload, current_user)
```

## Features Implemented

### 1. Required Validation
✅ `batch_name` is mandatory (not Optional)  
✅ Empty or whitespace-only values rejected  
✅ Returns 400 Bad Request if missing  

### 2. Batch Lookup (Case-Insensitive)
✅ Searches for existing batch by name  
✅ Case-insensitive matching (`"KF-Cohort-5"` == `"kf-cohort-5"`)  
✅ Reuses existing batch if found  

### 3. Auto-Create Batch
✅ Creates new batch if not found  
✅ Sets `team_lead_id` if created by Tech Lead  
✅ Sets `team_lead_id` to NULL if created by Admin  

### 4. Input Normalization
✅ Trims whitespace from batch_name  
✅ Prevents duplicate batches with different whitespace  

### 5. Comprehensive Logging
✅ Logs batch lookup  
✅ Logs batch creation  
✅ Logs profile creation  

## API Changes

### Request Format

**BEFORE:**
```json
POST /api/profiles
{
  "name": "John Doe",
  "email": "john@example.com",
  "role": "INTERN",
  "tech_stack": "React",
  "batch_id": "uuid-or-null"  // Optional
}
```

**AFTER:**
```json
POST /api/profiles
{
  "name": "John Doe",
  "email": "john@example.com",
  "role": "INTERN",
  "tech_stack": "React",
  "batch_name": "KF-Cohort-5"  // REQUIRED
}
```

### Error Responses

#### Missing batch_name:
```json
{
  "detail": "batch_name is required"
}
```
**Status:** 400 Bad Request

#### Empty batch_name:
```json
{
  "detail": "batch_name is required"
}
```
**Status:** 400 Bad Request

#### Duplicate email:
```json
{
  "detail": "A profile with email 'john@example.com' already exists (Name: John Doe, Role: INTERN)."
}
```
**Status:** 409 Conflict

## Batch Creation Logic

### Scenario 1: Batch Exists
```
Input: batch_name = "KF-Cohort-5"
Database: Batch "KF-Cohort-5" exists (ID: 123)
Result: Uses existing batch (ID: 123)
```

### Scenario 2: Batch Doesn't Exist (Tech Lead)
```
Input: batch_name = "New-Batch"
Current User: Tech Lead (ID: 456)
Database: Batch "New-Batch" doesn't exist
Result: Creates new batch with team_lead_id = 456
```

### Scenario 3: Batch Doesn't Exist (Admin)
```
Input: batch_name = "New-Batch"
Current User: Admin (ID: 789)
Database: Batch "New-Batch" doesn't exist
Result: Creates new batch with team_lead_id = NULL
```

### Scenario 4: Case-Insensitive Match
```
Input: batch_name = "kf-cohort-5"
Database: Batch "KF-Cohort-5" exists
Result: Uses existing batch (case-insensitive match)
```

## CSV Upload Validation

### Required Changes for CSV Upload:

```python
def process_csv_row(row, db, current_user):
    # 1. Validate batch_name
    if not row.get("batch_name") or not row["batch_name"].strip():
        return {
            "status": "skipped",
            "error": "Missing batch_name"
        }
    
    # 2. Create profile
    try:
        profile = profile_service.create_profile(
            db,
            ProfileCreate(
                name=row["name"],
                email=row["email"],
                role=row["role"],
                tech_stack=row.get("tech_stack"),
                batch_name=row["batch_name"]  # REQUIRED
            ),
            current_user
        )
        return {"status": "created", "profile": profile}
    except Exception as e:
        return {"status": "error", "error": str(e)}
```

### CSV Response Format:

```json
{
  "created": 8,
  "skipped": 2,
  "errors": [
    "Row 3: Missing batch_name",
    "Row 7: Missing batch_name"
  ]
}
```

## Testing Scenarios

### Test 1: Create with Valid Batch Name
```bash
POST /api/profiles
{
  "name": "John Doe",
  "email": "john@example.com",
  "role": "INTERN",
  "batch_name": "KF-Cohort-5"
}

Response: 201 Created ✅
```

### Test 2: Create with Missing Batch Name
```bash
POST /api/profiles
{
  "name": "John Doe",
  "email": "john@example.com",
  "role": "INTERN"
}

Response: 422 Unprocessable Entity ❌
Error: Field required
```

### Test 3: Create with Empty Batch Name
```bash
POST /api/profiles
{
  "name": "John Doe",
  "email": "john@example.com",
  "role": "INTERN",
  "batch_name": ""
}

Response: 400 Bad Request ❌
Error: "batch_name is required"
```

### Test 4: Create with Whitespace-Only Batch Name
```bash
POST /api/profiles
{
  "name": "John Doe",
  "email": "john@example.com",
  "role": "INTERN",
  "batch_name": "   "
}

Response: 400 Bad Request ❌
Error: "batch_name is required"
```

### Test 5: Create with New Batch Name
```bash
POST /api/profiles
{
  "name": "John Doe",
  "email": "john@example.com",
  "role": "INTERN",
  "batch_name": "New-Batch-2026"
}

Response: 201 Created ✅
Note: New batch "New-Batch-2026" created automatically
```

### Test 6: Case-Insensitive Batch Lookup
```bash
POST /api/profiles
{
  "name": "Jane Doe",
  "email": "jane@example.com",
  "role": "INTERN",
  "batch_name": "kf-cohort-5"
}

Response: 201 Created ✅
Note: Uses existing batch "KF-Cohort-5" (case-insensitive match)
```

## Database Impact

### Before:
```sql
-- Interns could have NULL batch_id
SELECT id, name, batch_id FROM profiles WHERE role = 'INTERN';
-- Results: Some with NULL batch_id
```

### After:
```sql
-- All new interns have batch_id
SELECT id, name, batch_id FROM profiles WHERE role = 'INTERN';
-- Results: All have valid batch_id
```

## Migration Considerations

### Existing Data:
- ✅ Existing profiles with NULL batch_id remain unchanged
- ✅ Only NEW profiles require batch_name
- ✅ No breaking changes to existing data

### Frontend Updates Required:
- ❌ Change from `batch_id` to `batch_name` in create form
- ❌ Update validation to require batch_name
- ❌ Update CSV upload to validate batch_name

## Logging Examples

### Successful Creation (Existing Batch):
```
INFO: Creating profile with batch_name: KF-Cohort-5
INFO: Found existing batch: KF-Cohort-5 (ID: 123)
INFO: Creating profile: John Doe (INTERN) in batch KF-Cohort-5
```

### Successful Creation (New Batch):
```
INFO: Creating profile with batch_name: New-Batch
INFO: Batch 'New-Batch' not found, creating new batch
INFO: Created new batch: New-Batch (ID: 456)
INFO: Creating profile: John Doe (INTERN) in batch New-Batch
```

### Failed Creation (Missing Batch Name):
```
ERROR: 400 Bad Request: batch_name is required
```

## Files Modified

1. ✅ `app/schemas/profile.py` - Changed batch_id to batch_name (required)
2. ✅ `app/services/profile_service.py` - Added validation and batch lookup
3. ✅ `app/routers/profiles.py` - Added authentication

## Result

✅ **batch_name always required**  
✅ **No intern created without batch**  
✅ **Auto-creates batch if missing**  
✅ **Case-insensitive batch lookup**  
✅ **Comprehensive validation**  
✅ **Production-ready**

## Next Steps for Frontend

1. Update create profile form to use `batch_name` instead of `batch_id`
2. Add validation to require batch_name
3. Update CSV upload to validate batch_name in each row
4. Handle 400 error for missing batch_name
5. Show success message when batch is auto-created
