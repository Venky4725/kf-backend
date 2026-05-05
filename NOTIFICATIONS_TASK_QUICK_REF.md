# Notifications + Task Assignment - Quick Reference

## 🔄 Database Migration

```bash
# Run this first in production
python scripts/migrate_notifications_sender.py
```

```sql
-- What it does:
ALTER TABLE notifications ADD COLUMN IF NOT EXISTS sender_id UUID REFERENCES profiles(id);
```

## 📬 Notifications API Changes

### GET /api/notifications
**NEW Response Format:**
```json
{
  "id": "uuid",
  "user_id": "uuid",
  "sender_id": "uuid",           // NEW
  "sender_name": "John Doe",     // NEW - auto-populated
  "title": "Task Assigned",
  "message": "You have a new task",
  "type": "INFO",
  "is_read": false,
  "is_broadcast": false,
  "created_at": "2024-01-01T00:00:00Z"
}
```

### POST /api/notifications
**NEW Request Body:**
```json
{
  "user_id": "uuid",
  "title": "Task Assigned",
  "message": "You have been assigned a task",
  "type": "INFO",
  "sender_id": "uuid"  // NEW - optional
}
```

### PUT /api/notifications/{id}
**Mark as Read:**
```json
{
  "is_read": true
}
```

## 📋 Task Assignment Changes

### POST /api/tasks
**Cross-Batch Assignment Now Allowed:**
```json
{
  "title": "Complete React Module",
  "batch_id": "batch-1-uuid",
  "assigned_to": "user-from-batch-2-uuid",  // ✅ Different batch OK
  "due_date": "2024-12-31"
}
```

**Validation:**
- ✅ User must exist (404 if not)
- ✅ User must be active (400 if inactive)
- ❌ NO batch restriction (removed)

### PUT /api/tasks/{id}
**Update Assignment:**
```json
{
  "assigned_to": "different-user-uuid"  // ✅ Can be from any batch
}
```

## 🔑 Key Changes Summary

### Notifications:
| Feature | Before | After |
|---------|--------|-------|
| Sender tracking | ❌ No | ✅ Yes (sender_id) |
| Sender name | ❌ No | ✅ Yes (auto-populated) |
| Who sent it | ❌ Unknown | ✅ Visible |

### Task Assignment:
| Feature | Before | After |
|---------|--------|-------|
| Assignment scope | Same batch only | ✅ Any active user |
| Cross-batch | ❌ Blocked (403) | ✅ Allowed |
| Validation | Batch membership | User exists + active |

## 📁 Files Modified

1. `app/models/notification.py` - Added sender_id + relationship
2. `app/schemas/notification.py` - Added sender fields
3. `app/services/notification_service.py` - Sender handling
4. `app/routers/notifications.py` - Response format
5. `app/services/task_service.py` - Removed batch restriction
6. `scripts/migrate_notifications_sender.py` - Migration

## ✅ Testing

### Notifications:
```bash
# Get notifications (should include sender_name)
GET /api/notifications

# Create with sender
POST /api/notifications
{
  "user_id": "uuid",
  "title": "Test",
  "message": "Test message",
  "sender_id": "uuid"
}

# Mark as read
PUT /api/notifications/{id}
{
  "is_read": true
}
```

### Tasks:
```bash
# Assign to user in different batch
POST /api/tasks
{
  "title": "Cross-batch task",
  "batch_id": "batch-1",
  "assigned_to": "user-from-batch-2"
}

# Update assignment
PUT /api/tasks/{id}
{
  "assigned_to": "another-user"
}
```

## 🚀 Result

✅ Notifications show who sent them  
✅ Tasks can be assigned across batches  
✅ Backward compatible  
✅ Production-ready
