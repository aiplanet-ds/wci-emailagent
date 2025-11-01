"""
Quick check test - Run this for a fast validation of database integration

This test provides a quick smoke test to verify the database is working.
Run this first before running the full test suite.

Usage:
    pytest test/database_integration/test_quick_check.py -v
"""
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from database.config import engine, DATABASE_URL


class TestQuickCheck:
    """Quick smoke tests for database integration"""

    @pytest.mark.asyncio
    async def test_database_connection(self):
        """Quick test: Can we connect to the database?"""
        try:
            async with engine.connect() as conn:
                result = await conn.execute(text("SELECT 1"))
                assert result.scalar() == 1
            print("\n✅ PASS: Database connection working")
        except Exception as e:
            pytest.fail(f"❌ FAIL: Database connection failed: {e}")

    @pytest.mark.asyncio
    async def test_database_credentials(self):
        """Quick test: Are we using the correct database and user?"""
        async with engine.connect() as conn:
            # Check database name
            result = await conn.execute(text("SELECT current_database()"))
            db_name = result.scalar()
            assert db_name == "wci_emailagent", f"Wrong database: {db_name}"
            
            # Check user
            result = await conn.execute(text("SELECT current_user"))
            user = result.scalar()
            assert user == "wci_user", f"Wrong user: {user}"
            
            print(f"\n✅ PASS: Connected to {db_name} as {user}")

    @pytest.mark.asyncio
    async def test_required_extensions(self):
        """Quick test: Are required extensions installed?"""
        required = ['pg_trgm', 'uuid-ossp', 'btree_gin']
        
        async with engine.connect() as conn:
            result = await conn.execute(
                text("SELECT extname FROM pg_extension WHERE extname = ANY(:exts)"),
                {"exts": required}
            )
            installed = [row[0] for row in result.fetchall()]
            
            missing = set(required) - set(installed)
            assert len(missing) == 0, f"Missing extensions: {missing}"
            
            print(f"\n✅ PASS: All required extensions installed: {', '.join(installed)}")

    @pytest.mark.asyncio
    async def test_tables_exist(self):
        """Quick test: Are all required tables created?"""
        required_tables = [
            'users', 'emails', 'email_states', 'vendors',
            'attachments', 'epicor_sync_results', 'delta_tokens', 'audit_logs'
        ]
        
        async with engine.connect() as conn:
            result = await conn.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_type = 'BASE TABLE'
            """))
            tables = [row[0] for row in result.fetchall()]
            
            missing = set(required_tables) - set(tables)
            assert len(missing) == 0, f"Missing tables: {missing}"
            
            print(f"\n✅ PASS: All {len(required_tables)} tables exist")

    @pytest.mark.asyncio
    async def test_can_insert_and_query(self):
        """Quick test: Can we insert and query data?"""
        async with engine.begin() as conn:
            # Try to insert a test user
            await conn.execute(text("""
                INSERT INTO users (email, display_name, is_active)
                VALUES ('test@quickcheck.com', 'Quick Check Test', true)
                ON CONFLICT (email) DO NOTHING
            """))
            
            # Try to query it back
            result = await conn.execute(text("""
                SELECT email, display_name 
                FROM users 
                WHERE email = 'test@quickcheck.com'
            """))
            row = result.fetchone()
            
            assert row is not None, "Could not retrieve inserted data"
            assert row[0] == 'test@quickcheck.com'
            
            # Clean up
            await conn.execute(text("""
                DELETE FROM users WHERE email = 'test@quickcheck.com'
            """))
            
            print("\n✅ PASS: Can insert and query data")

    @pytest.mark.asyncio
    async def test_full_text_search_working(self):
        """Quick test: Is full-text search working?"""
        async with engine.connect() as conn:
            # Test trigram similarity function
            result = await conn.execute(text("""
                SELECT similarity('test', 'testing')
            """))
            similarity = result.scalar()
            
            assert similarity is not None, "Trigram similarity not working"
            assert 0 <= similarity <= 1, f"Invalid similarity value: {similarity}"
            
            print(f"\n✅ PASS: Full-text search working (similarity: {similarity:.2f})")

    @pytest.mark.asyncio
    async def test_docker_postgres_accessible(self):
        """Quick test: Is Docker PostgreSQL accessible from host?"""
        assert "postgresql+asyncpg://" in DATABASE_URL, "Wrong database driver"
        assert "localhost" in DATABASE_URL or "127.0.0.1" in DATABASE_URL, \
            "Database should be accessible from localhost"
        
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT version()"))
            version = result.scalar()
            assert "PostgreSQL" in version
            
            print(f"\n✅ PASS: Docker PostgreSQL accessible from host")
            print(f"   Version: {version.split(',')[0]}")


def print_summary():
    """Print test summary"""
    print("\n" + "=" * 80)
    print("  QUICK CHECK SUMMARY")
    print("=" * 80)
    print("\nIf all tests passed, your Docker PostgreSQL integration is working!")
    print("\nNext steps:")
    print("  1. Run full test suite: python test/database_integration/run_tests.py")
    print("  2. Start your application: python start.py")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    # Run tests with pytest
    import sys
    exit_code = pytest.main([__file__, "-v", "-s"])
    
    if exit_code == 0:
        print_summary()
    
    sys.exit(exit_code)

