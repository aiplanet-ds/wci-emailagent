"""
Epicor OAuth Authentication Service
Automatically generates and refreshes Bearer tokens with database persistence
"""

import os
import httpx
import time
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from dotenv import load_dotenv
import logging
from utils.http_client import HTTPClientManager

load_dotenv()

logger = logging.getLogger(__name__)

# Service name constant for database
SERVICE_NAME = "epicor"


class EpicorAuthService:
    """Service for managing Epicor OAuth authentication with database persistence"""

    def __init__(self):
        """Initialize Epicor OAuth service"""
        # OAuth Configuration
        self.token_url = "https://login.epicor.com/connect/token"
        self.client_id = os.getenv("EPICOR_CLIENT_ID", "f4471628-2e91-4a29-bdac-0aa6e4dad31f")
        self.client_secret = os.getenv("EPICOR_CLIENT_SECRET", "")
        self.username = os.getenv("EPICOR_USERNAME", "abhijit.kumar@akkodisgroup.com")
        self.password = os.getenv("EPICOR_PASSWORD", "")
        self.company_id = os.getenv("EPICOR_COMPANY_ID", "165122")
        # Use correct scope for Epicor OAuth - "epicor_erp" for client_credentials
        # "openid email epicor_erp" only works with password grant
        self.scope_client_credentials = "epicor_erp"
        self.scope_password = "openid email epicor_erp"

        # Auto-token is now always enabled when credentials are available
        self.auto_token_enabled = bool(self.client_secret or (self.username and self.password))

        # In-memory token cache (loaded from database on first access)
        self._access_token: Optional[str] = None
        self._refresh_token: Optional[str] = None
        self._token_expires_at: float = 0
        self._token_loaded: bool = False

        if self.auto_token_enabled:
            logger.info("✅ Epicor OAuth Service initialized (auto-token enabled with DB storage)")
        else:
            logger.info("⚠️ Epicor OAuth Service initialized (no credentials configured)")
    
    async def _request_token_with_client_credentials(self) -> Dict[str, Any]:
        """
        Request Bearer token using client credentials (Client Credentials Grant).
        This is an async HTTP call - database storage is handled separately.

        Returns:
            Dictionary with token information
        """
        try:
            logger.info("Requesting Bearer token with client credentials...")

            # Prepare token request for client_credentials grant
            data = {
                "grant_type": "client_credentials",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "scope": self.scope_client_credentials
            }

            # Request token
            client = await HTTPClientManager.get_general_client()
            response = await client.post(
                self.token_url,
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=30.0
            )

            if response.status_code == 200:
                token_data = response.json()
                expires_in = token_data.get("expires_in", 3600)

                logger.info(f"Bearer token obtained successfully via client_credentials (expires in {expires_in}s)")

                return {
                    "status": "success",
                    "access_token": token_data.get("access_token"),
                    "refresh_token": token_data.get("refresh_token"),
                    "expires_in": expires_in,
                    "token_type": token_data.get("token_type", "Bearer"),
                    "grant_type": "client_credentials",
                    "scope": self.scope_client_credentials
                }
            else:
                logger.error(f"Client credentials token request failed: {response.status_code}")
                logger.error(f"   Response: {response.text}")
                return {
                    "status": "error",
                    "message": f"HTTP {response.status_code}: {response.text}",
                    "status_code": response.status_code,
                    "grant_type": "client_credentials"
                }

        except Exception as e:
            logger.error(f"Client credentials token request error: {e}")
            return {
                "status": "error",
                "message": str(e),
                "grant_type": "client_credentials"
            }

    async def _request_token_with_password(self) -> Dict[str, Any]:
        """
        Request Bearer token using username/password (Resource Owner Password Credentials Grant).
        This is an async HTTP call - database storage is handled separately.

        Returns:
            Dictionary with token information
        """
        try:
            logger.info("Requesting Bearer token with username/password...")

            # Prepare token request
            data = {
                "grant_type": "password",
                "username": self.username,
                "password": self.password,
                "client_id": self.client_id,
                "scope": self.scope_password
            }

            # Add client_secret if available
            if self.client_secret:
                data["client_secret"] = self.client_secret

            # Request token
            client = await HTTPClientManager.get_general_client()
            response = await client.post(
                self.token_url,
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=10.0
            )

            if response.status_code == 200:
                token_data = response.json()
                expires_in = token_data.get("expires_in", 3600)

                logger.info(f"Bearer token obtained successfully via password (expires in {expires_in}s)")

                return {
                    "status": "success",
                    "access_token": token_data.get("access_token"),
                    "refresh_token": token_data.get("refresh_token"),
                    "expires_in": expires_in,
                    "token_type": token_data.get("token_type", "Bearer"),
                    "grant_type": "password",
                    "scope": self.scope_password
                }
            else:
                logger.error(f"Password token request failed: {response.status_code}")
                return {
                    "status": "error",
                    "message": f"HTTP {response.status_code}: {response.text}",
                    "status_code": response.status_code,
                    "grant_type": "password"
                }

        except Exception as e:
            logger.error(f"Password token request error: {e}")
            return {
                "status": "error",
                "message": str(e),
                "grant_type": "password"
            }
    
    async def _request_refresh_token(self, refresh_token: str) -> Dict[str, Any]:
        """
        Request new token using refresh token.
        This is an async HTTP call - database storage is handled separately.

        Returns:
            Dictionary with new token information
        """
        try:
            logger.info("Refreshing Bearer token...")

            data = {
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
                "client_id": self.client_id,
                "scope": self.scope_password
            }

            if self.client_secret:
                data["client_secret"] = self.client_secret

            client = await HTTPClientManager.get_general_client()
            response = await client.post(
                self.token_url,
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=10.0
            )

            if response.status_code == 200:
                token_data = response.json()
                expires_in = token_data.get("expires_in", 3600)

                logger.info(f"Bearer token refreshed successfully (expires in {expires_in}s)")

                return {
                    "status": "success",
                    "access_token": token_data.get("access_token"),
                    "refresh_token": token_data.get("refresh_token", refresh_token),
                    "expires_in": expires_in,
                    "grant_type": "refresh_token",
                    "scope": self.scope_password
                }
            else:
                logger.error(f"Token refresh failed: {response.status_code}")
                return {
                    "status": "error",
                    "message": f"HTTP {response.status_code}: {response.text}",
                    "grant_type": "refresh_token"
                }

        except Exception as e:
            logger.error(f"Token refresh error: {e}")
            return {
                "status": "error",
                "message": str(e),
                "grant_type": "refresh_token"
            }

    async def _request_new_token(self) -> Dict[str, Any]:
        """
        Request a new token using the best available method (async).
        Tries client_credentials first, then falls back to password grant.

        Returns:
            Dictionary with token information
        """
        # Try client_credentials first if we have a client_secret
        if self.client_secret:
            result = await self._request_token_with_client_credentials()
            if result["status"] == "success":
                return result
            logger.warning("Client credentials failed, trying password grant...")

        # Fall back to password grant if we have username/password
        if self.username and self.password:
            return await self._request_token_with_password()

        return {
            "status": "error",
            "message": "No valid authentication method available. Configure either client_secret or username/password."
        }

    # ==================== ASYNC DATABASE METHODS ====================

    async def _load_token_from_db(self, db) -> bool:
        """Load token from database into memory cache"""
        from database.services.oauth_token_service import OAuthTokenService

        token = await OAuthTokenService.get_token(db, SERVICE_NAME)
        if token:
            self._access_token = token.access_token
            self._refresh_token = token.refresh_token
            self._token_expires_at = token.expires_at.timestamp()
            self._token_loaded = True
            logger.info(f"✅ Loaded Epicor token from database (expires at {token.expires_at})")
            return True
        return False

    async def _save_token_to_db(self, db, token_result: Dict[str, Any]) -> bool:
        """Save token to database and update memory cache"""
        from database.services.oauth_token_service import OAuthTokenService

        try:
            token = await OAuthTokenService.save_token(
                db=db,
                service_name=SERVICE_NAME,
                access_token=token_result["access_token"],
                expires_in=token_result["expires_in"],
                refresh_token=token_result.get("refresh_token"),
                token_type=token_result.get("token_type", "Bearer"),
                obtained_via=token_result.get("grant_type"),
                scope=token_result.get("scope"),
            )

            # Update memory cache
            self._access_token = token.access_token
            self._refresh_token = token.refresh_token
            self._token_expires_at = token.expires_at.timestamp()
            self._token_loaded = True

            logger.info(f"✅ Saved Epicor token to database (expires at {token.expires_at})")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to save token to database: {e}")
            return False

    async def get_valid_token_async(self, db) -> Optional[str]:
        """
        Get a valid Bearer token (async version with database support).
        Automatically loads from DB, refreshes if needed.

        Args:
            db: AsyncSession - database session

        Returns:
            Valid Bearer token or None
        """
        if not self.auto_token_enabled:
            logger.warning("Auto-token disabled - no credentials configured")
            return None

        # Load from database if not already loaded
        if not self._token_loaded:
            await self._load_token_from_db(db)

        # Check if token exists and is not expired (with 5 minute buffer)
        if self._access_token and time.time() < (self._token_expires_at - 300):
            return self._access_token

        # Token expired or doesn't exist
        logger.info("Token expired or missing, obtaining new token...")

        # Try to refresh if we have a refresh token
        if self._refresh_token:
            result = await self._request_refresh_token(self._refresh_token)
            if result["status"] == "success":
                await self._save_token_to_db(db, result)
                return self._access_token

        # Get new token
        result = await self._request_new_token()
        if result["status"] == "success":
            await self._save_token_to_db(db, result)
            return self._access_token

        logger.error("Failed to obtain valid token")
        return None

    async def initialize_token_async(self, db) -> bool:
        """
        Initialize token on application startup.
        Loads existing token from DB or obtains a new one.

        Args:
            db: AsyncSession - database session

        Returns:
            True if a valid token is available
        """
        logger.info("Initializing Epicor OAuth token...")

        if not self.auto_token_enabled:
            logger.warning("Auto-token disabled - no credentials configured")
            return False

        # Try to load existing token from database
        if await self._load_token_from_db(db):
            # Check if loaded token is still valid
            if time.time() < (self._token_expires_at - 300):
                logger.info("Existing token is valid")
                return True
            else:
                logger.info("Existing token expired, refreshing...")

        # Get new token
        result = await self._request_new_token()
        if result["status"] == "success":
            await self._save_token_to_db(db, result)
            return True

        logger.error("Failed to initialize Epicor token")
        return False

    async def get_token_info_async(self, db) -> Dict[str, Any]:
        """Get information about current token (async)"""
        from database.services.oauth_token_service import OAuthTokenService

        info = await OAuthTokenService.get_token_info(db, SERVICE_NAME)
        if info:
            return info
        return {
            "status": "no_token",
            "message": "No token available in database"
        }

    # ==================== ASYNC WRAPPER (NO DB) ====================

    async def get_valid_token(self) -> Optional[str]:
        """
        Get a valid token without database access.
        Uses the in-memory cache only.

        For database-backed token management, use get_valid_token_async().

        Returns:
            Valid Bearer token or None
        """
        if not self.auto_token_enabled:
            return None

        # Check if token exists and is not expired (with 5 minute buffer)
        if self._access_token and time.time() < (self._token_expires_at - 300):
            return self._access_token

        # Token expired or doesn't exist - try to get new one
        logger.info("Token expired or missing, obtaining new token...")
        result = await self._request_new_token()

        if result["status"] == "success":
            # Update memory cache only (no DB in this mode)
            self._access_token = result["access_token"]
            self._refresh_token = result.get("refresh_token")
            self._token_expires_at = time.time() + result.get("expires_in", 3600)
            return self._access_token

        logger.error("Failed to obtain valid token")
        return None

    def is_token_valid(self) -> bool:
        """Check if current cached token is valid"""
        if not self._access_token:
            return False
        return time.time() < (self._token_expires_at - 300)

    def get_token_info(self) -> Dict[str, Any]:
        """Get information about current cached token"""
        if not self._access_token:
            return {
                "status": "no_token",
                "message": "No token available"
            }

        time_remaining = self._token_expires_at - time.time()

        return {
            "status": "valid" if self.is_token_valid() else "expired",
            "expires_in": max(0, int(time_remaining)),
            "expires_at": self._token_expires_at,
            "has_refresh_token": bool(self._refresh_token)
        }


# Global instance
epicor_auth = EpicorAuthService()

