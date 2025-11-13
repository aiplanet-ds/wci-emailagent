# Database Integration Tests

Comprehensive test suite to verify Docker PostgreSQL database integration.

## Overview

This test suite validates that:
- ✅ Docker PostgreSQL container is running and healthy
- ✅ Database connection is working correctly
- ✅ Required PostgreSQL extensions are installed (pg_trgm, uuid-ossp, btree_gin)
- ✅ All database tables are created with correct schema
- ✅ Indexes and foreign keys are properly configured
- ✅ Database service layer is functioning correctly
- ✅ Full-text search capabilities are working

## Prerequisites

1. **Docker Desktop** must be installed and running
2. **PostgreSQL container** must be running:
   ```bash
   docker-compose up -d postgres
   ```
3. **Database must be initialized**:
   ```bash
   python scripts/init_db.py
   ```
4. **Python dependencies** must be installed:
   ```bash
   pip install -r requirements.txt
   ```

## Running Tests

### Quick Start

Run all tests with the test runner:
```bash
python test/database_integration/run_tests.py
```

### Verbose Mode

Get detailed output:
```bash
python test/database_integration/run_tests.py --verbose
```

### Run Specific Test Suite

Run only connection tests:
```bash
python test/database_integration/run_tests.py --specific connection
```

Run only table tests:
```bash
python test/database_integration/run_tests.py --specific tables
```

Run only service tests:
```bash
python test/database_integration/run_tests.py --specific services
```

### Using pytest Directly

Run all tests:
```bash
pytest test/database_integration/ -v
```

Run specific test file:
```bash
pytest test/database_integration/test_connection.py -v
```

Run specific test:
```bash
pytest test/database_integration/test_connection.py::TestDatabaseConnection::test_database_connection -v
```

Run with coverage:
```bash
pytest test/database_integration/ --cov=database --cov-report=html
```

## Test Suites

### 1. Connection Tests (`test_connection.py`)

Tests basic database connectivity:
- Database URL configuration
- Connection establishment
- PostgreSQL version check
- Database name verification
- User authentication
- Connection pooling
- Transaction support

**Run:**
```bash
pytest test/database_integration/test_connection.py -v
```

### 2. Extension Tests (`test_extensions.py`)

Tests PostgreSQL extensions:
- `pg_trgm` - Trigram text search
- `uuid-ossp` - UUID generation
- `btree_gin` - GIN indexes
- Extension functionality verification

**Run:**
```bash
pytest test/database_integration/test_extensions.py -v
```

### 3. Table Tests (`test_tables.py`)

Tests database schema:
- All required tables created
- Table structure and columns
- Primary keys
- Foreign key relationships
- Indexes (including GIN indexes for full-text search)
- Table accessibility

**Run:**
```bash
pytest test/database_integration/test_tables.py -v
```

### 4. Service Tests (`test_services.py`)

Tests database service layer:
- **UserService**: User creation, retrieval, updates
- **EmailService**: Email CRUD operations
- **EmailStateService**: Email state management
- **VendorService**: Vendor verification and management
- **DeltaService**: Delta token management
- **AuditService**: Audit logging

**Run:**
```bash
pytest test/database_integration/test_services.py -v
```

### 5. Docker Integration Tests (`test_docker_integration.py`)

Tests Docker-specific functionality:
- Container running and healthy
- Volume persistence
- Network configuration
- Port mapping
- Host accessibility
- Container logs

**Run:**
```bash
pytest test/database_integration/test_docker_integration.py -v
```

## Test Results Interpretation

### ✅ All Tests Pass
Your Docker PostgreSQL integration is working correctly! You can proceed with:
1. Starting your application: `python start.py`
2. Migrating existing data: `python scripts/migrate_json_to_db.py`

### ❌ Connection Tests Fail
**Possible causes:**
- PostgreSQL container not running
- Wrong credentials in `.env` file
- Port conflict (another PostgreSQL instance running)

**Solutions:**
```bash
# Check if container is running
docker-compose ps

# Restart container
docker-compose restart postgres

# Check logs
docker-compose logs postgres

# Verify .env file has correct credentials
cat .env | grep DB_
```

### ❌ Extension Tests Fail
**Possible causes:**
- Extensions not installed during initialization
- Old database volume without extensions

**Solutions:**
```bash
# Recreate database with extensions
docker-compose down -v
docker-compose up -d postgres
python scripts/init_db.py
```

### ❌ Table Tests Fail
**Possible causes:**
- Database not initialized
- Schema migration issues

**Solutions:**
```bash
# Initialize database
python scripts/init_db.py

# Or use Alembic migrations
alembic upgrade head
```

### ❌ Service Tests Fail
**Possible causes:**
- Database schema issues
- Service layer bugs
- Missing dependencies

**Solutions:**
```bash
# Reinstall dependencies
pip install -r requirements.txt

# Check database schema
docker-compose exec postgres psql -U wci_user -d wci_emailagent -c "\dt"
```

### ❌ Docker Tests Fail
**Possible causes:**
- Docker not running
- Container not started
- Network issues

**Solutions:**
```bash
# Start Docker Desktop
# Then start containers
docker-compose up -d postgres

# Check Docker status
docker ps
docker-compose ps
```

## Continuous Integration

To run these tests in CI/CD:

```yaml
# Example GitHub Actions workflow
- name: Start PostgreSQL
  run: docker-compose up -d postgres

- name: Wait for PostgreSQL
  run: sleep 10

- name: Initialize Database
  run: python scripts/init_db.py

- name: Run Database Tests
  run: pytest test/database_integration/ -v --cov=database
```

## Troubleshooting

### Tests hang or timeout
```bash
# Check if PostgreSQL is responsive
docker-compose exec postgres pg_isready -U wci_user

# Restart container
docker-compose restart postgres
```

### Permission errors
```bash
# Check database permissions
docker-compose exec postgres psql -U wci_user -d wci_emailagent -c "\du"
```

### Port conflicts
```bash
# Check what's using port 5432
netstat -ano | findstr :5432  # Windows
lsof -i :5432                  # Linux/Mac

# Use different port in .env
DB_PORT=5433
```

## Writing New Tests

To add new tests:

1. Create a new test file in `test/database_integration/`
2. Follow the naming convention: `test_<feature>.py`
3. Use pytest fixtures from `conftest.py`
4. Mark async tests with `@pytest.mark.asyncio`

Example:
```python
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

class TestMyFeature:
    @pytest.mark.asyncio
    async def test_something(self, db_session: AsyncSession):
        # Your test code here
        assert True
```

## Support

For issues or questions:
1. Check test output for specific error messages
2. Review Docker logs: `docker-compose logs postgres`
3. Verify environment configuration: `.env` file
4. Check database status: `docker-compose ps`

## Summary

These tests ensure your Docker PostgreSQL integration is:
- ✅ Properly configured
- ✅ Running correctly
- ✅ Ready for production use
- ✅ Compatible with your application

Run the tests regularly to catch integration issues early!

