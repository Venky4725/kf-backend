# Tech Lead Batch Update Fix

## Problem
Tech Lead was blocked when trying to change an intern's `batch_id` because the access control only checked if the intern was currently in their batch.

## Solution Implemented

### Updated Access Control Logic

**Before:**
```python
# Tech Lead could only update interns already in their batch
elif existing_profile.role == "INTERN" and existing_profile.batch_id == current_user.batch_id:
    pass  # Allow
else:
    raise HTTPException(403)  # Block
```

**After:**
```python
# Tech Lead can update interns in their batch OR assign interns TO their batch
elif existing_profile.role == "INTERN":
    # Allow if intern is currently in their batch
    if existing_profile.batch_id == current_user.batch_id:
        pass  # Allow
    # Also allow if Tech Lead is assigning intern TO their batch
    elif "batch_id" in payload and payload.batch_id == current_user.batch_id:
        pass  # Allow
    else:
        raise HTTPException(403)  # Block
```

## Access Control Rules (Updated)

### ADMIN:
✅ Can update ANY profile  
✅ Can change batch_id to ANY batch  

### TECH_LEAD:
✅ Can update their own profile  
✅ Can update interns currently in their batch  
✅ **NEW:** Can assign interns TO their batch (even if intern is in different batch or no batch)  
✅ **NEW:** Can change batch_id for interns in their batch  
❌ Cannot update interns in other batches (unless assigning to their batch)  
❌ Cannot update other Tech Leads or Admins  

### INTERN:
✅ Can update their own profile  
❌ Cannot update any other profile  
❌ Cannot change their own batch_id  

## Use Cases Now Supported

### Use Case 1: Reassign Intern Within Same Batch
```
Tech Lead (batch: A) updates Intern (batch: A)
Change: name, email, tech_stack, batch_id
Result: ✅ Allowed
```

### Use Case 2: Assign Unassigned Intern to Their Batch
```
Tech Lead (batch: A) updates Intern (batch: null)
Change: batch_id = A
Result: ✅ Allowed (NEW)
```

### Use Case 3: Move Intern From Another Batch to Their Batch
```
Tech Lead (batch: A) updates Intern (batch: B)
Change: batch_id = A
Result: ✅ Allowed (NEW)
```

### Use Case 4: Move Intern From Their Batch to Another Batch
```
Tech Lead (batch: A) updates Intern (batch: A)
Change: batch_id = B
Result: ✅ Allowed (NEW)
```

### Use Case 5: Update Intern in Another Batch (Not Assigning to Their Batch)
```
Tech Lead (batch: A) updates Intern (batch: B)
Change: name = "New Name" (no batch_id change)
Result: ❌ Blocked (403)
```

### Use Case 6: Move Intern From Another Batch to Yet Another Batch
```
Tech Lead (batch: A) updates Intern (batch: B)
Change: batch_id = C
Result: ❌ Blocked (403)
```

## Decision Tree

```
Is current_user ADMIN?
├─ YES → ✅ Allow all updates
└─ NO → Is current_user TECH_LEAD?
    ├─ YES → Is target profile an INTERN?
    │   ├─ YES → Is intern currently in Tech Lead's batch?
    │   │   ├─ YES → ✅ Allow (can change batch_id)
    │   │   └─ NO → Is Tech Lead assigning intern TO their batch?
    │   │       ├─ YES → ✅ Allow
    │   │       └─ NO → ❌ Block (403)
    │   └─ NO → Is target profile Tech Lead's own profile?
    │       ├─ YES → ✅ Allow
    │       └─ NO → ❌ Block (403)
    └─ NO → Is current_user INTERN?
        └─ Is target profile their own profile?
            ├─ YES → ✅ Allow (except batch_id change)
            └─ NO → ❌ Block (403)
```

## Examples

### Example 1: Tech Lead Assigns New Intern to Their Batch
```bash
# Tech Lead (batch_id: 123) assigns unassigned intern
PUT /api/profiles/intern-uuid
Authorization: Bearer {tech_lead_token}
Body: {
  "batch_id": "123"
}

Response: 200 OK ✅
Log: "Tech Lead assigning intern to their batch (batch_id: 123)"
```

### Example 2: Tech Lead Moves Intern From Their Batch to Another
```bash
# Tech Lead (batch_id: 123) moves intern to batch 456
PUT /api/profiles/intern-uuid
Authorization: Bearer {tech_lead_token}
Body: {
  "batch_id": "456"
}

Response: 200 OK ✅
Log: "Tech Lead updating intern in their batch (batch_id: 123)"
```

### Example 3: Tech Lead Tries to Update Intern in Different Batch
```bash
# Tech Lead (batch_id: 123) tries to update intern in batch 456
PUT /api/profiles/intern-uuid
Authorization: Bearer {tech_lead_token}
Body: {
  "name": "New Name"
}

Response: 403 Forbidden ❌
Error: "You can only update interns in your batch or assign interns to your batch"
```

### Example 4: Tech Lead Steals Intern From Another Batch
```bash
# Tech Lead (batch_id: 123) takes intern from batch 456
PUT /api/profiles/intern-uuid
Authorization: Bearer {tech_lead_token}
Body: {
  "batch_id": "123"
}

Response: 200 OK ✅
Log: "Tech Lead assigning intern to their batch (batch_id: 123)"
```

## Security Considerations

### What's Allowed:
✅ Tech Lead can manage interns in their batch  
✅ Tech Lead can recruit interns to their batch  
✅ Tech Lead can reassign interns from their batch  

### What's Blocked:
❌ Tech Lead cannot update interns in other batches (unless recruiting)  
❌ Tech Lead cannot update other Tech Leads  
❌ Tech Lead cannot update Admins  
❌ Intern cannot change their own batch  

## Logging

The updated code logs all access control decisions:

```
INFO: Tech Lead updating intern in their batch (batch_id: 123)
INFO: Tech Lead assigning intern to their batch (batch_id: 123)
WARNING: Tech Lead 456 attempted to update intern 789 not in their batch
```

## Testing Scenarios

### Scenario 1: Assign Unassigned Intern
```
Given: Intern with batch_id = null
When: Tech Lead (batch: A) sets batch_id = A
Then: ✅ Success
```

### Scenario 2: Move Intern Between Batches
```
Given: Intern with batch_id = A
When: Tech Lead (batch: A) sets batch_id = B
Then: ✅ Success
```

### Scenario 3: Recruit Intern From Another Batch
```
Given: Intern with batch_id = B
When: Tech Lead (batch: A) sets batch_id = A
Then: ✅ Success
```

### Scenario 4: Update Intern in Another Batch
```
Given: Intern with batch_id = B
When: Tech Lead (batch: A) updates name (no batch_id change)
Then: ❌ 403 Forbidden
```

### Scenario 5: Move Intern Between Other Batches
```
Given: Intern with batch_id = B
When: Tech Lead (batch: A) sets batch_id = C
Then: ❌ 403 Forbidden
```

## Files Modified

1. ✅ `app/services/profile_service.py` - Updated access control logic

## Result

✅ **Tech Lead can now reassign interns between batches**  
✅ **Tech Lead can assign unassigned interns to their batch**  
✅ **Tech Lead can move interns from their batch to other batches**  
✅ **Tech Lead can recruit interns from other batches**  
✅ **Security maintained - cannot update interns in other batches (unless recruiting)**  
✅ **Comprehensive logging for debugging**
