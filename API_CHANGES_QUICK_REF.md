# API Changes - Quick Reference

## 🔒 Security Fixes

### Submissions
```
PUT /api/submissions/{id}     → Now requires auth (Owner/TL/Admin only)
DELETE /api/submissions/{id}  → Now requires auth (Owner/TL/Admin only)
```

### Notifications
```
PUT /api/notifications/{id}     → Now requires auth (Owner only)
DELETE /api/notifications/{id}  → Now requires auth (Owner only)
POST /api/notifications/broadcast → Admin only (403 for others)
```

---

## 🆕 New Features

### Task Assignment to Individual
```json
POST /api/tasks
{
  "title": "Complete Tutorial",
  "batch_id": "uuid",
  "assigned_to": "user_uuid",  // NEW - Optional
  "due_date": "2024-12-31"
}
```

**Response includes:**
```json
{
  "id": "uuid",
  "title": "Complete Tutorial",
  "batch_id": "uuid",
  "assigned_to": "user_uuid",  // NEW
  "due_date": "2024-12-31",
  ...
}
```

---

## 🔍 Search & Filter (All Endpoints)

### Batches
```
GET /api/batches?search=react&sort_by=name&order=asc
```

### Tasks
```
GET /api/tasks?search=tutorial&batch_id=<uuid>&sort_by=due_date&order=desc
```

### Evaluations
```
GET /api/evaluations?search=excellent&batch_id=<uuid>&sort_by=score&order=desc
```

### Submissions
```
GET /api/submissions?search=react&batch_id=<uuid>&sort_by=submitted_for&order=desc
```

---

## 📊 Query Parameters

| Parameter | Type | Description | Example |
|-----------|------|-------------|---------|
| `search` | string | Text search | `?search=react` |
| `batch_id` | UUID | Filter by batch | `?batch_id=<uuid>` |
| `sort_by` | string | Sort field | `?sort_by=created_at` |
| `order` | string | asc or desc | `?order=desc` |

---

## 🗄️ Database Migration

**Required:**
```bash
python scripts/migrate_tasks_assigned_to.py
```

**Or manually:**
```sql
ALTER TABLE tasks ADD COLUMN assigned_to UUID REFERENCES profiles(id);
```

---

## 🚨 Error Codes

| Code | Meaning |
|------|---------|
| 200 | Success |
| 401 | Unauthorized (no/invalid token) |
| 403 | Forbidden (no permission) |
| 404 | Not found |

---

## ✅ Access Rules Summary

| Action | Admin | Tech Lead | Intern |
|--------|-------|-----------|--------|
| Edit any submission | ✅ | ❌ (only their batch) | ❌ (only own) |
| Delete any submission | ✅ | ❌ (only their batch) | ❌ (only own) |
| Edit any notification | ❌ | ❌ | ❌ (only own) |
| Delete any notification | ❌ | ❌ | ❌ (only own) |
| Broadcast notification | ✅ | ❌ | ❌ |
| Assign task to any user | ✅ | ❌ (only their batch) | ❌ |

---

**All changes are backward compatible!**
