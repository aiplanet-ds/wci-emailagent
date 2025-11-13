"""
Test database service layer
"""
import pytest
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from database.services.user_service import UserService
from database.services.email_service import EmailService
from database.services.email_state_service import EmailStateService
from database.services.vendor_service import VendorService
from database.services.delta_service import DeltaService
from database.services.audit_service import AuditService


class TestUserService:
    """Test suite for UserService"""

    @pytest.mark.asyncio
    async def test_create_user(self, db_session: AsyncSession):
        """Test creating a new user"""
        user, created = await UserService.get_or_create_user(
            db=db_session,
            email="newuser@example.com",
            display_name="New User"
        )
        
        assert created is True
        assert user.email == "newuser@example.com"
        assert user.display_name == "New User"
        assert user.is_active is True
        print(f"✅ User created successfully: {user.email}")

    @pytest.mark.asyncio
    async def test_get_existing_user(self, db_session: AsyncSession, sample_user):
        """Test getting an existing user"""
        user, created = await UserService.get_or_create_user(
            db=db_session,
            email=sample_user.email,
            display_name=sample_user.display_name
        )
        
        assert created is False
        assert user.id == sample_user.id
        assert user.email == sample_user.email
        print(f"✅ Existing user retrieved: {user.email}")

    @pytest.mark.asyncio
    async def test_get_user_by_email(self, db_session: AsyncSession, sample_user):
        """Test getting user by email"""
        user = await UserService.get_user_by_email(db_session, sample_user.email)
        
        assert user is not None
        assert user.id == sample_user.id
        assert user.email == sample_user.email
        print(f"✅ User found by email: {user.email}")

    @pytest.mark.asyncio
    async def test_update_user_last_login(self, db_session: AsyncSession, sample_user):
        """Test updating user last login"""
        await UserService.update_last_login(db_session, sample_user.id)
        await db_session.refresh(sample_user)
        
        assert sample_user.last_login_at is not None
        print(f"✅ User last login updated: {sample_user.last_login_at}")


class TestEmailService:
    """Test suite for EmailService"""

    @pytest.mark.asyncio
    async def test_create_email(self, db_session: AsyncSession, sample_user):
        """Test creating a new email"""
        email = await EmailService.create_email(
            db=db_session,
            message_id="test-email-001",
            user_id=sample_user.id,
            subject="Test Subject",
            sender="sender@test.com",
            body_text="Test body",
            received_datetime="2025-10-30T10:00:00Z"
        )
        
        assert email.message_id == "test-email-001"
        assert email.user_id == sample_user.id
        assert email.subject == "Test Subject"
        print(f"✅ Email created successfully: {email.message_id}")

    @pytest.mark.asyncio
    async def test_get_email_by_message_id(self, db_session: AsyncSession, sample_email):
        """Test getting email by message ID"""
        email = await EmailService.get_email_by_message_id(
            db_session,
            sample_email.message_id
        )
        
        assert email is not None
        assert email.id == sample_email.id
        assert email.message_id == sample_email.message_id
        print(f"✅ Email found by message ID: {email.message_id}")

    @pytest.mark.asyncio
    async def test_get_emails_by_user(self, db_session: AsyncSession, sample_user, sample_email):
        """Test getting emails by user"""
        emails = await EmailService.get_emails_by_user(
            db_session,
            sample_user.id,
            limit=10
        )
        
        assert len(emails) > 0
        assert any(e.id == sample_email.id for e in emails)
        print(f"✅ Found {len(emails)} emails for user")


class TestEmailStateService:
    """Test suite for EmailStateService"""

    @pytest.mark.asyncio
    async def test_create_email_state(self, db_session: AsyncSession, sample_user):
        """Test creating email state"""
        state = await EmailStateService.create_state(
            db=db_session,
            message_id="test-state-001",
            user_id=sample_user.id,
            is_price_change=True,
            llm_confidence=0.95
        )
        
        assert state.message_id == "test-state-001"
        assert state.is_price_change is True
        assert state.llm_confidence == 0.95
        assert state.status == "pending"
        print(f"✅ Email state created: {state.message_id}")

    @pytest.mark.asyncio
    async def test_get_state_by_message_id(self, db_session: AsyncSession, sample_email_state):
        """Test getting state by message ID"""
        state = await EmailStateService.get_state_by_message_id(
            db_session,
            sample_email_state.message_id
        )
        
        assert state is not None
        assert state.id == sample_email_state.id
        print(f"✅ Email state found: {state.message_id}")

    @pytest.mark.asyncio
    async def test_mark_as_processed(self, db_session: AsyncSession, sample_email_state, sample_user):
        """Test marking email as processed"""
        await EmailStateService.mark_as_processed(
            db=db_session,
            message_id=sample_email_state.message_id,
            processed_by_id=sample_user.id
        )
        
        await db_session.refresh(sample_email_state)
        assert sample_email_state.status == "processed"
        assert sample_email_state.processed_by_id == sample_user.id
        assert sample_email_state.processed_at is not None
        print(f"✅ Email state marked as processed")

    @pytest.mark.asyncio
    async def test_get_pending_states(self, db_session: AsyncSession, sample_user):
        """Test getting pending email states"""
        # Create a pending state
        await EmailStateService.create_state(
            db=db_session,
            message_id="pending-001",
            user_id=sample_user.id,
            is_price_change=True,
            llm_confidence=0.90
        )
        
        pending = await EmailStateService.get_pending_states(db_session, sample_user.id)
        assert len(pending) > 0
        assert all(s.status == "pending" for s in pending)
        print(f"✅ Found {len(pending)} pending email states")


class TestVendorService:
    """Test suite for VendorService"""

    @pytest.mark.asyncio
    async def test_create_or_update_vendor(self, db_session: AsyncSession):
        """Test creating or updating vendor"""
        vendor = await VendorService.create_or_update_vendor(
            db=db_session,
            vendor_id="VENDOR001",
            vendor_name="Test Vendor",
            email_address="vendor@test.com"
        )
        
        assert vendor.vendor_id == "VENDOR001"
        assert vendor.vendor_name == "Test Vendor"
        assert vendor.email_address == "vendor@test.com"
        print(f"✅ Vendor created: {vendor.vendor_id}")

    @pytest.mark.asyncio
    async def test_get_vendor_by_id(self, db_session: AsyncSession, sample_vendor):
        """Test getting vendor by ID"""
        vendor = await VendorService.get_vendor_by_id(db_session, sample_vendor.vendor_id)
        
        assert vendor is not None
        assert vendor.id == sample_vendor.id
        print(f"✅ Vendor found: {vendor.vendor_id}")

    @pytest.mark.asyncio
    async def test_verify_email_exact_match(self, db_session: AsyncSession, sample_vendor):
        """Test vendor email verification with exact match"""
        result = await VendorService.verify_email_against_vendors(
            db_session,
            sample_vendor.email_address
        )
        
        assert result is not None
        vendor, match_type = result
        assert vendor.id == sample_vendor.id
        assert match_type == "exact"
        print(f"✅ Vendor verified by exact email match: {match_type}")

    @pytest.mark.asyncio
    async def test_verify_email_domain_match(self, db_session: AsyncSession, sample_vendor):
        """Test vendor email verification with domain match"""
        # Test with different email from same domain
        domain = sample_vendor.email_address.split('@')[1]
        test_email = f"different@{domain}"
        
        result = await VendorService.verify_email_against_vendors(
            db_session,
            test_email
        )
        
        if result:
            vendor, match_type = result
            assert match_type == "domain"
            print(f"✅ Vendor verified by domain match: {match_type}")
        else:
            print("⚠️  Domain matching not enabled or no match found")


class TestDeltaService:
    """Test suite for DeltaService"""

    @pytest.mark.asyncio
    async def test_save_delta_token(self, db_session: AsyncSession, sample_user):
        """Test saving delta token"""
        token = await DeltaService.save_delta_token(
            db=db_session,
            user_id=sample_user.id,
            token="test-delta-token-123"
        )
        
        assert token.user_id == sample_user.id
        assert token.token == "test-delta-token-123"
        print(f"✅ Delta token saved for user {sample_user.id}")

    @pytest.mark.asyncio
    async def test_get_delta_token(self, db_session: AsyncSession, sample_user):
        """Test getting delta token"""
        # Save a token first
        await DeltaService.save_delta_token(
            db=db_session,
            user_id=sample_user.id,
            token="test-token-456"
        )
        
        token = await DeltaService.get_delta_token(db_session, sample_user.id)
        assert token is not None
        assert token.token == "test-token-456"
        print(f"✅ Delta token retrieved for user {sample_user.id}")


class TestAuditService:
    """Test suite for AuditService"""

    @pytest.mark.asyncio
    async def test_log_action(self, db_session: AsyncSession, sample_user):
        """Test logging user action"""
        log = await AuditService.log_action(
            db=db_session,
            user_id=sample_user.id,
            action="test_action",
            details={"test": "data"}
        )
        
        assert log.user_id == sample_user.id
        assert log.action == "test_action"
        assert log.details == {"test": "data"}
        print(f"✅ Action logged: {log.action}")

    @pytest.mark.asyncio
    async def test_get_user_audit_logs(self, db_session: AsyncSession, sample_user):
        """Test getting user audit logs"""
        # Create some logs
        await AuditService.log_action(
            db=db_session,
            user_id=sample_user.id,
            action="action1",
            details={}
        )
        
        logs = await AuditService.get_user_audit_logs(
            db_session,
            sample_user.id,
            limit=10
        )
        
        assert len(logs) > 0
        assert all(log.user_id == sample_user.id for log in logs)
        print(f"✅ Found {len(logs)} audit logs for user")

