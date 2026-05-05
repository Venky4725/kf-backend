# Quick Reference - Backend Updates

## 🎯 What Changed

### 1. Tech Lead Batch Restriction
```
GET /api/batches
```
- Tech Leads see ONLY their assigned batches
- Admins see all batches

### 2. Task Access Control
```
POST /api/tasks
PUT /api/tasks/{id}
DELETE /api/tasks/{id}
```
- Tech Leads can only manage tasks in their assigned batches
- Returns `403 Forbidden` if unauthorized

### 3. Evaluation Access Control
```
POST /api/evaluations
PUT /api/evaluations/{id}
DELETE /api/evaluations/{id}
```
- Tech Leads can only manage evaluations for interns in their assigned batches
- Returns `403 Forbidden` if unauthorized

### 4. Notification Visibility
```
GET /api/notifications
```
- Users see ONLY their own notifications
- No more global visibility

### 5. Broadcast Notifications (NEW)
```
POST /api/notifications/broadcast
Body: { "message": "text", "type": "SYSTEM" }
```
- Sends notification to ALL active users
- Returns recipient count

### 6. Notification Search & Filters
```
GET /api/notifications?search=<text>&type=<type>&is_read=<bool>
```
- `search` - Search in title/message
- `type` - Filter by type (SYSTEM, INFO, etc.)
- `is_read` - Filter by read status

---

## 🗄️ Database Migration

Run this SQL before deploying:

```sql
ALTER TABLE notifications ADD COLUMN IF NOT EXISTS type VARCHAR;
ALTER TABLE notifications ADD COLUMN IF NOT EXISTS is_broadcast BOOLEAN DEFAULT FALSE;
```

---

## 🔒 Access Control Rules

| Action | Admin | Tech Lead | Intern |
|--------|-------|-----------|--------|
| View all batches | ✅ | ❌ (only assigned) | ❌ |
| Create task in any batch | ✅ | ❌ (only assigned) | ❌ |
| Edit task in any batch | ✅ | ❌ (only assigned) | ❌ |
| Delete task in any batch | ✅ | ❌ (only assigned) | ❌ |
| Evaluate any intern | ✅ | ❌ (only in assigned batch) | ❌ |
| Edit any evaluation | ✅ | ❌ (only in assigned batch) | ❌ |
| Delete any evaluation | ✅ | ❌ (only in assigned batch) | ❌ |
| View all notifications | ❌ | ❌ | ❌ |
| View own notifications | ✅ | ✅ | ✅ |
| Broadcast notification | ✅ | ✅ | ❌ |

---

## 📱 Frontend Integration

### Handle 403 Errors
```javascript
if (response.status === 403) {
  toast.error("Access denied: You can only manage resources in your assigned batches");
}
```

### Use New Notification Filters
```javascript
// Search notifications
GET /api/notifications?search=maintenance

// Filter by type
GET /api/notifications?type=SYSTEM

// Get unread only
GET /api/notifications?is_read=false

// Combine filters
GET /api/notifications?search=urgent&type=SYSTEM&is_read=false
```

### Broadcast Notification (Admin UI)
```javascript
POST /api/notifications/broadcast
{
  "message": "System maintenance tonight at 10 PM",
  "type": "SYSTEM"
}

// Response:
{
  "message": "Broadcast notification sent successfully",
  "recipients": 25
}
```

---

## ✅ Testing Commands

```bash
# Test as Tech Lead
curl -H "Authorization: Bearer <tl_token>" \
  http://localhost:8000/api/batches

# Should only return their assigned batches

# Test task creation in wrong batch (should fail)
curl -X POST -H "Authorization: Bearer <tl_token>" \
  -H "Content-Type: application/json" \
  -d '{"title":"Test","batch_id":"<other_batch_id>"}' \
  http://localhost:8000/api/tasks

# Should return 403 Forbidden

# Test broadcast
curl -X POST -H "Authorization: Bearer <admin_token>" \
  -H "Content-Type: application/json" \
  -d '{"message":"Test broadcast","type":"SYSTEM"}' \
  http://localhost:8000/api/notifications/broadcast

# Should return recipient count
```

---

## 🚀 Deployment Checklist

- [ ] Run database migration (add columns to notifications table)
- [ ] Deploy backend code
- [ ] Test Tech Lead access restrictions
- [ ] Test Admin full access
- [ ] Test notification visibility
- [ ] Test broadcast functionality
- [ ] Update frontend error handling for 403 responses
- [ ] Update frontend to use new notification filters
- [ ] Add broadcast UI for admins

---

## 📞 Support

If you encounter issues:

1. Check that database migration ran successfully
2. Verify JWT tokens are valid
3. Check user roles in database
4. Review server logs for detailed error messages
5. Ensure `current_user` is being passed correctly

---

**All changes are backward compatible. Existing functionality continues to work!**
