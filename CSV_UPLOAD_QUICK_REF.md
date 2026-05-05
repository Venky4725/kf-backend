# CSV Upload - Quick Reference

## ✅ Endpoint Added

```
POST /api/profiles/upload-csv
```

## 📋 CSV Format

```csv
name,email,role,tech_stack,batch_name
John Doe,john@example.com,INTERN,React,KF-Cohort-5
Jane Smith,jane@example.com,INTERN,Python,KF-Cohort-5
```

## ⚠️ Required Columns

- `name` - Profile name
- `email` - Email address
- `role` - Role (ADMIN, TECHNICAL_LEAD, INTERN)
- `batch_name` - Batch name (REQUIRED)

## 📊 Response Format

```json
{
  "created": 8,
  "skipped": 2,
  "errors": [
    "Row 3: Missing batch_name",
    "Row 7: Missing email"
  ]
}
```

## 🔧 Validation Rules

| Field | Required | Action if Missing |
|-------|----------|-------------------|
| name | ✅ Yes | Skip row |
| email | ✅ Yes | Skip row |
| role | ✅ Yes | Skip row |
| batch_name | ✅ Yes | Skip row |
| tech_stack | ❌ No | Use NULL |

## 🚀 Usage Example

```javascript
const formData = new FormData();
formData.append('file', csvFile);

const response = await fetch('/api/profiles/upload-csv', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`
  },
  body: formData
});

const result = await response.json();
```

## ✅ Result

✅ Endpoint exists  
✅ No 405 error  
✅ Validates batch_name  
✅ Skips invalid rows  
✅ Production-ready
