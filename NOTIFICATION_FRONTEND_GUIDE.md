# Notification Frontend Implementation Guide

## 🔄 API Response Format (Updated)

```json
{
  "id": "uuid",
  "user_id": "receiver-uuid",
  "sender_id": "sender-uuid",
  "sender_name": "John Doe",
  "is_sender": false,
  "title": "Task Assigned",
  "message": "You have been assigned a new task",
  "type": "INFO",
  "is_read": false,
  "is_broadcast": false,
  "created_at": "2024-01-01T00:00:00Z"
}
```

## 🎯 Key Fields

| Field | Type | Description |
|-------|------|-------------|
| `sender_name` | string \| null | Name of person who sent notification |
| `is_sender` | boolean | `true` if current user sent this notification |
| `is_read` | boolean | `true` if notification has been read |

## 📋 UI Logic

### Rule 1: Show Sender Name (Receiver View)
```jsx
{!notification.is_sender && notification.sender_name && (
  <p>From: {notification.sender_name}</p>
)}
```

### Rule 2: Show Read Status (Sender View)
```jsx
{notification.is_sender && (
  <span>
    {notification.is_read ? "✓✓ Seen" : "✓ Sent"}
  </span>
)}
```

### Rule 3: Mark as Read Button (Receiver Only)
```jsx
{!notification.is_sender && !notification.is_read && (
  <button onClick={() => markAsRead(notification.id)}>
    Mark as Read
  </button>
)}
```

### Rule 4: Do NOT Show Mark as Read for Sender
```jsx
// ❌ WRONG - Shows for everyone
<button onClick={() => markAsRead(notification.id)}>
  Mark as Read
</button>

// ✅ CORRECT - Only shows for receiver
{!notification.is_sender && !notification.is_read && (
  <button onClick={() => markAsRead(notification.id)}>
    Mark as Read
  </button>
)}
```

## 💻 Complete React Component Example

```jsx
import React from 'react';
import { formatDistanceToNow } from 'date-fns';

function NotificationCard({ notification, onMarkAsRead }) {
  const handleMarkAsRead = async () => {
    try {
      await fetch(`/api/notifications/${notification.id}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ is_read: true })
      });
      onMarkAsRead(notification.id);
    } catch (error) {
      console.error('Failed to mark as read:', error);
    }
  };

  return (
    <div className={`notification-card ${notification.is_read ? 'read' : 'unread'}`}>
      {/* Header */}
      <div className="notification-header">
        <h3>{notification.title}</h3>
        <span className="time">
          {formatDistanceToNow(new Date(notification.created_at), { addSuffix: true })}
        </span>
      </div>

      {/* Message */}
      <p className="notification-message">{notification.message}</p>

      {/* Footer - Different for Sender vs Receiver */}
      <div className="notification-footer">
        {/* RECEIVER VIEW: Show sender name */}
        {!notification.is_sender && notification.sender_name && (
          <span className="sender-info">
            From: <strong>{notification.sender_name}</strong>
          </span>
        )}

        {/* SENDER VIEW: Show read status */}
        {notification.is_sender && (
          <span className={`read-status ${notification.is_read ? 'seen' : 'sent'}`}>
            {notification.is_read ? (
              <>
                <span className="checkmarks">✓✓</span> Seen
              </>
            ) : (
              <>
                <span className="checkmark">✓</span> Sent
              </>
            )}
          </span>
        )}

        {/* RECEIVER VIEW: Mark as read button */}
        {!notification.is_sender && !notification.is_read && (
          <button 
            onClick={handleMarkAsRead}
            className="mark-read-btn"
          >
            Mark as Read
          </button>
        )}
      </div>
    </div>
  );
}

export default NotificationCard;
```

## 🎨 CSS Styling Example

```css
.notification-card {
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 16px;
  margin-bottom: 12px;
  background: white;
}

.notification-card.unread {
  background: #f0f9ff;
  border-left: 4px solid #3b82f6;
}

.notification-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.notification-header h3 {
  font-size: 16px;
  font-weight: 600;
  margin: 0;
}

.time {
  font-size: 12px;
  color: #6b7280;
}

.notification-message {
  color: #374151;
  margin: 8px 0;
}

.notification-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid #f3f4f6;
}

.sender-info {
  font-size: 14px;
  color: #6b7280;
}

.sender-info strong {
  color: #111827;
}

.read-status {
  font-size: 14px;
  display: flex;
  align-items: center;
  gap: 4px;
}

.read-status.seen {
  color: #10b981;
}

.read-status.sent {
  color: #6b7280;
}

.checkmarks, .checkmark {
  font-weight: bold;
}

.mark-read-btn {
  background: #3b82f6;
  color: white;
  border: none;
  padding: 6px 12px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
}

.mark-read-btn:hover {
  background: #2563eb;
}
```

## 🔍 Decision Tree

```
Is notification.is_sender true?
├─ YES (I sent this)
│  └─ Show: Read status (Sent/Seen)
│  └─ Hide: Sender name, Mark as read button
│
└─ NO (I received this)
   ├─ Show: Sender name (if available)
   └─ Is notification.is_read false?
      ├─ YES (Unread)
      │  └─ Show: Mark as read button
      └─ NO (Already read)
         └─ Hide: Mark as read button
```

## 📊 Visual Examples

### Received Notification (Unread)
```
┌─────────────────────────────────────┐
│ Task Assigned          2 hours ago  │
│                                     │
│ You have been assigned a new task   │
│                                     │
│ From: John Doe    [Mark as Read]   │
└─────────────────────────────────────┘
```

### Received Notification (Read)
```
┌─────────────────────────────────────┐
│ Task Assigned          2 hours ago  │
│                                     │
│ You have been assigned a new task   │
│                                     │
│ From: John Doe                      │
└─────────────────────────────────────┘
```

### Sent Notification (Unread by receiver)
```
┌─────────────────────────────────────┐
│ Task Assigned          2 hours ago  │
│                                     │
│ You have been assigned a new task   │
│                                     │
│                          ✓ Sent     │
└─────────────────────────────────────┘
```

### Sent Notification (Read by receiver)
```
┌─────────────────────────────────────┐
│ Task Assigned          2 hours ago  │
│                                     │
│ You have been assigned a new task   │
│                                     │
│                         ✓✓ Seen     │
└─────────────────────────────────────┘
```

## 🧪 Testing Checklist

- [ ] Received notifications show sender name
- [ ] Sent notifications show "Sent" status
- [ ] Sent notifications show "Seen" when read
- [ ] Mark as read button only appears for received unread notifications
- [ ] Mark as read button doesn't appear for sent notifications
- [ ] Clicking mark as read updates the UI
- [ ] Read notifications have different styling than unread

## 🚀 Quick Start

1. Update your notification component to use `is_sender` field
2. Conditionally render sender name vs read status
3. Only show mark as read button for received notifications
4. Style read/unread notifications differently
5. Test with both sent and received notifications

## ⚠️ Common Mistakes

### ❌ WRONG: Always showing sender name
```jsx
<p>From: {notification.sender_name}</p>
```

### ✅ CORRECT: Only show for received
```jsx
{!notification.is_sender && notification.sender_name && (
  <p>From: {notification.sender_name}</p>
)}
```

### ❌ WRONG: Always showing mark as read
```jsx
<button onClick={markAsRead}>Mark as Read</button>
```

### ✅ CORRECT: Only for received unread
```jsx
{!notification.is_sender && !notification.is_read && (
  <button onClick={markAsRead}>Mark as Read</button>
)}
```

## 📞 API Endpoints

### Get Notifications
```
GET /api/notifications
Returns: Array of notifications (both sent and received)
```

### Mark as Read
```
PUT /api/notifications/{id}
Body: { "is_read": true }
```

## 🎯 Result

✅ Sender name visible for received notifications  
✅ Read status visible for sent notifications  
✅ Mark as read only for received notifications  
✅ WhatsApp-style messaging experience
