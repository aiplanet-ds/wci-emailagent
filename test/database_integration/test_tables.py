"""
Test database tables and schema
"""
import pytest
from sqlalchemy import text, inspect
from sqlalchemy.ext.asyncio import AsyncSession

from database.config import engine
from database.models import Base


class TestDatabaseTables:
    """Test suite for database tables"""

    @pytest.mark.asyncio
    async def test_all_tables_created(self):
        """Test that all required tables are created"""
        expected_tables = [
            'users',
            'emails',
            'email_states',
            'vendors',
            'attachments',
            'epicor_sync_results',
            'delta_tokens',
            'audit_logs'
        ]
        
        async with engine.connect() as conn:
            def get_tables(connection):
                inspector = inspect(connection)
                return inspector.get_table_names()
            
            tables = await conn.run_sync(get_tables)
            
            missing_tables = set(expected_tables) - set(tables)
            assert len(missing_tables) == 0, f"Missing tables: {missing_tables}"
            print(f"✅ All {len(expected_tables)} tables created: {', '.join(sorted(tables))}")

    @pytest.mark.asyncio
    async def test_users_table_structure(self):
        """Test users table structure"""
        async with engine.connect() as conn:
            def get_columns(connection):
                inspector = inspect(connection)
                return [col['name'] for col in inspector.get_columns('users')]
            
            columns = await conn.run_sync(get_columns)
            
            required_columns = ['id', 'email', 'display_name', 'is_active', 'created_at', 'updated_at']
            for col in required_columns:
                assert col in columns, f"Missing column '{col}' in users table"
            print(f"✅ Users table structure valid ({len(columns)} columns)")

    @pytest.mark.asyncio
    async def test_emails_table_structure(self):
        """Test emails table structure"""
        async with engine.connect() as conn:
            def get_columns(connection):
                inspector = inspect(connection)
                return [col['name'] for col in inspector.get_columns('emails')]
            
            columns = await conn.run_sync(get_columns)
            
            required_columns = ['id', 'message_id', 'user_id', 'subject', 'sender', 'body_text', 'received_datetime']
            for col in required_columns:
                assert col in columns, f"Missing column '{col}' in emails table"
            print(f"✅ Emails table structure valid ({len(columns)} columns)")

    @pytest.mark.asyncio
    async def test_email_states_table_structure(self):
        """Test email_states table structure"""
        async with engine.connect() as conn:
            def get_columns(connection):
                inspector = inspect(connection)
                return [col['name'] for col in inspector.get_columns('email_states')]
            
            columns = await conn.run_sync(get_columns)
            
            required_columns = ['id', 'message_id', 'user_id', 'is_price_change', 'llm_confidence', 'status']
            for col in required_columns:
                assert col in columns, f"Missing column '{col}' in email_states table"
            print(f"✅ Email states table structure valid ({len(columns)} columns)")

    @pytest.mark.asyncio
    async def test_vendors_table_structure(self):
        """Test vendors table structure"""
        async with engine.connect() as conn:
            def get_columns(connection):
                inspector = inspect(connection)
                return [col['name'] for col in inspector.get_columns('vendors')]
            
            columns = await conn.run_sync(get_columns)
            
            required_columns = ['id', 'vendor_id', 'vendor_name', 'email_address', 'is_active']
            for col in required_columns:
                assert col in columns, f"Missing column '{col}' in vendors table"
            print(f"✅ Vendors table structure valid ({len(columns)} columns)")

    @pytest.mark.asyncio
    async def test_primary_keys(self):
        """Test that all tables have primary keys"""
        tables = ['users', 'emails', 'email_states', 'vendors', 'attachments', 
                  'epicor_sync_results', 'delta_tokens', 'audit_logs']
        
        async with engine.connect() as conn:
            def get_pk(connection, table_name):
                inspector = inspect(connection)
                pk = inspector.get_pk_constraint(table_name)
                return pk['constrained_columns']
            
            for table in tables:
                pk_columns = await conn.run_sync(lambda conn: get_pk(conn, table))
                assert len(pk_columns) > 0, f"Table '{table}' has no primary key"
            
            print(f"✅ All {len(tables)} tables have primary keys")

    @pytest.mark.asyncio
    async def test_foreign_keys(self):
        """Test foreign key relationships"""
        async with engine.connect() as conn:
            def get_fks(connection, table_name):
                inspector = inspect(connection)
                return inspector.get_foreign_keys(table_name)
            
            # Test emails -> users foreign key
            emails_fks = await conn.run_sync(lambda conn: get_fks(conn, 'emails'))
            assert any(fk['referred_table'] == 'users' for fk in emails_fks), \
                "emails table should have foreign key to users"
            
            # Test email_states -> users foreign key
            states_fks = await conn.run_sync(lambda conn: get_fks(conn, 'email_states'))
            assert any(fk['referred_table'] == 'users' for fk in states_fks), \
                "email_states table should have foreign key to users"
            
            print("✅ Foreign key relationships configured correctly")

    @pytest.mark.asyncio
    async def test_indexes(self):
        """Test that required indexes are created"""
        async with engine.connect() as conn:
            def get_indexes(connection, table_name):
                inspector = inspect(connection)
                return inspector.get_indexes(table_name)
            
            # Test emails table indexes
            emails_indexes = await conn.run_sync(lambda conn: get_indexes(conn, 'emails'))
            index_names = [idx['name'] for idx in emails_indexes]
            
            # Check for full-text search indexes
            assert any('fts' in name.lower() or 'gin' in str(idx) for name in index_names for idx in emails_indexes), \
                "emails table should have full-text search indexes"
            
            print(f"✅ Indexes created (found {len(index_names)} indexes on emails table)")

    @pytest.mark.asyncio
    async def test_gin_indexes_for_fulltext_search(self):
        """Test that GIN indexes are created for full-text search"""
        async with engine.connect() as conn:
            result = await conn.execute(text("""
                SELECT indexname, indexdef 
                FROM pg_indexes 
                WHERE tablename = 'emails' 
                AND indexdef LIKE '%gin%'
            """))
            gin_indexes = result.fetchall()
            
            assert len(gin_indexes) >= 2, "Should have at least 2 GIN indexes on emails table"
            
            # Check for subject and body_text indexes
            index_defs = [idx[1] for idx in gin_indexes]
            has_subject_index = any('subject' in idx_def for idx_def in index_defs)
            has_body_index = any('body_text' in idx_def for idx_def in index_defs)
            
            assert has_subject_index, "Should have GIN index on subject column"
            assert has_body_index, "Should have GIN index on body_text column"
            
            print(f"✅ GIN indexes for full-text search configured correctly ({len(gin_indexes)} indexes)")

    @pytest.mark.asyncio
    async def test_table_row_counts(self):
        """Test that tables are accessible and can be queried"""
        tables = ['users', 'emails', 'email_states', 'vendors', 'attachments', 
                  'epicor_sync_results', 'delta_tokens', 'audit_logs']
        
        async with engine.connect() as conn:
            for table in tables:
                result = await conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
                count = result.scalar()
                assert count >= 0, f"Could not query table '{table}'"
            
            print(f"✅ All {len(tables)} tables are queryable")

