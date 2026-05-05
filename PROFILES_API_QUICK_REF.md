# Profiles API - Quick Reference

## ✅ YES - Fully Supported

```
GET /api/profiles?search_name=&batch_id=&sort_by=&sort_order=
```

## Quick Examples

### Search by Name:
```
GET /api/profiles?search_name=john
```

### Filter by Batch:
```
GET /api/profiles?batch_id=uuid
```

### Search + Filter:
```
GET /api/profiles?search_name=john&batch_id=uuid
```

### Sort by Name:
```
GET /api/profiles?sort_by=name&sort_order=asc
```

### Complete Query:
```
GET /api/profiles?search_name=john&batch_id=uuid&sort_by=name&sort_order=asc
```

## All Supported Parameters

| Parameter | Example |
|-----------|---------|
| `search_name` | `?search_name=john` |
| `search_email` | `?search_email=gmail` |
| `batch_id` | `?batch_id=uuid` |
| `role` | `?role=INTERN` |
| `tech_stack` | `?tech_stack=React` |
| `sort_by` | `?sort_by=name` |
| `sort_order` | `?sort_order=asc` |
| `is_active` | `?is_active=false` |
| `skip` | `?skip=0` |
| `limit` | `?limit=100` |

## Valid Sort Fields

- `name`
- `email`
- `tech_stack`
- `batch`

## Valid Sort Orders

- `asc` (default)
- `desc`

## Result

✅ **Backend fully supports all requested parameters**  
✅ **Plus additional search and filter options**  
✅ **Production-ready**
