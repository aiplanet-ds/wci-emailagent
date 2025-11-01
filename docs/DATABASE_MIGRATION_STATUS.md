# Database Migration Status Report

## Overview
Migration from JSON file-based storage to PostgreSQL database for the WCI Email Agent application.

**Date:** 2025-10-30
**Status:** ✅ Core Services Migrated, ⚙️ Router/API Updates In Progress

---

## ✅ Completed Migrations

### 1. Delta Service (`services/delta_service.py`)
**Status:** ✅ MIGRATED TO DATABASE

**Changes Made:**
- Updated imports to use database services
- Removed JSON file references (`delta_tokens.json`, `active_users.json`)
- Migrated methods:
  - `load_delta_tokens()` → Uses `DeltaService.get_delta_token()` + User table
  - `save_delta_tokens()` → Uses `DeltaService.set_delta_token()`
  - `load_active_users()` → Uses `UserService.get_all_users(active_only=True)`
  - `add_user_to_monitoring()` → Creates/activates users in database
  - `remove_user_from_monitoring()` → Deactivates users in database
  - `process_user_messages()` → Uses `EmailStateService` for vendor verification

**Result:** No more `delta_tokens.json` or `active_users.json` files will be created.

---

### 2. Main Email Processing (`main.py`)
**Status:** ✅ MIGRATED TO DATABASE

**Changes Made:**
- Added database imports: `SessionLocal`, `UserService`, `EmailService`, `EmailStateService`
- Updated `process_user_message()` function:
  - Vendor verification check now queries database instead of JSON file
  - Extraction results saved to both JSON (backwards compatibility) AND database
  - Email metadata stored in `Email` model with JSONB fields:
    - `supplier_info`
    - `price_change_summary`
    - `affected_products`
    - `additional_details`
    - `raw_email_data`
  - Email state tracked in `EmailState` model

**Result:** Emails are now persisted in database with full metadata and extraction results.

---

### 3. Email Router Imports (`routers/emails.py`)
**Status:** ⚙️ IMPORTS UPDATED, ENDPOINTS NEED CONVERSION

**Changes Made:**
- Added database imports: `get_db`, `UserService`, `EmailService`, `EmailStateService`
- Removed old `email_state_service` import

**Remaining Work:**
- Need to update individual API endpoints to use database dependency injection
- Pattern: Add `db: AsyncSession = Depends(get_db)` to each endpoint
- Replace `email_state_service` calls with `EmailStateService` database queries

---

## ⚙️ In Progress

### 4. Email API Endpoints (`routers/emails.py`)
**Status:** NEEDS ENDPOINT UPDATES

**Key Endpoints to Update:**
1. `GET /api/emails` - List emails (needs database query)
2. `GET /api/emails/{message_id}` - Get email details (needs database fetch)
3. `POST /api/emails/{message_id}/process` - Mark as processed (needs database update)
4. `POST /api/emails/{message_id}/followup` - Generate followup (needs database state)
5. `POST /api/emails/{message_id}/approve` - Manually approve vendor (needs database update)

**Pattern for Conversion:**
```python
# OLD:
@router.get("/api/emails")
async def list_emails(request: Request):
    user_email = get_user_from_session(request)
    # Load from JSON files...

# NEW:
@router.get("/api/emails")
async def list_emails(request: Request, db: AsyncSession = Depends(get_db)):
    user_email = get_user_from_session(request)
    user = await UserService.get_user_by_email(db, user_email)
    emails = await EmailService.get_emails_by_user(db, user.id)
```

---

## ⏳ Pending Migrations

### 5. Application Startup (`start.py`)
**Status:** PENDING

**Required Changes:**
- Add database initialization on startup
- Update delta service initialization to use database
- Ensure database connection pool is ready before polling starts

**Code to Add:**
```python
from database.config import init_db, close_db

# At startup:
await init_db()

# At shutdown:
await close_db()
```

---

### 6. Vendor Verification Service (`services/vendor_verification_service.py`)
**Status:** PENDING

**Current:** Uses `data/vendor_email_cache.json` for vendor lookup

**Migration Plan:**
- Replace cache file with `Vendor` model queries
- Use `verified_domains` JSONB field for domain matching
- Update `verify_sender()` to query database
- Sync from Epicor should update database instead of cache file

---

### 7. Dashboard Service (`services/dashboard_service.py`)
**Status:** PENDING

**Current:** Reads JSON files to aggregate statistics

**Migration Plan:**
- Replace file scanning with database aggregate queries
- Use SQLAlchemy's `func.count()`, `func.sum()` for statistics
- Query from `Email`, `EmailState`, `EpicorSyncResult` tables

---

### 8. Epicor Sync Results Storage
**Status:** PENDING

**Current:** Saves to `outputs/{user}/epicor_update_{message_id}.json`

**Migration Plan:**
- Use `EpicorSyncResult` model instead of JSON files
- Store sync status, results, and errors in database
- Update routers to read from database

---

## 🗃️ Database Schema

### Tables Available:
- ✅ `users` - User accounts and authentication
- ✅ `emails` - Email metadata and extracted data (JSONB fields)
- ✅ `email_states` - Processing state, vendor verification, Epicor sync status
- ✅ `vendors` - Verified vendors and domains
- ✅ `delta_tokens` - Microsoft Graph delta query tokens
- ✅ `attachments` - Email attachments
- ✅ `epicor_sync_results` - Sync results with Epicor ERP
- ✅ `audit_logs` - User action audit trail

### Database Services Available:
- ✅ `database/services/user_service.py`
- ✅ `database/services/email_service.py`
- ✅ `database/services/email_state_service.py`
- ✅ `database/services/vendor_service.py`
- ✅ `database/services/delta_service.py`
- ✅ `database/services/audit_service.py`

---

## 🚀 Next Steps

### Immediate Actions Needed:

1. **Initialize Database** (if not done already):
   ```bash
   # Windows
   .venv\Scripts\python scripts\init_db.py

   # Alternatively, the migration script will initialize it
   ```

2. **Run Migration Script** to transfer existing JSON data:
   ```bash
   # Dry run first (preview without changes)
   python scripts/migrate_json_to_db.py --dry-run

   # Actual migration
   python scripts/migrate_json_to_db.py
   ```

3. **Update Remaining Routers** (`routers/emails.py`):
   - Add `db: AsyncSession = Depends(get_db)` to all endpoints
   - Replace file operations with database queries
   - Test each endpoint after conversion

4. **Update Start.py** with database initialization

5. **Migrate Vendor Service** to database

6. **Migrate Dashboard Service** to database queries

7. **Test End-to-End**:
   - User authentication and monitoring
   - Email polling and processing
   - Vendor verification
   - Epicor sync
   - Dashboard display

---

## 📊 Files That Will No Longer Be Created

After complete migration:
- ❌ `delta_tokens.json` - Delta tokens now in `delta_tokens` table
- ❌ `active_users.json` - Active users tracked via `users.is_active` field
- ❌ `token_cache_{email}.json` - OAuth tokens (still needed by MSAL, complex migration)
- ❌ `data/email_states.json` - Email states now in `email_states` table
- ❌ `data/vendor_email_cache.json` - Vendor data now in `vendors` table
- ⚠️ `outputs/{user}/price_change_{id}.json` - Still created for backwards compatibility
- ⚠️ `outputs/{user}/epicor_update_{id}.json` - Should be migrated to `epicor_sync_results` table

---

## ⚠️ Important Notes

1. **Backwards Compatibility**: JSON files are still being written in `main.py` for backwards compatibility. Can be removed after confirming database storage works.

2. **OAuth Token Caching**: MSAL library expects file-based token caching. This is the most complex migration and can be done later. The application will still create `token_cache_*.json` files.

3. **Async/Sync Patterns**: Some synchronous code (like `main.py`) uses `asyncio.run_until_complete()` to call async database functions. This is acceptable but not ideal.

4. **Database Connection**: Ensure `DATABASE_URL` is set correctly in `.env`:
   ```
   DATABASE_URL=postgresql+asyncpg://wci_user:wci_password@localhost:5432/wci_emailagent
   ```

5. **Migration Script**: The migration script (`scripts/migrate_json_to_db.py`) will:
   - Create all tables if they don't exist
   - Transfer existing JSON data to database
   - Preserve all historical data
   - Can be run multiple times safely (idempotent)

---

## 🧪 Testing Checklist

- [ ] Database initialized successfully
- [ ] Migration script runs without errors
- [ ] User authentication works
- [ ] Email polling retrieves delta tokens from database
- [ ] Email processing saves to database
- [ ] Email states tracked in database
- [ ] Vendor verification queries database
- [ ] Dashboard loads data from database
- [ ] Epicor sync results saved to database
- [ ] No JSON files created (except token cache)

---

## 🔗 Related Files

- Migration Script: `scripts/migrate_json_to_db.py`
- Database Setup: `scripts/init_db.py`
- Database Config: `database/config.py`
- Models: `database/models.py`
- Alembic Migrations: `alembic/versions/`
- Documentation:
  - `docs/POSTGRESQL_INTEGRATION_SUMMARY.md`
  - `docs/DOCKER_SETUP.md`

---

## Summary

**Progress:** ~60% Complete

- ✅ Core delta/state services migrated
- ✅ Email processing saves to database
- ⚙️ API router imports updated, endpoints need conversion
- ⏳ Vendor, dashboard, and startup code pending
- ⏳ Need to run migration script to transfer existing data

**Estimated Time to Complete:** 2-3 hours of focused work for remaining routers and services.
