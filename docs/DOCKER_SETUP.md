# Docker Setup Guide

This guide covers setting up and running the WCI Email Agent with PostgreSQL using Docker.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [Database Setup](#database-setup)
- [Running the Application](#running-the-application)
- [Data Migration](#data-migration)
- [Development Workflow](#development-workflow)
- [Troubleshooting](#troubleshooting)
- [Useful Commands](#useful-commands)

## Prerequisites

- Docker Desktop (or Docker Engine + Docker Compose)
  - Windows/Mac: [Docker Desktop](https://www.docker.com/products/docker-desktop)
  - Linux: Docker Engine + Docker Compose plugin
- Git (for cloning the repository)
- At least 4GB of free disk space

## Quick Start

1. **Clone the repository** (if not already done):
   ```bash
   git clone <your-repo-url>
   cd wci-emailagent
   ```

2. **Configure environment variables**:
   ```bash
   # Copy the template
   cp .env.template .env

   # Edit .env with your actual credentials
   # Required: Azure AD, Azure OpenAI, Epicor credentials
   ```

3. **Start the services**:
   ```bash
   docker-compose up -d
   ```

4. **Check if services are running**:
   ```bash
   docker-compose ps
   ```

5. **Access the application**:
   - Application: http://localhost:8000
   - PostgreSQL: localhost:5432

## Configuration

### Environment Variables

Edit the `.env` file with your configuration:

```bash
# PostgreSQL Database
DATABASE_URL=postgresql+asyncpg://wci_user:wci_password@postgres:5432/wci_emailagent
DB_HOST=postgres
DB_PORT=5432
DB_NAME=wci_emailagent
DB_USER=wci_user
DB_PASSWORD=your-secure-password-here  # ⚠️ Change this!
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=10
DB_ECHO=false

# Azure AD (Multi-tenant OAuth)
AZURE_CLIENT_ID=your-client-id
AZURE_TENANT_ID=common
AZURE_CLIENT_SECRET=your-client-secret
AZURE_REDIRECT_URI=http://localhost:8000/auth/callback

# Azure OpenAI
AZURE_OPENAI_API_KEY=your-api-key
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4.1
AZURE_OPENAI_API_VERSION=2024-12-01-preview

# Epicor ERP
EPICOR_BASE_URL=https://your-epicor-server.com/EpicorData/api/v1
EPICOR_CLIENT_ID=your-client-id
EPICOR_CLIENT_SECRET=your-client-secret
EPICOR_USERNAME=your-username
EPICOR_PASSWORD=your-password
EPICOR_COMPANY=your-company-id

# Application Settings
SESSION_SECRET_KEY=your-session-secret  # Generate with: openssl rand -hex 32
LLM_CONFIDENCE_THRESHOLD=0.75
VENDOR_CACHE_TTL_HOURS=24
VENDOR_DOMAIN_MATCH_ENABLED=true
```

### Security Notes

⚠️ **IMPORTANT**: Change default passwords in production!

- `DB_PASSWORD`: Use a strong, unique password
- `SESSION_SECRET_KEY`: Generate with `openssl rand -hex 32`
- Never commit `.env` to version control

## Database Setup

### Initial Setup

The database will be automatically initialized when you start the services for the first time.

```bash
# Start services
docker-compose up -d

# Wait for database to be healthy (about 30 seconds)
docker-compose logs -f postgres

# Look for: "database system is ready to accept connections"
```

### Running Migrations

After the database is initialized, create the schema using Alembic:

```bash
# Create initial migration
docker-compose exec app alembic revision --autogenerate -m "Initial schema"

# Apply migrations
docker-compose exec app alembic upgrade head

# Verify current version
docker-compose exec app alembic current
```

### Database Management

```bash
# Connect to PostgreSQL
docker-compose exec postgres psql -U wci_user -d wci_emailagent

# Create a database backup
docker-compose exec postgres pg_dump -U wci_user wci_emailagent > backup.sql

# Restore from backup
cat backup.sql | docker-compose exec -T postgres psql -U wci_user -d wci_emailagent

# View database size
docker-compose exec postgres psql -U wci_user -d wci_emailagent -c "\l+"
```

## Running the Application

### Start All Services

```bash
# Start in detached mode
docker-compose up -d

# Start with logs visible
docker-compose up

# Start specific service
docker-compose up -d postgres
docker-compose up -d app
```

### Stop Services

```bash
# Stop all services
docker-compose down

# Stop and remove volumes (⚠️ deletes data!)
docker-compose down -v

# Stop specific service
docker-compose stop app
```

### View Logs

```bash
# View all logs
docker-compose logs

# Follow logs (live tail)
docker-compose logs -f

# View specific service logs
docker-compose logs -f app
docker-compose logs -f postgres

# View last 100 lines
docker-compose logs --tail=100 app
```

### Restart Services

```bash
# Restart all services
docker-compose restart

# Restart specific service
docker-compose restart app
docker-compose restart postgres
```

## Data Migration

If you have existing JSON data, migrate it to the database:

### Step 1: Backup JSON Files

```bash
# Create backup directory
mkdir -p backups/$(date +%Y%m%d)

# Backup JSON files
cp data/email_states.json backups/$(date +%Y%m%d)/
cp data/vendor_email_cache.json backups/$(date +%Y%m%d)/
cp delta_tokens.json backups/$(date +%Y%m%d)/
cp active_users.json backups/$(date +%Y%m%d)/
```

### Step 2: Run Migration (Dry Run First)

```bash
# Preview migration without changes
docker-compose exec app python scripts/migrate_json_to_db.py --dry-run
```

### Step 3: Run Actual Migration

```bash
# Run the migration
docker-compose exec app python scripts/migrate_json_to_db.py

# Check the results
docker-compose exec postgres psql -U wci_user -d wci_emailagent -c "SELECT COUNT(*) FROM users;"
docker-compose exec postgres psql -U wci_user -d wci_emailagent -c "SELECT COUNT(*) FROM email_states;"
docker-compose exec postgres psql -U wci_user -d wci_emailagent -c "SELECT COUNT(*) FROM vendors;"
```

### Step 4: Verify Migration

```bash
# Access the application and verify data is visible
# Browse to http://localhost:8000
```

## Development Workflow

### Hot Reload

The application container is configured with hot reload enabled:

```yaml
# In docker-compose.yml
volumes:
  - .:/app  # Maps your local code to container
command: uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Any changes to Python files will automatically restart the server.

### Installing New Dependencies

```bash
# Add package to requirements.txt
echo "new-package==1.0.0" >> requirements.txt

# Rebuild the application container
docker-compose build app

# Restart the service
docker-compose up -d app
```

### Running Tests

```bash
# Run all tests
docker-compose exec app pytest

# Run with coverage
docker-compose exec app pytest --cov=. --cov-report=html

# Run specific test file
docker-compose exec app pytest tests/test_email_service.py
```

### Accessing Python Shell

```bash
# Python shell with app context
docker-compose exec app python

# IPython shell (if installed)
docker-compose exec app ipython
```

### Database Shell Access

```bash
# PostgreSQL shell
docker-compose exec postgres psql -U wci_user -d wci_emailagent

# Useful psql commands:
# \dt              - List tables
# \d+ table_name   - Describe table
# \l               - List databases
# \du              - List users
# \q               - Quit
```

## Troubleshooting

### Services Won't Start

```bash
# Check service status
docker-compose ps

# View logs for errors
docker-compose logs

# Check if ports are already in use
# Windows
netstat -ano | findstr :8000
netstat -ano | findstr :5432

# Linux/Mac
lsof -i :8000
lsof -i :5432

# Restart Docker Desktop (Windows/Mac)
# or restart Docker daemon (Linux)
```

### Database Connection Issues

```bash
# Check if PostgreSQL is healthy
docker-compose exec postgres pg_isready -U wci_user

# Test connection from app container
docker-compose exec app python -c "
from database.config import engine
import asyncio
async def test():
    async with engine.connect() as conn:
        print('✓ Database connection successful')
asyncio.run(test())
"

# Check database logs
docker-compose logs postgres
```

### Application Errors

```bash
# View application logs
docker-compose logs -f app

# Restart application
docker-compose restart app

# Rebuild application (if code issues)
docker-compose up -d --build app

# Enter container for debugging
docker-compose exec app bash
```

### Disk Space Issues

```bash
# Check Docker disk usage
docker system df

# Clean up unused resources
docker system prune -a

# Remove old containers and images
docker container prune
docker image prune -a

# Remove unused volumes (⚠️ careful!)
docker volume prune
```

### Permission Issues (Linux)

```bash
# Fix file permissions
sudo chown -R $USER:$USER .

# Fix directory permissions
chmod -R 755 data/ outputs/ logs/
```

## Useful Commands

### Docker Compose Quick Reference

```bash
# Start services
docker-compose up -d

# Stop services
docker-compose down

# View logs
docker-compose logs -f

# Rebuild services
docker-compose build

# Restart services
docker-compose restart

# Execute command in container
docker-compose exec app <command>

# View running containers
docker-compose ps

# Pull latest images
docker-compose pull
```

### Database Quick Reference

```bash
# Backup database
docker-compose exec postgres pg_dump -U wci_user wci_emailagent > backup.sql

# Restore database
cat backup.sql | docker-compose exec -T postgres psql -U wci_user -d wci_emailagent

# Reset database (⚠️ deletes all data!)
docker-compose down -v
docker-compose up -d postgres
docker-compose exec app alembic upgrade head

# Query tables
docker-compose exec postgres psql -U wci_user -d wci_emailagent -c "
  SELECT table_name, pg_size_pretty(pg_total_relation_size(quote_ident(table_name))) AS size
  FROM information_schema.tables
  WHERE table_schema = 'public'
  ORDER BY pg_total_relation_size(quote_ident(table_name)) DESC;
"
```

### Health Checks

```bash
# Check application health
curl http://localhost:8000/health

# Check database health
docker-compose exec postgres pg_isready -U wci_user

# Check container health status
docker-compose ps
```

## Production Considerations

### Security

1. **Change default passwords** in `.env`
2. **Use secrets management** (AWS Secrets Manager, Azure Key Vault, etc.)
3. **Enable SSL/TLS** for PostgreSQL connections
4. **Restrict network access** using firewall rules
5. **Regular security updates** for base images

### Performance

1. **Adjust resource limits** in `docker-compose.yml`:
   ```yaml
   deploy:
     resources:
       limits:
         cpus: '2'
         memory: 2G
   ```

2. **Tune PostgreSQL** settings in `docker-compose.yml`:
   ```yaml
   command:
     - "postgres"
     - "-c"
     - "max_connections=200"
     - "-c"
     - "shared_buffers=256MB"
   ```

3. **Monitor performance**:
   ```bash
   docker stats
   ```

### Backup Strategy

1. **Automated backups**:
   ```bash
   # Add to crontab
   0 2 * * * docker-compose exec -T postgres pg_dump -U wci_user wci_emailagent | gzip > /backups/db_$(date +\%Y\%m\%d).sql.gz
   ```

2. **Volume backups**:
   ```bash
   docker run --rm -v wci-emailagent_pgdata:/data -v $(pwd)/backups:/backup ubuntu tar czf /backup/pgdata_backup.tar.gz -C /data .
   ```

3. **Test restore procedures** regularly

## Support

For issues or questions:
1. Check logs: `docker-compose logs -f`
2. Review this documentation
3. Check application logs in `logs/` directory
4. Contact your system administrator

---

**Last Updated**: 2025-01-30
