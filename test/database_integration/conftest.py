"""
Pytest fixtures for database integration tests
"""
import pytest
import asyncio
import os
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import database components
from database.config import Base, DATABASE_URL
from database.models import User, Email, EmailState, Vendor, Attachment, EpicorSyncResult, DeltaToken, AuditLog


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Create a new database session for each test"""
    from database.config import SessionLocal

    async with SessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@pytest.fixture
async def sample_user(db_session: AsyncSession) -> User:
    """Create a sample user for testing"""
    user = User(
        email="test@example.com",
        display_name="Test User",
        is_active=True
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def sample_vendor(db_session: AsyncSession) -> Vendor:
    """Create a sample vendor for testing"""
    vendor = Vendor(
        vendor_id="TEST001",
        vendor_name="Test Vendor Inc.",
        email_address="vendor@test.com",
        is_active=True
    )
    db_session.add(vendor)
    await db_session.commit()
    await db_session.refresh(vendor)
    return vendor


@pytest.fixture
async def sample_email(db_session: AsyncSession, sample_user: User) -> Email:
    """Create a sample email for testing"""
    email = Email(
        message_id="test-message-123",
        user_id=sample_user.id,
        subject="Test Email Subject",
        sender="sender@example.com",
        body_text="This is a test email body",
        received_datetime="2025-10-30T10:00:00Z"
    )
    db_session.add(email)
    await db_session.commit()
    await db_session.refresh(email)
    return email


@pytest.fixture
async def sample_email_state(db_session: AsyncSession, sample_user: User) -> EmailState:
    """Create a sample email state for testing"""
    state = EmailState(
        message_id="test-state-123",
        user_id=sample_user.id,
        is_price_change=True,
        llm_confidence=0.95,
        status="pending"
    )
    db_session.add(state)
    await db_session.commit()
    await db_session.refresh(state)
    return state


@pytest.fixture(autouse=True)
async def cleanup_test_data(db_session: AsyncSession):
    """Clean up test data after each test"""
    yield
    # Cleanup is handled by session rollback in db_session fixture

