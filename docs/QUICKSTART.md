# Quick Start Guide - PostgreSQL Integration

## Overview

Your WCI Email Agent application has been upgraded with PostgreSQL database support. This guide will help you get started quickly.

## What's New?

- **PostgreSQL Database**: Replaces JSON file storage for scalability and reliability
- **Docker Support**: Easy deployment with docker-compose
- **Database Models**: Structured tables for users, emails, vendors, and more
- **Migration Tools**: Scripts to migrate existing JSON data to PostgreSQL
- **Service Layer**: Clean database abstraction with async support

## Prerequisites

- Docker Desktop installed
- Your existing `.env` file with Azure/Epicor credentials

## Step-by-Step Setup

### 1. Install Python Dependencies (Local Development)

```bash
pip install -r requirements.txt
```

### 2. Initialize Database with Docker

```bash
# Start PostgreSQL container
docker-compose up -d postgres

# Wait for database to be ready (30 seconds)
docker-compose logs -f postgres
# Look for: "database system is ready to accept connections"

# Press Ctrl+C to exit logs
```

### 3. Create Database Schema

```bash
# Option A: Use the init script (simple)
python scripts/init_db.py

# Option B: Use Alembic migrations (recommended for production)
alembic revision --autogenerate -m "Initial schema"
alembic upgrade head
```

### 4. Migrate Existing Data (If You Have JSON Files)

```bash
# Preview migration (dry run)
python scripts/migrate_json_to_db.py --dry-run

# Run actual migration
python scripts/migrate_json_to_db.py
```

### 5. Start the Application

**Option A: Run Locally (with Docker PostgreSQL)**
```bash
# PostgreSQL runs in Docker, app runs locally
python start.py
```

**Option B: Run Everything in Docker**
```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f app
```

### 6. Verify Setup

```bash
# Check database tables
docker-compose exec postgres psql -U wci_user -d wci_emailagent -c "\dt"

# Check record counts
docker-compose exec postgres psql -U wci_user -d wci_emailagent -c "
  SELECT
    (SELECT COUNT(*) FROM users) as users,
    (SELECT COUNT(*) FROM email_states) as email_states,
    (SELECT COUNT(*) FROM vendors) as vendors,
    (SELECT COUNT(*) FROM emails) as emails;
"
```

## Architecture Overview

### Database Tables

1. **users** - User accounts and authentication
2. **emails** - Email content and metadata
3. **email_states** - Processing status and verification
4. **vendors** - Supplier information from Epicor
5. **attachments** - Email attachment metadata
6. **epicor_sync_results** - Sync tracking
7. **delta_tokens** - Microsoft Graph delta tokens
8. **audit_logs** - User action tracking

### File Structure

```
wci-emailagent/
├── database/
│   ├── __init__.py
│   ├── config.py           # Database connection
│   ├── models.py           # SQLAlchemy models
│   └── services/           # Service layer
│       ├── user_service.py
│       ├── email_service.py
│       ├── email_state_service.py
│       ├── vendor_service.py
│       ├── delta_service.py
│       └── audit_service.py
├── alembic/                # Database migrations
│   ├── env.py
│   └── versions/
├── scripts/
│   ├── init_db.py          # Initialize database
│   └── migrate_json_to_db.py  # Migrate JSON data
├── docker-compose.yml      # Docker services
├── Dockerfile              # App container
├── .dockerignore
└── DOCKER_SETUP.md         # Detailed Docker guide
```

## Common Tasks

### Development

```bash
# Run app locally with Docker PostgreSQL
docker-compose up -d postgres
python start.py

# View database logs
docker-compose logs -f postgres

# Connect to database
docker-compose exec postgres psql -U wci_user -d wci_emailagent
```

### Database Management

```bash
# Backup database
docker-compose exec postgres pg_dump -U wci_user wci_emailagent > backup.sql

# Restore database
cat backup.sql | docker-compose exec -T postgres psql -U wci_user -d wci_emailagent

# View table sizes
docker-compose exec postgres psql -U wci_user -d wci_emailagent -c "
  SELECT schemaname, tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
  FROM pg_tables
  WHERE schemaname = 'public'
  ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
"
```

### Migrations

```bash
# Create new migration after model changes
alembic revision --autogenerate -m "Add new column"

# Apply migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# View migration history
alembic history
```

## Troubleshooting

### Connection Refused

```bash
# Check if PostgreSQL is running
docker-compose ps postgres

# Restart PostgreSQL
docker-compose restart postgres

# Check logs
docker-compose logs postgres
```

### Migration Errors

```bash
# Reset database (⚠️ deletes all data!)
docker-compose down -v
docker-compose up -d postgres
python scripts/init_db.py
```

### Import Errors

```bash
# Ensure dependencies are installed
pip install -r requirements.txt

# Check Python path
python -c "import database; print(database.__file__)"
```

## Environment Variables

Key database-related environment variables in `.env`:

```bash
# Database connection (for Docker)
DATABASE_URL=postgresql+asyncpg://wci_user:wci_password@localhost:5432/wci_emailagent

# Or individual components
DB_HOST=localhost          # Use 'postgres' when running in Docker
DB_PORT=5432
DB_NAME=wci_emailagent
DB_USER=wci_user
DB_PASSWORD=wci_password   # ⚠️ Change in production!

# Connection pool settings
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=10
DB_ECHO=false              # Set true for SQL debugging
```

## Using the Service Layer

### Example: Working with Users

```python
from database.config import SessionLocal
from database.services.user_service import UserService

async def example():
    async with SessionLocal() as db:
        # Get or create user
        user, created = await UserService.get_or_create_user(
            db=db,
            email="user@example.com",
            display_name="John Doe"
        )

        if created:
            print(f"Created new user: {user.email}")
        else:
            print(f"User exists: {user.email}")

        await db.commit()
```

### Example: Working with Email States

```python
from database.services.email_state_service import EmailStateService

async def example():
    async with SessionLocal() as db:
        # Create email state
        state = await EmailStateService.create_state(
            db=db,
            message_id="msg123",
            user_id=1,
            is_price_change=True,
            llm_confidence=0.95
        )

        # Mark as processed
        await EmailStateService.mark_as_processed(
            db=db,
            message_id="msg123",
            processed_by_id=1
        )

        await db.commit()
```

### Example: Working with Vendors

```python
from database.services.vendor_service import VendorService

async def example():
    async with SessionLocal() as db:
        # Verify vendor email
        result = await VendorService.verify_email_against_vendors(
            db=db,
            email="supplier@vendor.com"
        )

        if result:
            vendor, match_type = result
            print(f"Verified: {vendor.vendor_name} ({match_type})")
        else:
            print("Not a verified vendor")
```

## Next Steps

1. **Review the full Docker setup**: See [DOCKER_SETUP.md](DOCKER_SETUP.md)
2. **Update your application code**: Integrate the service layer (see below)
3. **Test the migration**: Run with dry-run first
4. **Set up backups**: Configure automated database backups
5. **Monitor performance**: Use `docker stats` and PostgreSQL logs

## Integration Notes

### Services That Need Updates

The following services should be updated to use the database:

1. **services/email_state_service.py** - Replace with `database.services.email_state_service`
2. **services/vendor_verification_service.py** - Use `database.services.vendor_service`
3. **services/delta_service.py** - Use `database.services.delta_service`
4. **main.py** - Update email processing to save to database
5. **start.py** - Add database session management

### FastAPI Integration

Add database dependency to your routes:

```python
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from database.config import get_db

@app.get("/emails")
async def get_emails(db: AsyncSession = Depends(get_db)):
    from database.services.email_service import EmailService
    emails = await EmailService.get_emails_by_user(db, user_id=1)
    return {"emails": [email.message_id for email in emails]}
```

## Support

For detailed documentation, see:
- [DOCKER_SETUP.md](DOCKER_SETUP.md) - Comprehensive Docker guide
- [alembic/README](alembic/README) - Migration commands

For issues:
1. Check logs: `docker-compose logs -f`
2. Verify environment: `docker-compose config`
3. Test connection: `python scripts/init_db.py`

---

**Ready to start?** Run `docker-compose up -d postgres && python scripts/init_db.py`
