"""
Initialize database script - Creates all tables

This script initializes the database by creating all tables
defined in the SQLAlchemy models.

Usage:
    python scripts/init_db.py
"""

import asyncio
import sys
import logging
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from database.config import init_db, engine
from database.models import Base


async def main():
    """Initialize database tables"""
    logger.info("=" * 60)
    logger.info("Database Initialization")
    logger.info("=" * 60)

    try:
        logger.info("Creating database tables...")
        await init_db()
        logger.info("Database tables created successfully")

        # List all tables
        from sqlalchemy import inspect
        async with engine.connect() as conn:
            def get_tables(connection):
                inspector = inspect(connection)
                return inspector.get_table_names()

            tables = await conn.run_sync(get_tables)

        logger.info(f"Created {len(tables)} tables:")
        for table in sorted(tables):
            logger.info(f"  - {table}")

        logger.info("=" * 60)
        logger.info("Database initialization complete!")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
