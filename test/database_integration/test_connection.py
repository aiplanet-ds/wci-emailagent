"""
Test PostgreSQL database connection and basic setup
"""
import pytest
import asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from database.config import engine, DATABASE_URL


class TestDatabaseConnection:
    """Test suite for database connection"""

    @pytest.mark.asyncio
    async def test_database_url_configured(self):
        """Test that DATABASE_URL is properly configured"""
        assert DATABASE_URL is not None, "DATABASE_URL is not configured"
        assert "postgresql+asyncpg://" in DATABASE_URL, "DATABASE_URL should use asyncpg driver"
        assert "wci_emailagent" in DATABASE_URL, "DATABASE_URL should point to wci_emailagent database"
        print(f"✅ Database URL configured: {DATABASE_URL.split('@')[0]}@***")

    @pytest.mark.asyncio
    async def test_database_connection(self):
        """Test basic database connection"""
        try:
            async with engine.connect() as conn:
                result = await conn.execute(text("SELECT 1"))
                assert result.scalar() == 1
            print("✅ Database connection successful")
        except Exception as e:
            pytest.fail(f"❌ Database connection failed: {e}")

    @pytest.mark.asyncio
    async def test_database_version(self):
        """Test PostgreSQL version"""
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT version()"))
            version = result.scalar()
            assert "PostgreSQL" in version
            print(f"✅ PostgreSQL version: {version.split(',')[0]}")

    @pytest.mark.asyncio
    async def test_database_name(self):
        """Test that we're connected to the correct database"""
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT current_database()"))
            db_name = result.scalar()
            assert db_name == "wci_emailagent"
            print(f"✅ Connected to database: {db_name}")

    @pytest.mark.asyncio
    async def test_database_user(self):
        """Test database user"""
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT current_user"))
            user = result.scalar()
            assert user == "wci_user"
            print(f"✅ Connected as user: {user}")

    @pytest.mark.asyncio
    async def test_connection_pool(self):
        """Test connection pooling"""
        # Test multiple concurrent connections
        async def test_query():
            async with engine.connect() as conn:
                result = await conn.execute(text("SELECT 1"))
                return result.scalar()

        results = await asyncio.gather(*[test_query() for _ in range(5)])
        assert all(r == 1 for r in results)
        print("✅ Connection pool working correctly")

    @pytest.mark.asyncio
    async def test_transaction_support(self):
        """Test transaction support"""
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        print("✅ Transaction support working")

    @pytest.mark.asyncio
    async def test_docker_postgres_running(self):
        """Test that Docker PostgreSQL is running and accessible"""
        try:
            async with engine.connect() as conn:
                # Check if we can access the database
                result = await conn.execute(text("SELECT 1"))
                assert result.scalar() == 1
                
                # Check uptime (should be recent if just started)
                result = await conn.execute(text("SELECT pg_postmaster_start_time()"))
                start_time = result.scalar()
                assert start_time is not None
                print(f"✅ Docker PostgreSQL running since: {start_time}")
        except Exception as e:
            pytest.fail(f"❌ Docker PostgreSQL not accessible: {e}")

