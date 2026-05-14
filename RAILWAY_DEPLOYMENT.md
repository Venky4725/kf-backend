# Railway Deployment Guide - Backend Stabilization

## ✅ Pre-Deployment Status

All code changes are complete and verified:
- ✅ All Python files compile without errors
- ✅ No circular import issues
- ✅ Batch enrichment implemented
- ✅ Notification system enhanced
- ✅ Error handlers centralized
- ✅ Migration script ready

---

## 🚀 Deployment Steps for Railway

### Step 1: Commit and Push Changes

```bash
# Add all changes
git add .

# Commit with descriptive message
git commit -m "Backend stabilization: Fix batch display, enhance notifications, add error handling"

# Push to main branch (Railway will auto-deploy)
git push origin main
```

### Step 2: Monitor Railway Deployment

1. Go to Railway dashboard
2. Watch the build logs
3. Ensure build completes successfully
4. Wait for deployment to finish

**Expected Build Output:**
```
Building...
Installing dependencies...
Build completed successfully
Deploying...
Deployment successful
```

### Step 3: Run Database Migration (IMPORTANT!)

Once deployment is complete, run the migration script on Railway:

**Option A: Using Railway CLI**
```bash
# Install Railway CLI if not already installed
npm i -g @railway/cli

# Login to Railway
railway login

# Link to your project
railway link

# Run migration
railway run python scripts/backend_stabilization_migration.py
```

**Option B: Using Railway Dashboard**
1. Go to your Railway project
2. Click on your service
3. Go to "Settings" → "Variables"
4. Add a one-time deployment command or use the Railway shell
5. Run: `python scripts/backend_stabilization_migration.py`

**Option C: Add to Procfile (Recommended)**

Update your `Procfile` to run migration on startup:

```
release: python scripts/backend_stabilization_migration.py
web: uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

This ensures migration runs automatically before each deployment.

### Step 4: Verify Deployment

**Check Health Endpoint:**
```bash
curl https://your-app.railway.app/api/health
```

Expected response:
```json
{"status": "ok"}
```

**Check Batch Endpoint:**
```bash
curl https://your-app.railway.app/api/batches
```

Verify response includes `tech_leads_display` field.

**Check Notifications Endpoint:**
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
  https://your-app.railway.app/api/notifications
```

Verify response includes `sender_name` and `edited_at` fields.

---

## 🔍 What the Migration Does

The migration script will:

1. **Add Missing Column**
   - Adds `notifications.edited_at` column
   - Safe operation (uses IF NOT EXISTS)

2. **Ensure Enum Values**
   - Verifies `attendance_status` enum includes LATE
   - Adds if missing

3. **Add Performance Indexes**
   - Creates indexes for common queries
   - Improves performance

4. **Verify Integrity**
   - Checks foreign keys
   - Validates data integrity
   - Reports any issues

**Migration is safe to run multiple times** - it checks before making changes.

---

## 📊 Expected Changes After Deployment

### API Response Changes

#### Batch Responses (All Endpoints)
**Before:**
```json
{
  "id": "uuid",
  "name": "Batch A",
  "first_tech_lead_id": "uuid",
  "second_tech_lead_id": "uuid"
}
```

**After:**
```json
{
  "id": "uuid",
  "name": "Batch A",
  "first_tech_lead_id": "uuid",
  "second_tech_lead_id": "uuid",
  "first_tech_lead": {
    "id": "uuid",
    "name": "John Doe",
    "email": "john@example.com"
  },
  "second_tech_lead": {
    "id": "uuid",
    "name": "Jane Smith",
    "email": "jane@example.com"
  },
  "tech_leads_display": "John Doe/Jane Smith"
}
```

#### Notification Responses
**Before:**
```json
{
  "id": "uuid",
  "user_id": "uuid",
  "title": "Title",
  "message": "Message",
  "is_read": false,
  "created_at": "2024-01-01T00:00:00Z"
}
```

**After:**
```json
{
  "id": "uuid",
  "user_id": "uuid",
  "sender_id": "uuid",
  "sender_name": "Admin User",
  "is_sender": false,
  "title": "Title",
  "message": "Message",
  "is_read": false,
  "created_at": "2024-01-01T00:00:00Z",
  "edited_at": null
}
```

---

## 🧪 Testing After Deployment

### Manual Tests

1. **Login Test**
   - Login as admin
   - Verify dashboard loads

2. **Batch Display Test**
   - Navigate to batches page
   - Verify tech leads show as "TL1/TL2" format
   - NOT showing "Unassigned" for assigned batches

3. **Intern Creation Test**
   - Create new intern
   - Assign to batch
   - Verify saves successfully

4. **Notification Test**
   - Create notification
   - Verify sender name shows
   - Check edited_at field exists

5. **Attendance Test**
   - Mark attendance as LATE
   - Verify saves successfully

### API Tests

```bash
# Set your Railway URL
export API_URL="https://your-app.railway.app"

# Health check
curl $API_URL/api/health

# Login and get token
TOKEN=$(curl -X POST $API_URL/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"yourpassword"}' \
  | jq -r '.access_token')

# Test batch endpoint
curl -H "Authorization: Bearer $TOKEN" $API_URL/api/batches | jq

# Test notifications endpoint
curl -H "Authorization: Bearer $TOKEN" $API_URL/api/notifications | jq

# Test attendance with LATE status
curl -X POST $API_URL/api/attendance \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"user_id":"uuid","day":"2024-01-01","status":"LATE"}' | jq
```

---

## 🔧 Troubleshooting

### Issue: Build Fails on Railway

**Check:**
1. Review Railway build logs
2. Ensure all dependencies in requirements.txt
3. Check for syntax errors

**Solution:**
```bash
# Test locally first
python -m py_compile app/**/*.py
```

### Issue: Migration Fails

**Check Railway logs:**
```bash
railway logs
```

**Common causes:**
- Database connection issue
- Missing permissions
- Column already exists (safe to ignore)

**Solution:**
- Migration is idempotent (safe to re-run)
- Check DATABASE_URL environment variable
- Verify database is accessible

### Issue: "Unassigned" Still Showing

**Check:**
1. Clear browser cache
2. Verify API response includes `tech_leads_display`
3. Check frontend is using correct field

**Debug:**
```bash
# Check API response
curl https://your-app.railway.app/api/batches/{batch_id} | jq '.tech_leads_display'
```

### Issue: LATE Status Not Working

**Check:**
- Migration ran successfully
- Enum includes LATE value

**Solution:**
```bash
# Re-run migration
railway run python scripts/backend_stabilization_migration.py
```

---

## 📋 Railway Environment Variables

Ensure these are set in Railway:

**Required:**
- `DATABASE_URL` - PostgreSQL connection string
- `JWT_SECRET` - JWT signing secret (not "change-me")
- `ADMIN_PASSWORD` - Admin password (not "admin123")

**Optional:**
- `FRONTEND_URL` - Frontend URL for CORS
- `CORS_ORIGINS` - Additional CORS origins
- `ENVIRONMENT` - "production"

**To check:**
1. Go to Railway dashboard
2. Select your service
3. Go to "Variables" tab
4. Verify all required variables are set

---

## 🔄 Rollback Plan

If issues occur after deployment:

### Option 1: Revert Git Commit
```bash
git revert HEAD
git push origin main
```
Railway will auto-deploy the previous version.

### Option 2: Rollback in Railway Dashboard
1. Go to Railway dashboard
2. Select your service
3. Go to "Deployments" tab
4. Click on previous successful deployment
5. Click "Redeploy"

### Option 3: Database Rollback (Only if needed)
If migration caused issues:
1. Access Railway database
2. Run rollback SQL (if needed)
3. Re-deploy previous code version

**Note:** Migration is designed to be safe and non-destructive.

---

## ✅ Success Criteria

Deployment is successful when:

- ✅ Railway build completes without errors
- ✅ Application starts successfully
- ✅ Health endpoint returns 200
- ✅ Batch endpoints return `tech_leads_display`
- ✅ Notification endpoints return `sender_name`
- ✅ Attendance LATE status works
- ✅ No errors in Railway logs
- ✅ Frontend displays tech leads correctly

---

## 📞 Support

### Check Railway Logs
```bash
# Using Railway CLI
railway logs

# Or in Railway Dashboard
# Go to your service → Deployments → View Logs
```

### Common Log Locations
- Build logs: Railway dashboard → Deployments → Build
- Runtime logs: Railway dashboard → Deployments → Deploy
- Database logs: Railway dashboard → Database → Logs

### Debug Commands
```bash
# Check if service is running
railway status

# View environment variables
railway variables

# Connect to database
railway connect
```

---

## 🎯 Post-Deployment Checklist

- [ ] Code pushed to repository
- [ ] Railway build completed successfully
- [ ] Migration script executed
- [ ] Health endpoint responding
- [ ] Batch tech leads displaying correctly
- [ ] Notifications showing sender names
- [ ] Attendance LATE status working
- [ ] No errors in logs
- [ ] Frontend tested and working
- [ ] Team notified of deployment

---

## 📈 Monitoring

After deployment, monitor:

1. **Railway Metrics**
   - CPU usage
   - Memory usage
   - Response times
   - Error rates

2. **Application Logs**
   - Check for errors
   - Verify successful requests
   - Monitor database queries

3. **User Feedback**
   - Test critical workflows
   - Verify bug fixes
   - Check for new issues

---

## 🎉 Summary

**What Changed:**
- ✅ Fixed batch "Unassigned" display bug
- ✅ Enhanced notification system with sender tracking
- ✅ Added centralized error handling
- ✅ Improved database integrity
- ✅ Added performance indexes

**No Breaking Changes:**
- All changes are backward compatible
- Existing API contracts maintained
- New fields are additions, not replacements

**Ready to Deploy:**
- All code changes complete
- Migration script ready
- Documentation complete
- Testing plan ready

**Deploy with confidence! 🚀**
