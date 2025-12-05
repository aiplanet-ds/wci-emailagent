"""OAuth Token service for managing external API tokens"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import OAuthToken


class OAuthTokenService:
    """Service for managing OAuth tokens in the database"""

    # Service name constants
    SERVICE_EPICOR = "epicor"
    
    @staticmethod
    async def get_token(db: AsyncSession, service_name: str) -> Optional[OAuthToken]:
        """Get OAuth token for a service"""
        result = await db.execute(
            select(OAuthToken).where(OAuthToken.service_name == service_name)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_valid_token(
        db: AsyncSession, 
        service_name: str,
        buffer_minutes: int = 5
    ) -> Optional[str]:
        """
        Get a valid (non-expired) access token for a service.
        Returns None if token doesn't exist or will expire within buffer_minutes.
        """
        token = await OAuthTokenService.get_token(db, service_name)
        if not token:
            return None
        
        # Check if token is expired or will expire soon
        expiry_threshold = datetime.utcnow() + timedelta(minutes=buffer_minutes)
        if token.expires_at <= expiry_threshold:
            return None
        
        return token.access_token

    @staticmethod
    async def save_token(
        db: AsyncSession,
        service_name: str,
        access_token: str,
        expires_in: int,
        refresh_token: Optional[str] = None,
        token_type: str = "Bearer",
        obtained_via: Optional[str] = None,
        scope: Optional[str] = None,
    ) -> OAuthToken:
        """
        Save or update an OAuth token for a service.
        
        Args:
            service_name: Service identifier (e.g., 'epicor')
            access_token: The access token string
            expires_in: Token lifetime in seconds
            refresh_token: Optional refresh token
            token_type: Token type (usually 'Bearer')
            obtained_via: How the token was obtained (e.g., 'client_credentials')
            scope: OAuth scope used
        """
        result = await db.execute(
            select(OAuthToken).where(OAuthToken.service_name == service_name)
        )
        token = result.scalar_one_or_none()
        
        expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
        
        if token:
            # Update existing token
            token.access_token = access_token
            token.refresh_token = refresh_token
            token.token_type = token_type
            token.expires_at = expires_at
            token.obtained_via = obtained_via
            token.scope = scope
            token.updated_at = datetime.utcnow()
        else:
            # Create new token
            token = OAuthToken(
                service_name=service_name,
                access_token=access_token,
                refresh_token=refresh_token,
                token_type=token_type,
                expires_at=expires_at,
                obtained_via=obtained_via,
                scope=scope,
            )
            db.add(token)
        
        await db.flush()
        await db.refresh(token)
        return token

    @staticmethod
    async def delete_token(db: AsyncSession, service_name: str) -> bool:
        """Delete OAuth token for a service"""
        result = await db.execute(
            select(OAuthToken).where(OAuthToken.service_name == service_name)
        )
        token = result.scalar_one_or_none()
        
        if not token:
            return False
        
        await db.delete(token)
        await db.flush()
        return True

    @staticmethod
    async def is_token_expired(
        db: AsyncSession, 
        service_name: str,
        buffer_minutes: int = 5
    ) -> bool:
        """
        Check if token is expired or will expire within buffer_minutes.
        Returns True if token doesn't exist, is expired, or will expire soon.
        """
        token = await OAuthTokenService.get_token(db, service_name)
        if not token:
            return True
        
        expiry_threshold = datetime.utcnow() + timedelta(minutes=buffer_minutes)
        return token.expires_at <= expiry_threshold

    @staticmethod
    async def get_token_info(db: AsyncSession, service_name: str) -> Optional[Dict[str, Any]]:
        """Get token info as dictionary (for debugging/logging)"""
        token = await OAuthTokenService.get_token(db, service_name)
        if not token:
            return None
        
        return {
            "service_name": token.service_name,
            "token_type": token.token_type,
            "expires_at": token.expires_at.isoformat(),
            "is_expired": token.is_expired,
            "expires_soon": token.expires_soon,
            "obtained_via": token.obtained_via,
            "scope": token.scope,
            "created_at": token.created_at.isoformat(),
            "updated_at": token.updated_at.isoformat(),
        }

