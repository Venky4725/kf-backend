# Profiles API - Supported Query Parameters

## ✅ YES - Backend Fully Supports These Parameters

The `GET /api/profiles` endpoint supports comprehensive filtering, searching, and sorting.

## Supported Query Parameters

### Pagination:
- `skip` - Offset for pagination (default: 0)
- `limit` - Number of results per page (default: 100)

### Filtering:
- `role` - Filter by role (ADMIN, TECHNICAL_LEAD, INTERN)
- `batch_id` - Filter by batch UUID
- `tech_stack` - Filter by tech stack (exact match, case-insensitive)
- `is_active` - Filter by active status (true/false, default: true)

### Searching:
- `search_name` - Search in name field (partial match, case-insensitive)
- `search_email` - Search in email field (partial match, case-insensitive)

### Sorting:
- `sort_by` - Sort field (name, email, tech_stack, batch)
- `sort_order` - Sort direction (asc, desc)

## API Endpoint

```
GET /api/profiles
```

## Complete Parameter List

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `skip` | integer | No | 0 | Pagination offset |
| `limit` | integer | No | 100 | Results per page |
| `role` | string | No | null | Filter by role |
| `batch_id` | UUID | No | null | Filter by batch |
| `search_name` | string | No | null | Search in name |
| `search_email` | string | No | null | Search in email |
| `tech_stack` | string | No | null | Filter by tech stack |
| `sort_by` | string | No | null | Sort field |
| `sort_order` | string | No | asc | Sort direction |
| `is_active` | boolean | No | true | Filter by active status |

## Example Queries

### 1. Basic Search
```bash
GET /api/profiles?search_name=john
```
Returns all profiles with "john" in the name (case-insensitive)

### 2. Filter by Batch
```bash
GET /api/profiles?batch_id=123e4567-e89b-12d3-a456-426614174000
```
Returns all profiles in the specified batch

### 3. Search + Filter by Batch
```bash
GET /api/profiles?search_name=john&batch_id=123e4567-e89b-12d3-a456-426614174000
```
Returns profiles with "john" in name AND in the specified batch

### 4. Sort by Name
```bash
GET /api/profiles?sort_by=name&sort_order=asc
```
Returns profiles sorted by name in ascending order

### 5. Combined: Search + Filter + Sort
```bash
GET /api/profiles?search_name=john&batch_id=123e4567-e89b-12d3-a456-426614174000&sort_by=name&sort_order=asc
```
Returns profiles with "john" in name, in specified batch, sorted by name

### 6. Filter by Role
```bash
GET /api/profiles?role=INTERN
```
Returns only interns

### 7. Filter by Tech Stack
```bash
GET /api/profiles?tech_stack=React
```
Returns profiles with React tech stack

### 8. Search Email
```bash
GET /api/profiles?search_email=@gmail.com
```
Returns profiles with Gmail addresses

### 9. Get Inactive Profiles (Archives)
```bash
GET /api/profiles?is_active=false
```
Returns deactivated profiles

### 10. Complex Query
```bash
GET /api/profiles?role=INTERN&batch_id=123&search_name=john&sort_by=name&sort_order=asc&limit=50
```
Returns first 50 interns named "john" in batch 123, sorted by name

## Response Format

```json
[
  {
    "id": "uuid",
    "name": "John Doe",
    "email": "john@example.com",
    "role": "INTERN",
    "tech_stack": "React",
    "batch_id": "uuid",
    "is_active": true,
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-01T00:00:00Z"
  }
]
```

## Valid Sort Fields

The `sort_by` parameter accepts these values:
- `name` - Sort by profile name
- `email` - Sort by email address
- `tech_stack` - Sort by tech stack
- `batch` - Sort by batch name (joins with batch table)

**Note:** Invalid sort fields are ignored and default sorting is applied.

## Valid Sort Orders

The `sort_order` parameter accepts:
- `asc` - Ascending order (A-Z, 0-9)
- `desc` - Descending order (Z-A, 9-0)

**Default:** `asc` if not specified

## Search Behavior

### Partial Match:
- `search_name` and `search_email` use `LIKE '%search%'`
- Case-insensitive matching
- Matches anywhere in the field

**Examples:**
- `search_name=john` matches "John", "Johnny", "Johnson"
- `search_email=gmail` matches "user@gmail.com", "test.gmail@example.com"

### Exact Match:
- `tech_stack` uses exact match (case-insensitive)
- `role` uses exact match (case-insensitive)

## Filter Combination

All filters work together with AND logic:

```bash
GET /api/profiles?role=INTERN&batch_id=123&search_name=john
```

This returns profiles that are:
- Role = INTERN **AND**
- Batch ID = 123 **AND**
- Name contains "john"

## Default Behavior

### Without Parameters:
```bash
GET /api/profiles
```
Returns:
- First 100 active profiles
- Sorted by created_at descending
- All roles included

### With is_active:
```bash
GET /api/profiles?is_active=false
```
Returns deactivated profiles (archives)

## Frontend Usage Examples

### React/TypeScript:
```typescript
// Search by name
const searchProfiles = async (name: string) => {
  const response = await fetch(
    `/api/profiles?search_name=${encodeURIComponent(name)}`
  );
  return response.json();
};

// Filter by batch
const getProfilesByBatch = async (batchId: string) => {
  const response = await fetch(
    `/api/profiles?batch_id=${batchId}`
  );
  return response.json();
};

// Combined search and filter
const searchInBatch = async (name: string, batchId: string) => {
  const params = new URLSearchParams({
    search_name: name,
    batch_id: batchId,
    sort_by: 'name',
    sort_order: 'asc'
  });
  const response = await fetch(`/api/profiles?${params}`);
  return response.json();
};

// Get inactive profiles
const getArchivedProfiles = async () => {
  const response = await fetch('/api/profiles?is_active=false');
  return response.json();
};
```

## Performance Considerations

### Efficient Queries:
- All filters applied at database level
- Indexed columns: email, batch_id
- Pagination limits result size

### Sorting with Batch:
- `sort_by=batch` performs a LEFT JOIN with batches table
- Slightly slower than other sort fields
- Still efficient due to indexed foreign key

## Testing Checklist

- [x] Search by name works
- [x] Search by email works
- [x] Filter by batch_id works
- [x] Filter by role works
- [x] Filter by tech_stack works
- [x] Sort by name works
- [x] Sort by email works
- [x] Sort by batch works
- [x] Combined filters work
- [x] Pagination works
- [x] is_active filter works

## Summary

✅ **YES - Backend fully supports:**
- `search` (via search_name and search_email)
- `batch_id` filtering
- `sort_by` sorting
- `order` (via sort_order)

✅ **Additional features:**
- Role filtering
- Tech stack filtering
- Active/inactive filtering
- Email search
- Pagination

✅ **Production-ready with comprehensive query support**
