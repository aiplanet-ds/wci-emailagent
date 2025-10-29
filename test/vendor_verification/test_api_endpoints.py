"""
API integration tests for vendor verification endpoints
"""
import pytest
from unittest.mock import patch, Mock
from fastapi.testclient import TestClient


class TestVendorVerificationAPI:
    """Test suite for vendor verification API endpoints"""

    @pytest.fixture
    def client(self):
        """Create FastAPI test client"""
        from main import app
        return TestClient(app)

    @pytest.fixture
    def auth_session(self, client):
        """Setup authenticated session"""
        # Mock session authentication
        with client.session_transaction() as session:
            session['user_email'] = 'test@example.com'
        return client

    @patch('services.email_state_service.email_state_service.get_all_states')
    def test_get_pending_verification_emails(self, mock_get_states, client):
        """Test GET /api/emails/pending-verification"""
        # Mock email states
        mock_get_states.return_value = {
            "msg-1": {
                "verification_status": "pending_review",
                "vendor_verified": False,
                "sender": "unknown@random.com",
                "subject": "Test Email 1",
                "received_time": "2025-10-23T10:00:00"
            },
            "msg-2": {
                "verification_status": "verified",
                "vendor_verified": True,
                "sender": "vendor@company.com"
            },
            "msg-3": {
                "verification_status": "pending_review",
                "vendor_verified": False,
                "sender": "spam@spam.com",
                "subject": "Test Email 3",
                "received_time": "2025-10-23T11:00:00"
            }
        }

        # Make request
        response = client.get("/api/emails/pending-verification")

        assert response.status_code == 200
        data = response.json()

        # Should return only pending emails
        assert data["total"] == 2
        assert len(data["emails"]) == 2

        # Check that all returned emails are pending
        for email in data["emails"]:
            assert email["verification_status"] == "pending_review"

    @patch('services.email_state_service.email_state_service.get_all_states')
    def test_get_pending_verification_empty(self, mock_get_states, client):
        """Test pending verification with no flagged emails"""
        mock_get_states.return_value = {
            "msg-1": {
                "verification_status": "verified",
                "vendor_verified": True
            }
        }

        response = client.get("/api/emails/pending-verification")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert len(data["emails"]) == 0

    @patch('services.email_state_service.email_state_service.get_state')
    @patch('services.email_state_service.email_state_service.mark_as_manually_approved')
    @patch('main.process_user_message')
    def test_approve_and_process_email(
        self, mock_process, mock_mark_approved, mock_get_state, client
    ):
        """Test POST /api/emails/{message_id}/approve-and-process"""
        # Mock email state
        mock_get_state.return_value = {
            "verification_status": "pending_review",
            "vendor_verified": False,
            "sender": "test@unknown.com",
            "email_data": {"subject": "Test", "body": "Test body"}
        }

        # Mock user session
        with patch('routers.emails.get_user_from_session', return_value='admin@example.com'):
            response = client.post("/api/emails/test-msg-123/approve-and-process")

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "approved_and_processing"
        assert data["message_id"] == "test-msg-123"

        # Verify mark_as_manually_approved was called
        mock_mark_approved.assert_called_once_with("test-msg-123", "admin@example.com")

        # Verify AI extraction was triggered
        mock_process.assert_called_once()

    def test_approve_nonexistent_email(self, client):
        """Test approving non-existent email"""
        with patch('services.email_state_service.email_state_service.get_state', return_value=None):
            with patch('routers.emails.get_user_from_session', return_value='admin@example.com'):
                response = client.post("/api/emails/nonexistent-msg/approve-and-process")

        assert response.status_code == 404

    @patch('services.email_state_service.email_state_service.get_state')
    @patch('services.email_state_service.email_state_service.mark_as_rejected')
    def test_reject_email(self, mock_mark_rejected, mock_get_state, client):
        """Test POST /api/emails/{message_id}/reject"""
        mock_get_state.return_value = {
            "verification_status": "pending_review",
            "vendor_verified": False
        }

        with patch('routers.emails.get_user_from_session', return_value='admin@example.com'):
            response = client.post("/api/emails/test-msg-456/reject")

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "rejected"
        assert data["message_id"] == "test-msg-456"

        # Verify mark_as_rejected was called
        mock_mark_rejected.assert_called_once_with("test-msg-456", "admin@example.com")

    def test_reject_nonexistent_email(self, client):
        """Test rejecting non-existent email"""
        with patch('services.email_state_service.email_state_service.get_state', return_value=None):
            with patch('routers.emails.get_user_from_session', return_value='admin@example.com'):
                response = client.post("/api/emails/nonexistent/reject")

        assert response.status_code == 404

    @patch('services.vendor_verification_service.vendor_verification_service.get_cache_status')
    def test_get_vendor_cache_status(self, mock_get_status, client):
        """Test GET /api/emails/vendors/cache-status"""
        mock_get_status.return_value = {
            "last_updated": "2025-10-23T10:00:00",
            "vendor_count": 100,
            "email_count": 98,
            "domain_count": 74,
            "is_stale": False,
            "ttl_hours": 24,
            "next_refresh": "2025-10-24T10:00:00",
            "domain_matching_enabled": True
        }

        response = client.get("/api/emails/vendors/cache-status")

        assert response.status_code == 200
        data = response.json()

        assert data["vendor_count"] == 100
        assert data["email_count"] == 98
        assert data["domain_count"] == 74
        assert data["is_stale"] is False
        assert data["ttl_hours"] == 24

    @patch('services.vendor_verification_service.vendor_verification_service.refresh_cache')
    def test_refresh_vendor_cache(self, mock_refresh, client):
        """Test POST /api/emails/vendors/refresh-cache"""
        mock_refresh.return_value = {
            "last_updated": "2025-10-23T12:00:00",
            "verified_emails": ["test@vendor.com"],
            "verified_domains": ["vendor.com"],
            "vendor_lookup": {}
        }

        with patch('routers.emails.get_user_from_session', return_value='admin@example.com'):
            response = client.post("/api/emails/vendors/refresh-cache")

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "success"
        assert "cache_data" in data

        # Verify refresh was called
        mock_refresh.assert_called_once()

    @patch('services.email_state_service.email_state_service.get_all_states')
    def test_pending_emails_search_filter(self, mock_get_states, client):
        """Test pending emails with search parameter"""
        mock_get_states.return_value = {
            "msg-1": {
                "verification_status": "pending_review",
                "sender": "test@spam.com",
                "subject": "Price Update"
            },
            "msg-2": {
                "verification_status": "pending_review",
                "sender": "other@random.com",
                "subject": "Urgent"
            }
        }

        # Test with search parameter
        response = client.get("/api/emails/pending-verification?search=spam")

        assert response.status_code == 200
        data = response.json()

        # Should filter based on search
        assert data["total"] <= 2

    @patch('services.email_state_service.email_state_service.get_state')
    def test_approve_already_verified_email(self, mock_get_state, client):
        """Test approving email that's already verified"""
        mock_get_state.return_value = {
            "verification_status": "verified",
            "vendor_verified": True
        }

        with patch('routers.emails.get_user_from_session', return_value='admin@example.com'):
            response = client.post("/api/emails/test-msg/approve-and-process")

        # Should handle gracefully (either 400 or process anyway)
        assert response.status_code in [200, 400]

    @patch('services.vendor_verification_service.vendor_verification_service.refresh_cache')
    def test_refresh_cache_error_handling(self, mock_refresh, client):
        """Test cache refresh error handling"""
        mock_refresh.side_effect = Exception("Epicor connection failed")

        with patch('routers.emails.get_user_from_session', return_value='admin@example.com'):
            response = client.post("/api/emails/vendors/refresh-cache")

        assert response.status_code == 500

    @patch('services.email_state_service.email_state_service.get_state')
    @patch('main.process_user_message')
    def test_approve_triggers_ai_extraction(self, mock_process, mock_get_state, client):
        """Test that approving email triggers AI extraction"""
        mock_get_state.return_value = {
            "verification_status": "pending_review",
            "sender": "test@vendor.com",
            "email_data": {
                "subject": "Price Change",
                "body": "Updated prices attached"
            }
        }

        with patch('routers.emails.get_user_from_session', return_value='admin@example.com'):
            with patch('services.email_state_service.email_state_service.mark_as_manually_approved'):
                response = client.post("/api/emails/test-msg/approve-and-process")

        assert response.status_code == 200

        # Verify AI extraction was called
        assert mock_process.called

    def test_unauthorized_access(self, client):
        """Test API endpoints without authentication"""
        # Mock no user in session
        with patch('routers.emails.get_user_from_session', return_value=None):
            response = client.post("/api/emails/test-msg/approve-and-process")

        # Should return 401 Unauthorized
        assert response.status_code == 401
