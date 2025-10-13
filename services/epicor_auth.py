"""
Epicor OAuth Authentication Service
Automatically generates and refreshes Bearer tokens
"""

import os
import requests
import time
from typing import Dict, Any, Optional
from dotenv import load_dotenv, set_key
import logging

load_dotenv()

logger = logging.getLogger(__name__)


class EpicorAuthService:
    """Service for managing Epicor OAuth authentication"""
    
    def __init__(self):
        """Initialize Epicor OAuth service"""
        # OAuth Configuration
        self.token_url = "https://login.epicor.com/connect/token"
        self.client_id = os.getenv("EPICOR_CLIENT_ID", "f4471628-2e91-4a29-bdac-0aa6e4dad31f")
        self.client_secret = os.getenv("EPICOR_CLIENT_SECRET", "")
        self.username = os.getenv("EPICOR_USERNAME", "abhijit.kumar@akkodisgroup.com")
        self.password = os.getenv("EPICOR_PASSWORD", "")
        self.company_id = os.getenv("EPICOR_COMPANY_ID", "165122")
        self.scope = "openid email epicor_erp"

        # Check if auto-token generation is enabled
        self.auto_token_enabled = os.getenv("EPICOR_AUTO_TOKEN", "false").lower() == "true"

        # Token storage
        self.access_token = None
        self.refresh_token = None
        self.token_expires_at = 0

        if self.auto_token_enabled:
            logger.info("✅ Epicor OAuth Service initialized (auto-token enabled)")
        else:
            logger.info("✅ Epicor OAuth Service initialized (using manual token from .env)")
    
    def get_token_with_password(self) -> Dict[str, Any]:
        """
        Get Bearer token using username/password (Resource Owner Password Credentials Grant)
        
        Returns:
            Dictionary with token information
        """
        try:
            logger.info("🔐 Requesting Bearer token with username/password...")
            
            # Prepare token request
            data = {
                "grant_type": "password",
                "username": self.username,
                "password": self.password,
                "client_id": self.client_id,
                "scope": self.scope
            }
            
            # Add client_secret if available
            if self.client_secret:
                data["client_secret"] = self.client_secret
            
            # Request token
            response = requests.post(
                self.token_url,
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=10
            )
            
            if response.status_code == 200:
                token_data = response.json()
                
                # Store tokens
                self.access_token = token_data.get("access_token")
                self.refresh_token = token_data.get("refresh_token")
                expires_in = token_data.get("expires_in", 3600)
                self.token_expires_at = time.time() + expires_in
                
                # Update .env file
                self._update_env_token(self.access_token)
                
                logger.info(f"✅ Bearer token obtained successfully (expires in {expires_in}s)")
                
                return {
                    "status": "success",
                    "access_token": self.access_token,
                    "refresh_token": self.refresh_token,
                    "expires_in": expires_in,
                    "token_type": token_data.get("token_type", "Bearer")
                }
            else:
                logger.error(f"❌ Token request failed: {response.status_code}")
                return {
                    "status": "error",
                    "message": f"HTTP {response.status_code}: {response.text}",
                    "status_code": response.status_code
                }
                
        except Exception as e:
            logger.error(f"❌ Token request error: {e}")
            return {
                "status": "error",
                "message": str(e)
            }
    
    def refresh_access_token(self) -> Dict[str, Any]:
        """
        Refresh the Bearer token using refresh token
        
        Returns:
            Dictionary with new token information
        """
        if not self.refresh_token:
            logger.warning("⚠️ No refresh token available, requesting new token...")
            return self.get_token_with_password()
        
        try:
            logger.info("🔄 Refreshing Bearer token...")
            
            # Prepare refresh request
            data = {
                "grant_type": "refresh_token",
                "refresh_token": self.refresh_token,
                "client_id": self.client_id,
                "scope": self.scope
            }
            
            # Add client_secret if available
            if self.client_secret:
                data["client_secret"] = self.client_secret
            
            # Request new token
            response = requests.post(
                self.token_url,
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=10
            )
            
            if response.status_code == 200:
                token_data = response.json()
                
                # Update tokens
                self.access_token = token_data.get("access_token")
                self.refresh_token = token_data.get("refresh_token", self.refresh_token)
                expires_in = token_data.get("expires_in", 3600)
                self.token_expires_at = time.time() + expires_in
                
                # Update .env file
                self._update_env_token(self.access_token)
                
                logger.info(f"✅ Bearer token refreshed successfully (expires in {expires_in}s)")
                
                return {
                    "status": "success",
                    "access_token": self.access_token,
                    "refresh_token": self.refresh_token,
                    "expires_in": expires_in
                }
            else:
                logger.error(f"❌ Token refresh failed: {response.status_code}")
                # Try getting new token with password
                return self.get_token_with_password()
                
        except Exception as e:
            logger.error(f"❌ Token refresh error: {e}")
            return {
                "status": "error",
                "message": str(e)
            }
    
    def get_valid_token(self) -> Optional[str]:
        """
        Get a valid Bearer token (refresh if expired)

        Returns:
            Valid Bearer token or None
        """
        # If auto-token is disabled, return None (will use manual token from .env)
        if not self.auto_token_enabled:
            return None

        # Check if token exists and is not expired
        if self.access_token and time.time() < (self.token_expires_at - 300):
            # Token is valid (with 5 minute buffer)
            return self.access_token

        # Token expired or doesn't exist, get new one
        logger.info("⏰ Token expired or missing, obtaining new token...")
        result = self.get_token_with_password()

        if result["status"] == "success":
            return result["access_token"]
        else:
            logger.error("❌ Failed to obtain valid token")
            return None
    
    def _update_env_token(self, token: str):
        """Update Bearer token in .env file"""
        try:
            env_path = ".env"
            set_key(env_path, "EPICOR_BEARER_TOKEN", token)
            logger.info("✅ Bearer token updated in .env file")
        except Exception as e:
            logger.warning(f"⚠️ Could not update .env file: {e}")
    
    def is_token_valid(self) -> bool:
        """Check if current token is valid"""
        if not self.access_token:
            return False
        
        # Check if token is expired (with 5 minute buffer)
        return time.time() < (self.token_expires_at - 300)
    
    def get_token_info(self) -> Dict[str, Any]:
        """Get information about current token"""
        if not self.access_token:
            return {
                "status": "no_token",
                "message": "No token available"
            }
        
        time_remaining = self.token_expires_at - time.time()
        
        return {
            "status": "valid" if self.is_token_valid() else "expired",
            "expires_in": max(0, int(time_remaining)),
            "expires_at": self.token_expires_at,
            "has_refresh_token": bool(self.refresh_token)
        }


# Global instance
epicor_auth = EpicorAuthService()

