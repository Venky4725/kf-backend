# Backend Stabilization - Deployment Checklist

## Pre-Deployment

### 1. Code Review
- [ ] All changes reviewed and approved
- [ ] No merge conflicts
- [ ] All files compile without errors
- [ ] No TODO or FIXME comments in critical code

### 2. Local Testing
- [ ] Run `python scripts/quick_health_check.py` - All checks pass
- [ ] Run `python scripts/test_backend_stability.py` - All tests pass
- [ ] Manual testing of critical features completed
- [ ] No errors in console/logs

### 3. Database Backup
- [ ] Database backup created
- [ ] Backup verified and accessible
- [ ] Backup location documented
- [ ] Rollback procedure tested

**Command:**
```bash
pg_dump -U postgres knowledge_factory > backup_$(date +%Y%m%d_%H%M%S).sql
```

### 4. Environment Check
- [ ] Environment variables verified
- [ ] Database connection string correct
- [ ] CORS origins configured
- [ ] JWT secret set (not default)
- [ ] Admin password changed (not default)

### 5. Dependencies
- [ ] All dependencies installed
- [ ] Requirements.txt up to date
- [ ] No conflicting package versions
- [ ] Virtual environment activated

---

## Deployment

### 1. Stop Application (if applicable)
- [ ] Application stopped gracefully
- [ ] Active connections closed
- [ ] Background jobs stopped

**Commands:**
```bash
# Systemd
sudo systemctl stop knowledge-factory

# Docker
docker-compose down

# Heroku (no stop needed)
```

### 2. Deploy Code
- [ ] Code pushed to repository
- [ ] Deployment triggered
- [ ] Build completed successfully
- [ ] No build errors

**Commands:**
```bash
# Git
git add .
git commit -m "Backend stabilization - fixes batch display, notifications, error handling"
git push origin main

# Heroku
git push heroku main

# Docker
docker-compose build
docker-compose up -d
```

### 3. Run Database Migration
- [ ] Migration script executed
- [ ] All migration steps completed
- [ ] No migration errors
- [ ] Migration log reviewed

**Command:**
```bash
python scripts/backend_stabilization_migration.py
```

**Expected Output:**
```
[STEP 1] Adding missing columns...
✅ Added notifications.edited_at column

[STEP 2] Ensuring enum values...
✅ All attendance status enum values exist

[STEP 3] Verifying foreign keys...
✅ All foreign keys verified

[STEP 4] Adding performance indexes...
✅ Created indexes

[STEP 5] Verifying unique constraints...
✅ All constraints verified

[STEP 6] Validating data integrity...
✅ No orphaned records found

✅ MIGRATION COMPLETED SUCCESSFULLY
```

### 4. Start Application
- [ ] Application started
- [ ] No startup errors
- [ ] Health endpoint responding
- [ ] Logs show successful startup

**Commands:**
```bash
# Systemd
sudo systemctl start knowledge-factory
sudo systemctl status knowledge-factory

# Docker
docker-compose up -d
docker-compose logs -f

# Heroku (automatic)
heroku logs --tail
```

---

## Post-Deployment Verification

### 1. Health Check
- [ ] Run `python scripts/quick_health_check.py`
- [ ] All checks pass
- [ ] No warnings or errors

**Command:**
```bash
python scripts/quick_health_check.py
```

**Expected Output:**
```
✅ Database connection: OK
✅ All tables exist
✅ All critical columns exist
✅ Attendance status enum: OK
✅ All foreign keys verified
✅ Performance indexes exist
✅ Data integrity: OK

Result: 7/7 checks passed
✅ ALL CHECKS PASSED - Backend is healthy!
```

### 2. API Endpoints
- [ ] GET /api/health returns 200
- [ ] GET /api/batches returns enriched data
- [ ] GET /api/notifications returns sender info
- [ ] POST /api/attendance with LATE status works
- [ ] Error responses are consistent

**Commands:**
```bash
# Health check
curl https://your-api.com/api/health

# Batch with tech leads
curl https://your-api.com/api/batches/{batch_id}
# Verify: tech_leads_display field present

# Notifications
curl -H "Authorization: Bearer $TOKEN" https://your-api.com/api/notifications
# Verify: sender_name field present

# Attendance with LATE
curl -X POST https://your-api.com/api/attendance \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"user_id": "uuid", "day": "2024-01-01", "status": "LATE"}'
# Verify: 201 Created
```

### 3. Critical Features
- [ ] User login works
- [ ] Intern creation works
- [ ] Batch assignment works
- [ ] Tech lead display correct
- [ ] Notification creation works
- [ ] Attendance marking works
- [ ] Dashboard loads

### 4. Error Handling
- [ ] Invalid requests return proper errors
- [ ] Error messages are user-friendly
- [ ] No stack traces exposed to users
- [ ] Errors logged correctly

**Test:**
```bash
# Invalid data
curl -X POST https://your-api.com/api/profiles \
  -H "Content-Type: application/json" \
  -d '{"invalid": "data"}'

# Expected: 422 with clear error message
```

### 5. Performance
- [ ] Response times acceptable
- [ ] No slow queries
- [ ] Database connections stable
- [ ] Memory usage normal

### 6. Logs
- [ ] No error messages in logs
- [ ] No warnings (except expected)
- [ ] Startup messages correct
- [ ] Request logging working

**Commands:**
```bash
# Check logs
tail -f /var/log/knowledge-factory/app.log

# Or Docker
docker-compose logs -f

# Or Heroku
heroku logs --tail
```

---

## Smoke Tests

### Test 1: Admin Login
- [ ] Navigate to login page
- [ ] Login as admin
- [ ] Dashboard loads
- [ ] No console errors

### Test 2: Create Batch with Tech Leads
- [ ] Navigate to batches
- [ ] Create new batch
- [ ] Assign two tech leads
- [ ] Save batch
- [ ] Verify tech leads display as "TL1/TL2"

### Test 3: Create Intern
- [ ] Navigate to profiles
- [ ] Create new intern
- [ ] Assign to batch
- [ ] Save intern
- [ ] Verify batch assignment

### Test 4: Send Notification
- [ ] Navigate to notifications
- [ ] Create notification
- [ ] Send to user
- [ ] Verify sender name shows

### Test 5: Mark Attendance
- [ ] Navigate to attendance
- [ ] Select date
- [ ] Mark intern as LATE
- [ ] Save attendance
- [ ] Verify LATE status saved

---

## Rollback Procedure (If Needed)

### 1. Identify Issue
- [ ] Issue documented
- [ ] Severity assessed
- [ ] Decision to rollback made

### 2. Rollback Code
```bash
# Git
git revert HEAD
git push origin main

# Heroku
git push heroku main

# Docker
git checkout previous-commit
docker-compose build
docker-compose up -d
```

### 3. Rollback Database (Only if migration caused issues)
```bash
# Restore from backup
psql knowledge_factory < backup_YYYYMMDD_HHMMSS.sql
```

### 4. Verify Rollback
- [ ] Application running
- [ ] Health check passes
- [ ] Critical features work
- [ ] No errors in logs

### 5. Document
- [ ] Issue documented
- [ ] Rollback reason documented
- [ ] Next steps planned

---

## Post-Deployment Tasks

### Immediate (Within 1 hour)
- [ ] Monitor error logs
- [ ] Check performance metrics
- [ ] Verify user reports
- [ ] Update status page

### Short-term (Within 24 hours)
- [ ] Review all logs
- [ ] Check database performance
- [ ] Gather user feedback
- [ ] Document any issues

### Long-term (Within 1 week)
- [ ] Performance analysis
- [ ] User satisfaction survey
- [ ] Identify improvements
- [ ] Plan next iteration

---

## Communication

### Before Deployment
- [ ] Notify team of deployment window
- [ ] Inform users of potential downtime
- [ ] Prepare status updates

### During Deployment
- [ ] Update status page
- [ ] Communicate progress
- [ ] Report any issues

### After Deployment
- [ ] Announce completion
- [ ] Share what was fixed
- [ ] Provide feedback channel
- [ ] Thank team

---

## Sign-off

### Technical Lead
- [ ] Code reviewed and approved
- [ ] Tests passed
- [ ] Documentation complete
- [ ] Ready for deployment

**Name:** ________________  
**Date:** ________________  
**Signature:** ________________

### DevOps/SRE
- [ ] Infrastructure ready
- [ ] Backup completed
- [ ] Monitoring configured
- [ ] Rollback plan ready

**Name:** ________________  
**Date:** ________________  
**Signature:** ________________

### Product Owner
- [ ] Features verified
- [ ] User impact assessed
- [ ] Communication plan ready
- [ ] Approved for deployment

**Name:** ________________  
**Date:** ________________  
**Signature:** ________________

---

## Deployment Log

**Deployment Date:** ________________  
**Deployment Time:** ________________  
**Deployed By:** ________________  
**Environment:** ________________  

**Pre-Deployment Checks:**
- Health Check: ☐ Pass ☐ Fail
- Tests: ☐ Pass ☐ Fail
- Backup: ☐ Complete ☐ Incomplete

**Deployment Steps:**
- Code Deploy: ☐ Success ☐ Failed
- Migration: ☐ Success ☐ Failed
- Application Start: ☐ Success ☐ Failed

**Post-Deployment Verification:**
- Health Check: ☐ Pass ☐ Fail
- API Tests: ☐ Pass ☐ Fail
- Smoke Tests: ☐ Pass ☐ Fail

**Issues Encountered:**
_____________________________________________
_____________________________________________
_____________________________________________

**Resolution:**
_____________________________________________
_____________________________________________
_____________________________________________

**Final Status:** ☐ Success ☐ Partial ☐ Failed ☐ Rolled Back

**Notes:**
_____________________________________________
_____________________________________________
_____________________________________________

---

## Success Criteria

Deployment is considered successful when:
- ✅ All pre-deployment checks pass
- ✅ Code deployed without errors
- ✅ Migration completed successfully
- ✅ Application started successfully
- ✅ All post-deployment checks pass
- ✅ All smoke tests pass
- ✅ No critical errors in logs
- ✅ Performance metrics normal
- ✅ User feedback positive

**If all criteria met: Deployment SUCCESSFUL ✅**

---

## Emergency Contacts

**Technical Lead:** ________________  
**DevOps/SRE:** ________________  
**Database Admin:** ________________  
**Product Owner:** ________________  

**Escalation Path:**
1. Technical Lead
2. DevOps/SRE
3. Engineering Manager
4. CTO

---

## Additional Resources

- **Audit Report:** `BACKEND_AUDIT_REPORT.txt`
- **Quick Start:** `QUICK_START_GUIDE.md`
- **Changes Summary:** `CHANGES_SUMMARY.md`
- **Scripts Documentation:** `scripts/README.md`

---

**Remember:** If in doubt, don't deploy. Better to delay than to cause issues.

**Good luck! 🚀**
