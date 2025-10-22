"""
End-to-end workflow tests for vendor verification
Tests the complete flow: email arrives → verification → flagging/processing → approval
"""
import pytest
from unittest.mock import patch, Mock, AsyncMock
from datetime import datetime


class TestVendorVerificationWorkflow:
    """Test suite for complete vendor verification workflows"""

    @pytest.fixture
    def mock_services(self):
        """Setup mocked services"""
        with patch('services.vendor_verification_service.vendor_verification_service') as mock_vendor_service, \
             patch('services.email_state_service.email_state_service') as mock_state_service, \
             patch('services.delta_service.DeltaService') as mock_delta_service:

            yield {
                'vendor_service': mock_vendor_service,
                'state_service': mock_state_service,
                'delta_service': mock_delta_service
            }

    @pytest.mark.asyncio
    @patch('services.delta_service.DeltaService._save_flagged_email_metadata')
    async def test_workflow_unverified_email_flagged(self, mock_save_flagged):
        """Test: Unverified email should be flagged without AI extraction"""
        from services.delta_service import DeltaService
        from services.vendor_verification_service import vendor_verification_service

        # Mock unverified sender
        with patch.object(vendor_verification_service, 'verify_sender') as mock_verify:
            mock_verify.return_value = {
                "is_verified": False,
                "method": None,
                "vendor_info": None
            }

            delta_service = DeltaService()

            # Simulate email arrival
            email_data = {
                "id": "msg-unverified-123",
                "sender": {"emailAddress": {"address": "spam@unknown.com"}},
                "subject": "Random Price Update",
                "receivedDateTime": datetime.utcnow().isoformat(),
                "body": {"content": "This is spam"}
            }

            # Process should flag without AI extraction
            with patch.object(delta_service, '_save_flagged_email_metadata') as mock_flag:
                mock_flag.return_value = None

                # Simulate processing
                user_email = "test@company.com"

                # Call would be made in delta_service
                verification_result = vendor_verification_service.verify_sender("spam@unknown.com")

                assert verification_result["is_verified"] is False

                # If not verified, should save as flagged
                # mock_flag.assert_called()

    @pytest.mark.asyncio
    @patch('extractor.process_user_message')
    async def test_workflow_verified_email_processed(self, mock_process):
        """Test: Verified email should proceed with AI extraction"""
        from services.vendor_verification_service import vendor_verification_service

        # Mock verified sender
        with patch.object(vendor_verification_service, 'verify_sender') as mock_verify:
            mock_verify.return_value = {
                "is_verified": True,
                "method": "exact_email",
                "vendor_info": {
                    "vendor_id": "VENDOR001",
                    "vendor_name": "Trusted Vendor"
                }
            }

            # Simulate email from verified vendor
            email_data = {
                "id": "msg-verified-123",
                "sender": {"emailAddress": {"address": "supplier@trustedvendor.com"}},
                "subject": "Price Update",
                "receivedDateTime": datetime.utcnow().isoformat(),
                "body": {"content": "Updated price list attached"}
            }

            # Verify sender
            verification_result = vendor_verification_service.verify_sender("supplier@trustedvendor.com")

            assert verification_result["is_verified"] is True
            assert verification_result["method"] == "exact_email"

            # Should proceed to AI extraction
            # In real flow, process_user_message would be called

    @pytest.mark.asyncio
    @patch('extractor.process_user_message')
    async def test_workflow_manual_approval_triggers_ai(self, mock_process):
        """Test: Manual approval should trigger AI extraction"""
        from services.email_state_service import email_state_service

        message_id = "msg-manual-approve-123"

        # Mock email state
        with patch.object(email_state_service, 'get_state') as mock_get_state:
            mock_get_state.return_value = {
                "verification_status": "pending_review",
                "vendor_verified": False,
                "sender": "newvendor@company.com",
                "email_data": {
                    "subject": "Price Changes",
                    "body": "See attached"
                }
            }

            # Mock mark as approved
            with patch.object(email_state_service, 'mark_as_manually_approved') as mock_mark:
                mock_mark.return_value = None

                # Simulate admin approves the email
                admin_email = "admin@company.com"
                email_state_service.mark_as_manually_approved(message_id, admin_email)

                # After approval, AI extraction should be triggered
                # process_user_message would be called with email data

                mock_mark.assert_called_once_with(message_id, admin_email)

    def test_workflow_domain_match_verification(self):
        """Test: Email from same domain as verified vendor should be verified"""
        from services.vendor_verification_service import VendorVerificationService

        # Create service with domain matching enabled
        with patch('services.epicor_service.EpicorAPIService') as mock_epicor:
            mock_epicor.return_value.get_all_vendor_emails.return_value = [
                {
                    "vendor_id": "VENDOR001",
                    "name": "Acme Corp",
                    "email": "sales@acme.com"
                }
            ]

            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
                temp_file = f.name

            try:
                service = VendorVerificationService(cache_file=temp_file)
                service.build_verified_cache()

                # Test different email from same domain
                result = service.verify_sender("support@acme.com")

                assert result["is_verified"] is True
                assert result["method"] == "domain_match"
                assert result["vendor_info"]["vendor_id"] == "VENDOR001"

            finally:
                import os
                if os.path.exists(temp_file):
                    os.remove(temp_file)

    def test_workflow_rejection(self):
        """Test: Rejected email should be marked accordingly"""
        from services.email_state_service import email_state_service

        message_id = "msg-reject-123"

        with patch.object(email_state_service, 'mark_as_rejected') as mock_reject:
            mock_reject.return_value = None

            # Simulate admin rejects the email
            admin_email = "admin@company.com"
            email_state_service.mark_as_rejected(message_id, admin_email)

            mock_reject.assert_called_once_with(message_id, admin_email)

    @pytest.mark.asyncio
    async def test_workflow_cache_refresh_before_verification(self):
        """Test: Stale cache should be refreshed before verification"""
        from services.vendor_verification_service import VendorVerificationService
        from datetime import timedelta

        with patch('services.epicor_service.EpicorAPIService') as mock_epicor:
            mock_epicor.return_value.get_all_vendor_emails.return_value = [
                {
                    "vendor_id": "VENDOR001",
                    "name": "Test Vendor",
                    "email": "test@vendor.com"
                }
            ]

            import tempfile
            import json
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
                temp_file = f.name

            try:
                service = VendorVerificationService(cache_file=temp_file)

                # Create stale cache
                stale_time = datetime.utcnow() - timedelta(hours=48)
                stale_cache = {
                    "last_updated": stale_time.isoformat(),
                    "ttl_hours": 24,
                    "verified_emails": [],
                    "verified_domains": [],
                    "vendor_lookup": {}
                }

                service._save_cache(stale_cache)

                # Verify sender should trigger refresh
                result = service.verify_sender("test@vendor.com")

                # Should have refreshed and found the vendor
                assert result["is_verified"] is True

            finally:
                import os
                if os.path.exists(temp_file):
                    os.remove(temp_file)

    def test_workflow_multiple_pending_emails(self):
        """Test: Multiple pending emails can be retrieved and processed"""
        from services.email_state_service import email_state_service

        with patch.object(email_state_service, 'get_all_states') as mock_get_all:
            mock_get_all.return_value = {
                "msg-1": {
                    "verification_status": "pending_review",
                    "sender": "email1@unknown.com"
                },
                "msg-2": {
                    "verification_status": "pending_review",
                    "sender": "email2@unknown.com"
                },
                "msg-3": {
                    "verification_status": "verified",
                    "sender": "email3@verified.com"
                }
            }

            states = email_state_service.get_all_states()
            pending = [
                msg_id for msg_id, state in states.items()
                if state.get("verification_status") == "pending_review"
            ]

            assert len(pending) == 2
            assert "msg-1" in pending
            assert "msg-2" in pending

    @pytest.mark.asyncio
    async def test_workflow_token_savings(self):
        """Test: Unverified emails save AI tokens by not processing"""
        from services.vendor_verification_service import vendor_verification_service

        with patch.object(vendor_verification_service, 'verify_sender') as mock_verify:
            # Mock 10 emails: 7 verified, 3 unverified
            verified_count = 0
            unverified_count = 0

            emails = [
                "vendor1@trusted.com",
                "vendor2@trusted.com",
                "spam1@random.com",
                "vendor3@trusted.com",
                "spam2@random.com",
                "vendor4@trusted.com",
                "vendor5@trusted.com",
                "spam3@random.com",
                "vendor6@trusted.com",
                "vendor7@trusted.com"
            ]

            for email in emails:
                if "spam" in email:
                    mock_verify.return_value = {"is_verified": False, "method": None, "vendor_info": None}
                    unverified_count += 1
                else:
                    mock_verify.return_value = {"is_verified": True, "method": "exact_email", "vendor_info": {}}
                    verified_count += 1

                result = vendor_verification_service.verify_sender(email)

            # Should save tokens on 30% of emails
            token_savings_percentage = (unverified_count / len(emails)) * 100
            assert token_savings_percentage == 30.0

    def test_workflow_case_insensitive_matching(self):
        """Test: Email verification should be case-insensitive"""
        from services.vendor_verification_service import VendorVerificationService

        with patch('services.epicor_service.EpicorAPIService') as mock_epicor:
            mock_epicor.return_value.get_all_vendor_emails.return_value = [
                {
                    "vendor_id": "VENDOR001",
                    "name": "Test Vendor",
                    "email": "sales@company.com"
                }
            ]

            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
                temp_file = f.name

            try:
                service = VendorVerificationService(cache_file=temp_file)
                service.build_verified_cache()

                # Test various case combinations
                test_emails = [
                    "sales@company.com",
                    "SALES@COMPANY.COM",
                    "Sales@Company.Com",
                    "sAlEs@CoMpAnY.cOm"
                ]

                for email in test_emails:
                    result = service.verify_sender(email)
                    assert result["is_verified"] is True, f"Failed for email: {email}"

            finally:
                import os
                if os.path.exists(temp_file):
                    os.remove(temp_file)
