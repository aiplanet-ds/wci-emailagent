import httpx
import logging
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional
from auth.oauth import multi_auth
from utils.http_client import HTTPClientManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

GRAPH_BASE = "https://graph.microsoft.com/v1.0"

class MultiUserGraphClient:
    def __init__(self):
        self.auth = multi_auth

    def _get_headers(self, user_email: str) -> Dict[str, str]:
        """Get authorization headers for user"""
        token = self.auth.get_user_token(user_email)
        if not token:
            raise ValueError(f"No valid token for user {user_email}")
        logger.debug(f"Using token for {user_email}: {token[:50]}...")
        return {"Authorization": f"Bearer {token}"}

    async def get_user_messages(self, user_email: str, top: int = 10) -> List[Dict[str, Any]]:
        """Get messages for specific user"""
        headers = self._get_headers(user_email)
        url = f"{GRAPH_BASE}/me/messages"
        params = {
            "$top": top,
            "$select": "id,subject,body,from,receivedDateTime,hasAttachments,isRead,conversationId,conversationIndex"
        }

        logger.debug(f"Fetching messages for {user_email}")
        logger.debug(f"   URL: {url}")

        client = await HTTPClientManager.get_graph_client()
        response = await client.get(url, headers=headers, params=params)

        if response.status_code != 200:
            logger.error(f"Graph API error: {response.status_code}")
            logger.error(f"   Response: {response.text[:500]}")

        response.raise_for_status()
        return response.json().get("value", [])

    async def get_user_message_by_id(self, user_email: str, message_id: str) -> Dict[str, Any]:
        """Get specific message for user"""
        headers = self._get_headers(user_email)
        url = f"{GRAPH_BASE}/me/messages/{message_id}"

        client = await HTTPClientManager.get_graph_client()
        response = await client.get(url, headers=headers)
        response.raise_for_status()
        return response.json()

    async def get_user_message_attachments(self, user_email: str, message_id: str) -> List[Dict[str, Any]]:
        """Get attachments for specific message"""
        headers = self._get_headers(user_email)
        url = f"{GRAPH_BASE}/me/messages/{message_id}/attachments"

        client = await HTTPClientManager.get_graph_client()
        response = await client.get(url, headers=headers)
        response.raise_for_status()
        return response.json().get("value", [])

    async def get_user_profile(self, user_email: str) -> Dict[str, Any]:
        """Get user profile information"""
        headers = self._get_headers(user_email)
        url = f"{GRAPH_BASE}/me"

        client = await HTTPClientManager.get_graph_client()
        response = await client.get(url, headers=headers)
        response.raise_for_status()
        return response.json()

    async def get_user_delta_messages(self, user_email: str, delta_token: Optional[str] = None) -> Dict[str, Any]:
        """Get delta messages for user - tracks changes since last query"""
        headers = self._get_headers(user_email)
        client = await HTTPClientManager.get_graph_client()

        if delta_token:
            # Use existing delta token to get changes
            url = delta_token
            response = await client.get(url, headers=headers)
        else:
            # Initial delta query - use inbox folder delta for better compatibility
            # Include threading fields: conversationId, conversationIndex
            # Limit initial sync to last 14 days to avoid overwhelming the system
            # with a full mailbox fetch for new users
            cutoff_date = (datetime.now(timezone.utc) - timedelta(days=14)).strftime("%Y-%m-%dT%H:%M:%SZ")
            url = f"{GRAPH_BASE}/me/mailFolders/inbox/messages/delta"
            params = {
                "$select": "id,subject,body,from,receivedDateTime,hasAttachments,isRead,conversationId,conversationIndex",
                "$filter": f"receivedDateTime ge {cutoff_date}"
            }
            logger.info(f"Initial delta sync for {user_email}: fetching emails from last 14 days (since {cutoff_date})")
            response = await client.get(url, headers=headers, params=params)

        response.raise_for_status()
        data = response.json()

        # Extract messages and next delta link
        messages = data.get("value", [])
        delta_link = None

        # Look for delta link in @odata.deltaLink or @odata.nextLink
        if "@odata.deltaLink" in data:
            delta_link = data["@odata.deltaLink"]
        elif "@odata.nextLink" in data:
            delta_link = data["@odata.nextLink"]

        return {
            "messages": messages,
            "delta_token": delta_link
        }

    def is_user_authenticated(self, user_email: str) -> bool:
        """Check if user has valid authentication"""
        try:
            token = self.auth.get_user_token(user_email)
            return token is not None
        except Exception:
            return False

# Global instance
graph_client = MultiUserGraphClient()

# Backward compatibility functions for existing code
def get_token():
    """Backward compatibility - will need user context"""
    raise NotImplementedError("Use MultiUserGraphClient for new multi-user system")

def get_message_by_id(message_id: str):
    """Backward compatibility - will need user context"""
    raise NotImplementedError("Use MultiUserGraphClient.get_user_message_by_id with user_email")

def get_messages(top: int = 5):
    """Backward compatibility - will need user context"""
    raise NotImplementedError("Use MultiUserGraphClient.get_user_messages with user_email")

def get_attachments(message_id: str):
    """Backward compatibility - will need user context"""
    raise NotImplementedError("Use MultiUserGraphClient.get_user_message_attachments with user_email")