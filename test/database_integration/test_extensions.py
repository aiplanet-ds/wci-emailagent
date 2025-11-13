"""
Test PostgreSQL extensions required for the application
"""
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from database.config import engine


class TestDatabaseExtensions:
    """Test suite for PostgreSQL extensions"""

    @pytest.mark.asyncio
    async def test_pg_trgm_extension(self):
        """Test that pg_trgm extension is installed"""
        async with engine.connect() as conn:
            result = await conn.execute(
                text("SELECT extname, extversion FROM pg_extension WHERE extname = 'pg_trgm'")
            )
            row = result.fetchone()
            assert row is not None, "pg_trgm extension is not installed"
            assert row[0] == "pg_trgm"
            print(f"✅ pg_trgm extension installed (version {row[1]})")

    @pytest.mark.asyncio
    async def test_uuid_ossp_extension(self):
        """Test that uuid-ossp extension is installed"""
        async with engine.connect() as conn:
            result = await conn.execute(
                text("SELECT extname, extversion FROM pg_extension WHERE extname = 'uuid-ossp'")
            )
            row = result.fetchone()
            assert row is not None, "uuid-ossp extension is not installed"
            assert row[0] == "uuid-ossp"
            print(f"✅ uuid-ossp extension installed (version {row[1]})")

    @pytest.mark.asyncio
    async def test_btree_gin_extension(self):
        """Test that btree_gin extension is installed"""
        async with engine.connect() as conn:
            result = await conn.execute(
                text("SELECT extname, extversion FROM pg_extension WHERE extname = 'btree_gin'")
            )
            row = result.fetchone()
            assert row is not None, "btree_gin extension is not installed"
            assert row[0] == "btree_gin"
            print(f"✅ btree_gin extension installed (version {row[1]})")

    @pytest.mark.asyncio
    async def test_all_required_extensions(self):
        """Test that all required extensions are installed"""
        required_extensions = ['pg_trgm', 'uuid-ossp', 'btree_gin']
        
        async with engine.connect() as conn:
            result = await conn.execute(
                text("SELECT extname FROM pg_extension WHERE extname = ANY(:extensions)"),
                {"extensions": required_extensions}
            )
            installed = [row[0] for row in result.fetchall()]
            
            missing = set(required_extensions) - set(installed)
            assert len(missing) == 0, f"Missing extensions: {missing}"
            print(f"✅ All required extensions installed: {', '.join(installed)}")

    @pytest.mark.asyncio
    async def test_trigram_similarity(self):
        """Test pg_trgm trigram similarity function"""
        async with engine.connect() as conn:
            result = await conn.execute(
                text("SELECT similarity('test', 'test123')")
            )
            similarity = result.scalar()
            assert similarity is not None
            assert 0 <= similarity <= 1
            print(f"✅ Trigram similarity function working (similarity: {similarity:.2f})")

    @pytest.mark.asyncio
    async def test_uuid_generation(self):
        """Test UUID generation function"""
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT uuid_generate_v4()"))
            uuid = result.scalar()
            assert uuid is not None
            assert len(str(uuid)) == 36  # UUID format: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
            print(f"✅ UUID generation working (sample: {uuid})")

