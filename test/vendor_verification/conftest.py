"""
Pytest fixtures for vendor verification tests
"""
import pytest
import json
import os
import tempfile
from datetime import datetime, timedelta
from typing import Dict, Any, List
from unittest.mock import Mock, MagicMock


@pytest.fixture
def temp_cache_file():
    """Create a temporary cache file for testing"""
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
        temp_file = f.name
    yield temp_file
    # Cleanup
    if os.path.exists(temp_file):
        os.remove(temp_file)


@pytest.fixture
def sample_vendor_data():
    """Sample vendor data from Epicor"""
    return [
        {
            "vendor_id": "VENDOR001",
            "name": "Test Vendor 1",
            "email": "vendor1@testcompany.com"
        },
        {
            "vendor_id": "VENDOR002",
            "name": "Test Vendor 2",
            "email": "vendor2@testcompany.com"
        },
        {
            "vendor_id": "VENDOR003",
            "name": "Test Vendor 3",
            "email": "sales@anothercompany.com"
        },
        {
            "vendor_id": "VENDOR004",
            "name": "Test Vendor 4",
            "email": "info@anothercompany.com"  # Same domain as VENDOR003
        }
    ]


@pytest.fixture
def sample_cache_data():
    """Sample cache data structure"""
    return {
        "last_updated": datetime.utcnow().isoformat(),
        "ttl_hours": 24,
        "verified_emails": [
            "vendor1@testcompany.com",
            "vendor2@testcompany.com",
            "sales@anothercompany.com",
            "info@anothercompany.com"
        ],
        "verified_domains": [
            "testcompany.com",
            "anothercompany.com"
        ],
        "vendor_lookup": {
            "vendor1@testcompany.com": {
                "vendor_id": "VENDOR001",
                "vendor_name": "Test Vendor 1"
            },
            "vendor2@testcompany.com": {
                "vendor_id": "VENDOR002",
                "vendor_name": "Test Vendor 2"
            },
            "sales@anothercompany.com": {
                "vendor_id": "VENDOR003",
                "vendor_name": "Test Vendor 3"
            },
            "info@anothercompany.com": {
                "vendor_id": "VENDOR004",
                "vendor_name": "Test Vendor 4"
            },
            "@testcompany.com": {
                "vendor_id": "VENDOR001",
                "vendor_name": "Test Vendor 1"
            },
            "@anothercompany.com": {
                "vendor_id": "VENDOR003",
                "vendor_name": "Test Vendor 3"
            }
        }
    }


@pytest.fixture
def stale_cache_data(sample_cache_data):
    """Cache data that is stale (older than TTL)"""
    cache = sample_cache_data.copy()
    # Set last_updated to 48 hours ago (stale if TTL is 24 hours)
    stale_time = datetime.utcnow() - timedelta(hours=48)
    cache["last_updated"] = stale_time.isoformat()
    return cache


@pytest.fixture
def mock_epicor_service(sample_vendor_data):
    """Mock Epicor API service"""
    mock = Mock()
    mock.get_all_vendor_emails = Mock(return_value=sample_vendor_data)
    return mock


@pytest.fixture
def sample_email_metadata():
    """Sample email metadata for testing"""
    return {
        "message_id": "test-message-123",
        "sender": "vendor1@testcompany.com",
        "subject": "Price Update for Parts",
        "received_time": datetime.utcnow().isoformat(),
        "body_preview": "This is a test price change email..."
    }


@pytest.fixture
def unverified_email_metadata():
    """Sample unverified email metadata"""
    return {
        "message_id": "test-message-456",
        "sender": "random@unknown.com",
        "subject": "Spam Price Update",
        "received_time": datetime.utcnow().isoformat(),
        "body_preview": "This is a random spam email..."
    }


@pytest.fixture
def mock_email_state_service():
    """Mock email state service"""
    mock = Mock()
    mock.get_all_states = Mock(return_value={})
    mock.get_state = Mock(return_value={
        "verification_status": "pending_review",
        "vendor_verified": False
    })
    mock.mark_as_vendor_verified = Mock()
    mock.mark_as_manually_approved = Mock()
    mock.mark_as_rejected = Mock()
    return mock


@pytest.fixture
def test_app_client():
    """Create FastAPI test client"""
    from fastapi.testclient import TestClient
    from main import app
    return TestClient(app)


@pytest.fixture(autouse=True)
def setup_test_env(monkeypatch):
    """Setup test environment variables"""
    monkeypatch.setenv("VENDOR_VERIFICATION_ENABLED", "true")
    monkeypatch.setenv("VENDOR_CACHE_TTL_HOURS", "24")
    monkeypatch.setenv("VENDOR_DOMAIN_MATCHING_ENABLED", "true")
