"""
Initialize database script - Creates all tables

This script initializes the database by creating all tables
defined in the SQLAlchemy models.

Usage:
    python scripts/init_db.py
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.config import init_db, engine
from database.models import Base


async def main():
    """Initialize database tables"""
    print("=" * 60)
    print("Database Initialization")
    print("=" * 60)

    try:
        print("\nCreating database tables...")
        await init_db()
        print("✓ Database tables created successfully")

        # List all tables
        from sqlalchemy import inspect
        async with engine.connect() as conn:
            def get_tables(connection):
                inspector = inspect(connection)
                return inspector.get_table_names()

            tables = await conn.run_sync(get_tables)

        print(f"\n✓ Created {len(tables)} tables:")
        for table in sorted(tables):
            print(f"  - {table}")

        print("\n" + "=" * 60)
        print("Database initialization complete!")
        print("=" * 60)

    except Exception as e:
        print(f"\n✗ Error initializing database: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
