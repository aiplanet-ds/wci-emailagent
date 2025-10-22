"""
Dashboard Statistics Service
Aggregates and computes dashboard statistics for email processing
"""
import json
import os
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from pathlib import Path
from services.email_state_service import email_state_service


class DashboardService:
    """Manages dashboard statistics aggregation"""

    def __init__(self, outputs_dir: str = "outputs"):
        self.outputs_dir = outputs_dir
        self.email_state_service = email_state_service

    def _parse_date(self, date_str: Optional[str]) -> Optional[datetime]:
        """Parse ISO format date string to datetime"""
        if not date_str:
            return None
        try:
            return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        except (ValueError, AttributeError):
            return None

    def _get_user_email_files(self, user_email: str) -> List[Path]:
        """Get all email JSON files for a specific user"""
        safe_email = user_email.replace('@', '_at_').replace('.', '_dot_')
        user_dir = Path(self.outputs_dir) / safe_email

        if not user_dir.exists():
            return []

        return list(user_dir.glob("price_change_*.json"))

    def _load_email_data(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """Load email data from JSON file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return None

    def _load_epicor_results(self, user_email: str, message_id: str) -> Optional[Dict[str, Any]]:
        """Load Epicor sync results for a specific email"""
        safe_email = user_email.replace('@', '_at_').replace('.', '_dot_')
        epicor_file = Path(self.outputs_dir) / safe_email / f"epicor_update_{message_id}.json"

        if not epicor_file.exists():
            return None

        try:
            with open(epicor_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return None

    def _is_within_date_range(
        self,
        email_date: Optional[datetime],
        start_date: Optional[datetime],
        end_date: Optional[datetime]
    ) -> bool:
        """Check if email date falls within the specified range"""
        if not email_date:
            return True  # Include emails without dates

        if start_date and email_date < start_date:
            return False

        if end_date and email_date > end_date:
            return False

        return True

    def get_user_stats(
        self,
        user_email: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get comprehensive dashboard statistics for a user

        Args:
            user_email: Email of the user
            start_date: Optional ISO format start date for filtering
            end_date: Optional ISO format end date for filtering

        Returns:
            Dictionary containing all dashboard statistics
        """
        # Parse date filters
        start_dt = self._parse_date(start_date)
        end_dt = self._parse_date(end_date)

        # Get all email states
        all_states = self.email_state_service.get_all_email_states()

        # Get user's email files
        email_files = self._get_user_email_files(user_email)

        # Initialize counters
        stats = {
            "total_emails": 0,
            "processed_count": 0,
            "unprocessed_count": 0,
            "needs_followup_count": 0,
            "price_change_count": 0,
            "non_price_change_count": 0,
            "epicor_sync_success": 0,
            "epicor_sync_failed": 0,
            "epicor_sync_pending": 0,
            "processing_rate": 0.0,
            "emails_with_missing_fields": 0,
            "recent_activity": []
        }

        # Track message IDs we've seen in files
        file_message_ids = set()

        # Process each email file
        for file_path in email_files:
            email_data = self._load_email_data(file_path)
            if not email_data:
                continue

            # Extract message_id and metadata
            message_id = email_data.get("email_metadata", {}).get("message_id")
            if not message_id:
                continue

            file_message_ids.add(message_id)

            # Get email date
            email_date_str = email_data.get("email_metadata", {}).get("date")
            email_date = self._parse_date(email_date_str)

            # Check if within date range
            if not self._is_within_date_range(email_date, start_dt, end_dt):
                continue

            # Get state for this email
            state = all_states.get(message_id, {})

            # Count total emails
            stats["total_emails"] += 1

            # Count processed vs unprocessed
            if state.get("processed", False):
                stats["processed_count"] += 1
            else:
                stats["unprocessed_count"] += 1

            # Count emails needing follow-up
            if state.get("needs_info", False) or len(state.get("selected_missing_fields", [])) > 0:
                stats["needs_followup_count"] += 1
                stats["emails_with_missing_fields"] += 1

            # Count price change classification
            if state.get("is_price_change", False):
                stats["price_change_count"] += 1
            else:
                stats["non_price_change_count"] += 1

            # Check Epicor sync status
            epicor_results = self._load_epicor_results(user_email, message_id)
            if epicor_results:
                successful = epicor_results.get("successful", 0)
                failed = epicor_results.get("failed", 0)

                if successful > 0 and failed == 0:
                    stats["epicor_sync_success"] += 1
                elif failed > 0:
                    stats["epicor_sync_failed"] += 1
            else:
                # No Epicor results file means sync hasn't happened
                if state.get("processed", False):
                    stats["epicor_sync_pending"] += 1

            # Add to recent activity
            if state.get("processed_at"):
                processed_at = self._parse_date(state.get("processed_at"))
                if processed_at:
                    stats["recent_activity"].append({
                        "message_id": message_id,
                        "subject": email_data.get("email_metadata", {}).get("subject", "Unknown"),
                        "processed_at": state.get("processed_at"),
                        "processed_by": state.get("processed_by"),
                        "action": "processed"
                    })

        # Calculate processing rate
        if stats["total_emails"] > 0:
            stats["processing_rate"] = round(
                (stats["processed_count"] / stats["total_emails"]) * 100,
                2
            )

        # Sort recent activity by date (newest first) and limit to 10
        stats["recent_activity"].sort(
            key=lambda x: x["processed_at"] or "",
            reverse=True
        )
        stats["recent_activity"] = stats["recent_activity"][:10]

        # Add percentage calculations
        stats["unprocessed_percentage"] = round(
            (stats["unprocessed_count"] / stats["total_emails"] * 100) if stats["total_emails"] > 0 else 0,
            2
        )

        stats["followup_percentage"] = round(
            (stats["needs_followup_count"] / stats["total_emails"] * 100) if stats["total_emails"] > 0 else 0,
            2
        )

        # Epicor sync success rate
        total_syncs = stats["epicor_sync_success"] + stats["epicor_sync_failed"]
        stats["epicor_success_rate"] = round(
            (stats["epicor_sync_success"] / total_syncs * 100) if total_syncs > 0 else 0,
            2
        )

        return stats


# Global instance
dashboard_service = DashboardService()
