# PostgreSQL Integration - Implementation Summary

## Overview

Your WCI Email Agent application has been successfully upgraded with PostgreSQL database support, replacing the previous JSON file-based storage system. This provides better scalability, reliability, and data integrity.

## What Was Implemented

### 1. Docker Infrastructure ✅

**Files Created:**
- [`docker-compose.yml`](docker-compose.yml) - Multi-container setup with PostgreSQL and app
- [`Dockerfile`](Dockerfile) - Application container configuration
- [`.dockerignore`](.dockerignore) - Docker build exclusions

**Features:**
- PostgreSQL 16 container with persistent volumes
- Health checks for both services
- Resource limits (CPU and memory)
- Shared network for service communication
- Hot reload support for development
- Automatic dependency management

**Usage:**
```bash
# Start all services
docker-compose up -d

# Stop all services
docker-compose down

# View logs
docker-compose logs -f
```

---

### 2. Database Layer ✅

**Files Created:**
- [`database/__init__.py`](database/__init__.py) - Package initialization
- [`database/config.py`](database/config.py) - Database connection and session management
- [`database/models.py`](database/models.py) - SQLAlchemy models (8 tables)

**Database Schema:**

1. **users** - User accounts and authentication
   - Fields: email, display_name, preferences, last_login, token expiry
   - Relationships: emails, email_states, delta_tokens, audit_logs

2. **emails** - Email content and extracted data
   - Fields: message_id, subject, sender, body, received_at
   - JSON fields: supplier_info, price_change_summary, affected_products
   - Relationships: attachments, email_state, epicor_sync_results

3. **email_states** - Processing and verification status
   - Fields: processed, is_price_change, llm_confidence, verification_status
   - Tracks: vendor verification, Epicor sync, follow-up needs
   - Relationships: email, user, vendor

4. **vendors** - Supplier information from Epicor
   - Fields: vendor_id, vendor_name, contact_email, verified_domains
   - Supports: exact email matching and domain matching

5. **attachments** - Email attachment metadata
   - Fields: filename, content_type, file_size, storage_path

6. **epicor_sync_results** - Epicor integration tracking
   - Fields: sync_status, total_products, success/failed counts

7. **delta_tokens** - Microsoft Graph delta query tokens
   - One per user for efficient email polling

8. **audit_logs** - User action tracking
   - Fields: action_type, action_details, ip_address, user_agent

---

### 3. Database Migration System ✅

**Files Created:**
- [`alembic.ini`](alembic.ini) - Alembic configuration
- [`alembic/env.py`](alembic/env.py) - Migration environment with async support
- [`alembic/script.py.mako`](alembic/script.py.mako) - Migration template
- [`alembic/README`](alembic/README) - Migration commands reference

**Usage:**
```bash
# Create migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

---

### 4. Service Layer ✅

**Files Created:**
- [`database/services/__init__.py`](database/services/__init__.py)
- [`database/services/user_service.py`](database/services/user_service.py)
- [`database/services/email_service.py`](database/services/email_service.py)
- [`database/services/email_state_service.py`](database/services/email_state_service.py)
- [`database/services/vendor_service.py`](database/services/vendor_service.py)
- [`database/services/delta_service.py`](database/services/delta_service.py)
- [`database/services/audit_service.py`](database/services/audit_service.py)

**Features:**
- Clean abstraction over database operations
- Async/await support for all operations
- CRUD operations for all models
- Business logic encapsulation
- Query optimization with joinedload

**Example Usage:**
```python
from database.config import SessionLocal
from database.services.email_state_service import EmailStateService

async with SessionLocal() as db:
    state = await EmailStateService.create_state(
        db=db,
        message_id="msg123",
        user_id=1,
        is_price_change=True
    )
    await db.commit()
```

---

### 5. Data Migration Tools ✅

**Files Created:**
- [`scripts/migrate_json_to_db.py`](scripts/migrate_json_to_db.py) - JSON to PostgreSQL migration
- [`scripts/init_db.py`](scripts/init_db.py) - Database initialization
- [`scripts/setup.bat`](scripts/setup.bat) - Windows setup script
- [`scripts/setup.sh`](scripts/setup.sh) - Linux/Mac setup script

**Migration Features:**
- Migrates users from `active_users.json`
- Migrates email states from `data/email_states.json`
- Migrates vendors from `data/vendor_email_cache.json`
- Migrates delta tokens from `delta_tokens.json`
- Migrates processed emails from `outputs/` directory
- Dry-run mode for preview
- Comprehensive error handling and reporting

**Usage:**
```bash
# Preview migration
python scripts/migrate_json_to_db.py --dry-run

# Run migration
python scripts/migrate_json_to_db.py
```

---

### 6. Documentation ✅

**Files Created:**
- [`DOCKER_SETUP.md`](DOCKER_SETUP.md) - Comprehensive Docker guide (300+ lines)
- [`QUICKSTART.md`](QUICKSTART.md) - Quick start guide with examples
- [`POSTGRESQL_INTEGRATION_SUMMARY.md`](POSTGRESQL_INTEGRATION_SUMMARY.md) - This file

**Documentation Covers:**
- Docker setup and configuration
- Database initialization
- Migration procedures
- Development workflow
- Troubleshooting guide
- Production considerations
- Security best practices

---

### 7. Configuration Updates ✅

**Files Updated:**
- [`requirements.txt`](requirements.txt) - Added database dependencies
- [`.env.template`](.env.template) - Added PostgreSQL configuration
- [`.env`](.env) - Added database connection settings

**New Dependencies:**
```
sqlalchemy[asyncio]>=2.0.0
asyncpg>=0.29.0
psycopg2-binary>=2.9.9
alembic>=1.13.0
greenlet>=3.0.0
```

**New Environment Variables:**
```bash
DATABASE_URL=postgresql+asyncpg://wci_user:wci_password@localhost:5432/wci_emailagent
DB_HOST=localhost
DB_PORT=5432
DB_NAME=wci_emailagent
DB_USER=wci_user
DB_PASSWORD=wci_password
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=10
DB_ECHO=false
```

---

## Project Structure

```
wci-emailagent/
├── database/                    # NEW: Database layer
│   ├── __init__.py
│   ├── config.py               # Connection & session management
│   ├── models.py               # SQLAlchemy models (8 tables)
│   └── services/               # Service layer
│       ├── __init__.py
│       ├── user_service.py
│       ├── email_service.py
│       ├── email_state_service.py
│       ├── vendor_service.py
│       ├── delta_service.py
│       └── audit_service.py
├── alembic/                     # NEW: Database migrations
│   ├── env.py
│   ├── script.py.mako
│   ├── README
│   └── versions/
├── scripts/                     # NEW: Setup & migration scripts
│   ├── migrate_json_to_db.py
│   ├── init_db.py
│   ├── setup.bat
│   └── setup.sh
├── docker-compose.yml           # NEW: Docker services
├── Dockerfile                   # NEW: App container
├── .dockerignore                # NEW: Docker exclusions
├── alembic.ini                  # NEW: Migration config
├── DOCKER_SETUP.md              # NEW: Docker guide
├── QUICKSTART.md                # NEW: Quick start guide
├── POSTGRESQL_INTEGRATION_SUMMARY.md  # NEW: This file
├── requirements.txt             # UPDATED: Added DB deps
├── .env.template                # UPDATED: Added DB config
└── .env                         # UPDATED: Added DB config
```

---

## Getting Started

### Option 1: Quick Setup (Automated)

**Windows:**
```bash
scripts\setup.bat
```

**Linux/Mac:**
```bash
chmod +x scripts/setup.sh
./scripts/setup.sh
```

### Option 2: Manual Setup

```bash
# 1. Start PostgreSQL
docker-compose up -d postgres

# 2. Wait for database (30 seconds)
docker-compose logs -f postgres

# 3. Install dependencies
pip install -r requirements.txt

# 4. Initialize database
python scripts/init_db.py

# 5. Migrate data (optional)
python scripts/migrate_json_to_db.py

# 6. Start application
python start.py
```

---

## Next Steps: Integration Required

The following parts of your existing application need to be updated to use the database:

### 1. Update Email State Service

**File:** `services/email_state_service.py`

**Action:** Replace with database-backed implementation

**Before:**
```python
# JSON file operations
with open("data/email_states.json", "r") as f:
    states = json.load(f)
```

**After:**
```python
from database.config import SessionLocal
from database.services.email_state_service import EmailStateService

async with SessionLocal() as db:
    state = await EmailStateService.get_state_by_message_id(db, message_id)
    await db.commit()
```

---

### 2. Update Vendor Verification Service

**File:** `services/vendor_verification_service.py`

**Action:** Use database vendor service

**Before:**
```python
# JSON cache operations
with open("data/vendor_email_cache.json", "r") as f:
    cache = json.load(f)
```

**After:**
```python
from database.services.vendor_service import VendorService

async with SessionLocal() as db:
    result = await VendorService.verify_email_against_vendors(db, email)
    if result:
        vendor, match_type = result
```

---

### 3. Update Delta Service

**File:** `services/delta_service.py`

**Action:** Use database delta token storage

**Before:**
```python
# JSON file operations
with open("delta_tokens.json", "r") as f:
    tokens = json.load(f)
```

**After:**
```python
from database.services.delta_service import DeltaService

async with SessionLocal() as db:
    token = await DeltaService.get_delta_token(db, user_id)
    await DeltaService.set_delta_token(db, user_id, new_token)
    await db.commit()
```

---

### 4. Update Main Email Processing

**File:** `main.py`

**Action:** Save emails to database when processed

**Add:**
```python
from database.services.email_service import EmailService
from database.services.email_state_service import EmailStateService

async def process_email(email_data):
    async with SessionLocal() as db:
        # Create user if needed
        user, _ = await UserService.get_or_create_user(
            db=db,
            email=email_data["user_email"]
        )

        # Create email record
        email = await EmailService.create_email(
            db=db,
            message_id=email_data["message_id"],
            user_id=user.id,
            subject=email_data["subject"],
            sender_email=email_data["sender"],
            # ... other fields
        )

        # Create email state
        state = await EmailStateService.create_state(
            db=db,
            message_id=email_data["message_id"],
            user_id=user.id,
            is_price_change=True,
            llm_confidence=0.95
        )

        await db.commit()
```

---

### 5. Update FastAPI Routes

**File:** `start.py`

**Action:** Add database dependency injection

**Add:**
```python
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from database.config import get_db, init_db, close_db

# Add startup/shutdown events
@app.on_event("startup")
async def startup():
    await init_db()

@app.on_event("shutdown")
async def shutdown():
    await close_db()

# Update routes to use database
@app.get("/emails")
async def get_emails(
    db: AsyncSession = Depends(get_db),
    request: Request = None
):
    user_email = request.session.get("user_email")
    user = await UserService.get_user_by_email(db, user_email)
    emails = await EmailService.get_emails_by_user(db, user.id)
    return {"emails": emails}
```

---

## Testing Your Integration

### 1. Test Database Connection

```bash
python -c "
import asyncio
from database.config import engine

async def test():
    async with engine.connect() as conn:
        print('✓ Database connection successful')

asyncio.run(test())
"
```

### 2. Test Service Layer

```bash
python -c "
import asyncio
from database.config import SessionLocal
from database.services.user_service import UserService

async def test():
    async with SessionLocal() as db:
        user, created = await UserService.get_or_create_user(
            db=db,
            email='test@example.com',
            display_name='Test User'
        )
        await db.commit()
        print(f'✓ User service working: {user.email}')

asyncio.run(test())
"
```

### 3. Test Migration

```bash
# Dry run to preview
python scripts/migrate_json_to_db.py --dry-run

# Check counts
docker-compose exec postgres psql -U wci_user -d wci_emailagent -c "
  SELECT COUNT(*) FROM users;
  SELECT COUNT(*) FROM email_states;
  SELECT COUNT(*) FROM vendors;
"
```

---

## Benefits of PostgreSQL Integration

### Scalability
- ✅ Handles millions of records efficiently
- ✅ Built-in indexing for fast queries
- ✅ Connection pooling for concurrent access
- ✅ Query optimization

### Reliability
- ✅ ACID transactions for data integrity
- ✅ Foreign key constraints
- ✅ Automatic crash recovery
- ✅ Point-in-time recovery

### Features
- ✅ Full-text search capabilities
- ✅ JSON/JSONB support for flexible data
- ✅ Advanced querying with joins
- ✅ Aggregate functions and analytics

### Maintenance
- ✅ Automated backups
- ✅ Database migrations with Alembic
- ✅ Performance monitoring
- ✅ Easy scaling

---

## Performance Considerations

### Connection Pooling
- Pool size: 20 connections
- Max overflow: 10 connections
- Pre-ping enabled for health checks
- Connection recycling every hour

### Indexing
- Primary keys on all tables
- Indexes on foreign keys
- Indexes on frequently queried fields
- Full-text search indexes (optional)

### Query Optimization
- Use `joinedload` for relationships
- Limit results with pagination
- Use select_related for eager loading
- Monitor slow queries with `DB_ECHO=true`

---

## Security Best Practices

1. **Change Default Passwords**
   ```bash
   # Generate secure password
   openssl rand -base64 32

   # Update .env
   DB_PASSWORD=your-secure-password
   ```

2. **Use Environment Variables**
   - Never commit `.env` to git
   - Use secrets management in production
   - Rotate credentials regularly

3. **Network Security**
   - Restrict PostgreSQL to internal network
   - Use SSL/TLS in production
   - Configure firewall rules

4. **Access Control**
   - Use role-based access control
   - Limit user permissions
   - Audit database access

---

## Backup Strategy

### Automated Backups

```bash
# Daily backup script
docker-compose exec postgres pg_dump -U wci_user wci_emailagent | gzip > backups/db_$(date +%Y%m%d).sql.gz

# Retention: Keep last 30 days
find backups/ -name "db_*.sql.gz" -mtime +30 -delete
```

### Volume Backups

```bash
# Backup Docker volume
docker run --rm -v wci-emailagent_pgdata:/data -v $(pwd)/backups:/backup ubuntu tar czf /backup/pgdata_backup.tar.gz -C /data .

# Restore Docker volume
docker run --rm -v wci-emailagent_pgdata:/data -v $(pwd)/backups:/backup ubuntu tar xzf /backup/pgdata_backup.tar.gz -C /data
```

---

## Monitoring

### Database Performance

```bash
# View active connections
docker-compose exec postgres psql -U wci_user -d wci_emailagent -c "
  SELECT * FROM pg_stat_activity;
"

# View table sizes
docker-compose exec postgres psql -U wci_user -d wci_emailagent -c "
  SELECT schemaname, tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
  FROM pg_tables WHERE schemaname = 'public'
  ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
"

# View slow queries (requires pg_stat_statements extension)
docker-compose exec postgres psql -U wci_user -d wci_emailagent -c "
  SELECT query, mean_exec_time, calls
  FROM pg_stat_statements
  ORDER BY mean_exec_time DESC
  LIMIT 10;
"
```

### Application Monitoring

```bash
# View container stats
docker stats

# View application logs
docker-compose logs -f app

# View database logs
docker-compose logs -f postgres
```

---

## Support & Resources

### Documentation
- [DOCKER_SETUP.md](DOCKER_SETUP.md) - Complete Docker guide
- [QUICKSTART.md](QUICKSTART.md) - Quick start guide
- [alembic/README](alembic/README) - Migration commands

### Useful Commands
```bash
# Database management
docker-compose exec postgres psql -U wci_user -d wci_emailagent

# View logs
docker-compose logs -f

# Restart services
docker-compose restart

# Rebuild containers
docker-compose up -d --build
```

### Troubleshooting
1. Check logs: `docker-compose logs -f`
2. Verify connection: `python scripts/init_db.py`
3. Test migration: `python scripts/migrate_json_to_db.py --dry-run`
4. Review [DOCKER_SETUP.md](DOCKER_SETUP.md) troubleshooting section

---

## Summary

You now have a complete PostgreSQL integration for your WCI Email Agent application with:

✅ Docker containerization for easy deployment
✅ Robust database schema with 8 tables
✅ Service layer for clean data access
✅ Migration tools for existing data
✅ Comprehensive documentation
✅ Development and production support

**Next Action:** Follow the integration steps above to update your application code to use the database services.

---

**Implementation Date:** 2025-01-30
**PostgreSQL Version:** 16-alpine
**SQLAlchemy Version:** 2.0+
**Docker Compose Version:** 3.8
