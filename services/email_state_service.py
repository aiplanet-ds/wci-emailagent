"""
Email State Management Service
Manages the state of processed emails, missing fields, and follow-up drafts
"""
import json
import os
from typing import Dict, List, Optional, Any
from datetime import datetime
import asyncio
from pathlib import Path


class EmailStateService:
    """Manages email processing state using JSON file storage"""

    def __init__(self, state_file: str = "data/email_states.json"):
        self.state_file = state_file
        self._ensure_data_directory()
        self._ensure_state_file()

    def _ensure_data_directory(self):
        """Ensure data directory exists"""
        data_dir = os.path.dirname(self.state_file)
        if data_dir and not os.path.exists(data_dir):
            os.makedirs(data_dir)

    def _ensure_state_file(self):
        """Ensure state file exists with initial structure"""
        if not os.path.exists(self.state_file):
            initial_state = {"emails": {}}
            with open(self.state_file, 'w') as f:
                json.dump(initial_state, f, indent=2)

    def _load_state(self) -> Dict:
        """Load state from JSON file"""
        try:
            with open(self.state_file, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {"emails": {}}

    def _save_state(self, state: Dict):
        """Save state to JSON file"""
        with open(self.state_file, 'w') as f:
            json.dump(state, f, indent=2)

    def get_email_state(self, message_id: str) -> Dict[str, Any]:
        """Get state for a specific email"""
        state = self._load_state()
        return state.get("emails", {}).get(message_id, {
            "message_id": message_id,
            "processed": False,
            "is_price_change": False,
            "needs_info": False,
            "selected_missing_fields": [],
            "followup_draft": None,
            "last_updated": None,
            "processed_at": None,
            "processed_by": None
        })

    def update_email_state(
        self,
        message_id: str,
        updates: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update state for a specific email"""
        state = self._load_state()

        if "emails" not in state:
            state["emails"] = {}

        # Get existing email state or create new
        email_state = state["emails"].get(message_id, {
            "message_id": message_id,
            "processed": False,
            "is_price_change": False,
            "needs_info": False,
            "selected_missing_fields": [],
            "followup_draft": None,
            "last_updated": None
        })

        # Update with new values
        email_state.update(updates)
        email_state["last_updated"] = datetime.utcnow().isoformat()

        # Save back
        state["emails"][message_id] = email_state
        self._save_state(state)

        return email_state

    def mark_as_processed(
        self,
        message_id: str,
        user_email: Optional[str] = None
    ) -> Dict[str, Any]:
        """Mark email as processed"""
        return self.update_email_state(message_id, {
            "processed": True,
            "processed_at": datetime.utcnow().isoformat(),
            "processed_by": user_email
        })

    def mark_as_unprocessed(self, message_id: str) -> Dict[str, Any]:
        """Mark email as unprocessed"""
        return self.update_email_state(message_id, {
            "processed": False,
            "processed_at": None,
            "processed_by": None
        })

    def set_missing_fields(
        self,
        message_id: str,
        missing_fields: List[str]
    ) -> Dict[str, Any]:
        """Set missing fields for an email"""
        needs_info = len(missing_fields) > 0
        return self.update_email_state(message_id, {
            "needs_info": needs_info,
            "selected_missing_fields": missing_fields
        })

    def save_followup_draft(
        self,
        message_id: str,
        draft_text: str
    ) -> Dict[str, Any]:
        """Save AI-generated follow-up draft"""
        return self.update_email_state(message_id, {
            "followup_draft": draft_text
        })

    def set_price_change_classification(
        self,
        message_id: str,
        is_price_change: bool
    ) -> Dict[str, Any]:
        """Set whether email is a price change notification"""
        return self.update_email_state(message_id, {
            "is_price_change": is_price_change
        })

    def get_all_email_states(self) -> Dict[str, Dict[str, Any]]:
        """Get all email states"""
        state = self._load_state()
        return state.get("emails", {})

    def delete_email_state(self, message_id: str) -> bool:
        """Delete state for a specific email"""
        state = self._load_state()

        if message_id in state.get("emails", {}):
            del state["emails"][message_id]
            self._save_state(state)
            return True

        return False


# Global instance
email_state_service = EmailStateService()
