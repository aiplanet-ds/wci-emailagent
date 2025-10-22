"""
Unit tests for VendorVerificationService
"""
import pytest
import json
import os
from datetime import datetime, timedelta
from unittest.mock import patch, Mock
from services.vendor_verification_service import VendorVerificationService


class TestVendorVerificationService:
    """Test suite for VendorVerificationService"""

    def test_initialization(self, temp_cache_file):
        """Test service initialization"""
        service = VendorVerificationService(cache_file=temp_cache_file)
        assert service.cache_file == temp_cache_file
        assert service.cache_ttl_hours == 24
        assert service.domain_matching_enabled is True

    def test_ensure_data_directory(self, tmp_path):
        """Test data directory creation"""
        cache_file = str(tmp_path / "test_dir" / "cache.json")
        service = VendorVerificationService(cache_file=cache_file)
        assert os.path.exists(os.path.dirname(cache_file))

    def test_load_cache_empty(self, temp_cache_file):
        """Test loading cache when file doesn't exist"""
        service = VendorVerificationService(cache_file=temp_cache_file)
        cache = service._load_cache()

        assert cache["last_updated"] is None
        assert cache["verified_emails"] == []
        assert cache["verified_domains"] == []
        assert cache["vendor_lookup"] == {}

    def test_save_and_load_cache(self, temp_cache_file, sample_cache_data):
        """Test saving and loading cache"""
        service = VendorVerificationService(cache_file=temp_cache_file)
        service._save_cache(sample_cache_data)

        loaded_cache = service._load_cache()
        assert loaded_cache["verified_emails"] == sample_cache_data["verified_emails"]
        assert loaded_cache["verified_domains"] == sample_cache_data["verified_domains"]
        assert len(loaded_cache["vendor_lookup"]) == len(sample_cache_data["vendor_lookup"])

    def test_is_cache_stale_no_cache(self, temp_cache_file):
        """Test cache staleness when no cache exists"""
        service = VendorVerificationService(cache_file=temp_cache_file)
        assert service.is_cache_stale() is True

    def test_is_cache_stale_fresh(self, temp_cache_file, sample_cache_data):
        """Test cache staleness with fresh cache"""
        service = VendorVerificationService(cache_file=temp_cache_file)
        service._save_cache(sample_cache_data)
        assert service.is_cache_stale() is False

    def test_is_cache_stale_old(self, temp_cache_file, stale_cache_data):
        """Test cache staleness with old cache"""
        service = VendorVerificationService(cache_file=temp_cache_file)
        service._save_cache(stale_cache_data)
        assert service.is_cache_stale() is True

    @patch('services.epicor_service.EpicorAPIService')
    def test_fetch_vendors_from_epicor(self, mock_epicor_class, temp_cache_file, sample_vendor_data):
        """Test fetching vendors from Epicor"""
        mock_epicor = Mock()
        mock_epicor.get_all_vendor_emails.return_value = sample_vendor_data
        mock_epicor_class.return_value = mock_epicor

        service = VendorVerificationService(cache_file=temp_cache_file)
        vendors = service.fetch_vendors_from_epicor()

        assert len(vendors) == 4
        assert vendors[0]["vendor_id"] == "VENDOR001"
        mock_epicor.get_all_vendor_emails.assert_called_once()

    @patch('services.epicor_service.EpicorAPIService')
    def test_build_verified_cache(self, mock_epicor_class, temp_cache_file, sample_vendor_data):
        """Test building verified cache"""
        mock_epicor = Mock()
        mock_epicor.get_all_vendor_emails.return_value = sample_vendor_data
        mock_epicor_class.return_value = mock_epicor

        service = VendorVerificationService(cache_file=temp_cache_file)
        cache = service.build_verified_cache()

        assert len(cache["verified_emails"]) == 4
        assert len(cache["verified_domains"]) == 2
        assert "testcompany.com" in cache["verified_domains"]
        assert "anothercompany.com" in cache["verified_domains"]
        assert "vendor1@testcompany.com" in cache["verified_emails"]

    @patch('services.epicor_service.EpicorAPIService')
    def test_build_cache_with_domain_lookup(self, mock_epicor_class, temp_cache_file, sample_vendor_data):
        """Test that domain lookup is created correctly"""
        mock_epicor = Mock()
        mock_epicor.get_all_vendor_emails.return_value = sample_vendor_data
        mock_epicor_class.return_value = mock_epicor

        service = VendorVerificationService(cache_file=temp_cache_file)
        cache = service.build_verified_cache()

        # Check domain keys in lookup
        assert "@testcompany.com" in cache["vendor_lookup"]
        assert "@anothercompany.com" in cache["vendor_lookup"]

    def test_verify_sender_exact_match(self, temp_cache_file, sample_cache_data):
        """Test exact email verification"""
        service = VendorVerificationService(cache_file=temp_cache_file)
        service._save_cache(sample_cache_data)

        result = service.verify_sender("vendor1@testcompany.com")

        assert result["is_verified"] is True
        assert result["method"] == "exact_email"
        assert result["vendor_info"]["vendor_id"] == "VENDOR001"

    def test_verify_sender_domain_match(self, temp_cache_file, sample_cache_data):
        """Test domain-based verification"""
        service = VendorVerificationService(cache_file=temp_cache_file)
        service._save_cache(sample_cache_data)

        # Test email not in exact list but domain matches
        result = service.verify_sender("newperson@testcompany.com")

        assert result["is_verified"] is True
        assert result["method"] == "domain_match"
        assert result["vendor_info"]["vendor_id"] == "VENDOR001"

    def test_verify_sender_case_insensitive(self, temp_cache_file, sample_cache_data):
        """Test case insensitive verification"""
        service = VendorVerificationService(cache_file=temp_cache_file)
        service._save_cache(sample_cache_data)

        result = service.verify_sender("VENDOR1@TESTCOMPANY.COM")

        assert result["is_verified"] is True
        assert result["method"] == "exact_email"

    def test_verify_sender_not_verified(self, temp_cache_file, sample_cache_data):
        """Test unverified sender"""
        service = VendorVerificationService(cache_file=temp_cache_file)
        service._save_cache(sample_cache_data)

        result = service.verify_sender("random@unknown.com")

        assert result["is_verified"] is False
        assert result["method"] is None
        assert result["vendor_info"] is None

    def test_verify_sender_empty_email(self, temp_cache_file, sample_cache_data):
        """Test verification with empty email"""
        service = VendorVerificationService(cache_file=temp_cache_file)
        service._save_cache(sample_cache_data)

        result = service.verify_sender("")

        assert result["is_verified"] is False
        assert result["method"] is None

    def test_verify_sender_domain_matching_disabled(self, temp_cache_file, sample_cache_data, monkeypatch):
        """Test verification with domain matching disabled"""
        monkeypatch.setenv("VENDOR_DOMAIN_MATCHING_ENABLED", "false")
        service = VendorVerificationService(cache_file=temp_cache_file)
        service._save_cache(sample_cache_data)

        # Should not match via domain
        result = service.verify_sender("newperson@testcompany.com")

        assert result["is_verified"] is False

    def test_get_cache_status(self, temp_cache_file, sample_cache_data):
        """Test getting cache status"""
        service = VendorVerificationService(cache_file=temp_cache_file)
        service._save_cache(sample_cache_data)

        status = service.get_cache_status()

        assert status["last_updated"] is not None
        assert status["vendor_count"] == 4  # 4 unique vendors
        assert status["email_count"] == 4
        assert status["domain_count"] == 2
        assert status["is_stale"] is False
        assert status["ttl_hours"] == 24
        assert status["domain_matching_enabled"] is True

    def test_get_cache_status_stale(self, temp_cache_file, stale_cache_data):
        """Test cache status with stale cache"""
        service = VendorVerificationService(cache_file=temp_cache_file)
        service._save_cache(stale_cache_data)

        status = service.get_cache_status()

        assert status["is_stale"] is True

    @patch('services.epicor_service.EpicorAPIService')
    def test_refresh_cache(self, mock_epicor_class, temp_cache_file, sample_vendor_data):
        """Test cache refresh"""
        mock_epicor = Mock()
        mock_epicor.get_all_vendor_emails.return_value = sample_vendor_data
        mock_epicor_class.return_value = mock_epicor

        service = VendorVerificationService(cache_file=temp_cache_file)
        cache = service.refresh_cache()

        assert len(cache["verified_emails"]) == 4
        assert cache["last_updated"] is not None

    @patch('services.epicor_service.EpicorAPIService')
    def test_verify_sender_refreshes_stale_cache(self, mock_epicor_class, temp_cache_file, stale_cache_data, sample_vendor_data):
        """Test that verify_sender refreshes stale cache"""
        mock_epicor = Mock()
        mock_epicor.get_all_vendor_emails.return_value = sample_vendor_data
        mock_epicor_class.return_value = mock_epicor

        service = VendorVerificationService(cache_file=temp_cache_file)
        service._save_cache(stale_cache_data)

        # Should trigger refresh
        result = service.verify_sender("vendor1@testcompany.com")

        # Cache should be refreshed
        cache = service._load_cache()
        updated_time = datetime.fromisoformat(cache["last_updated"])
        assert (datetime.utcnow() - updated_time).total_seconds() < 10  # Updated recently

    @patch('services.epicor_service.EpicorAPIService')
    def test_build_cache_empty_vendors(self, mock_epicor_class, temp_cache_file):
        """Test building cache with no vendors"""
        mock_epicor = Mock()
        mock_epicor.get_all_vendor_emails.return_value = []
        mock_epicor_class.return_value = mock_epicor

        service = VendorVerificationService(cache_file=temp_cache_file)
        cache = service.build_verified_cache()

        assert cache["verified_emails"] == []
        assert cache["verified_domains"] == []
        assert cache["vendor_lookup"] == {}

    def test_whitespace_handling(self, temp_cache_file, sample_cache_data):
        """Test email whitespace handling"""
        service = VendorVerificationService(cache_file=temp_cache_file)
        service._save_cache(sample_cache_data)

        result = service.verify_sender("  vendor1@testcompany.com  ")

        assert result["is_verified"] is True
        assert result["method"] == "exact_email"
