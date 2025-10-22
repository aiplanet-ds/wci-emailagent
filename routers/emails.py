"""
Email API Router
Handles all email-related API endpoints for the Price-Change Inbox Dashboard
"""
from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import JSONResponse
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
import json
import os
from pathlib import Path
from datetime import datetime

from services.email_state_service import email_state_service
from services.validation_service import validation_service
from services.epicor_service import EpicorAPIService
from auth.multi_graph import MultiUserGraphClient
from extractor import generate_followup_email


router = APIRouter(prefix="/api/emails", tags=["emails"])


# Pydantic models for request/response
class EmailStateUpdate(BaseModel):
    processed: Optional[bool] = None


class FollowupRequest(BaseModel):
    missing_fields: List[Dict[str, Any]]


class EmailListResponse(BaseModel):
    emails: List[Dict[str, Any]]
    total: int


class EmailDetailResponse(BaseModel):
    email_data: Dict[str, Any]
    state: Dict[str, Any]
    validation: Dict[str, Any]
    epicor_status: Optional[Dict[str, Any]] = None


# Helper functions
def get_user_from_session(request: Request) -> str:
    """Get authenticated user email from session"""
    # Check both 'user' and 'user_email' for backwards compatibility
    user_email = request.session.get("user_email") or request.session.get("user")
    if not user_email:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user_email


def get_user_outputs_directory(user_email: str) -> str:
    """Get the outputs directory for a specific user"""
    safe_email = user_email.replace("@", "_at_").replace(".", "_dot_")
    outputs_dir = f"outputs/{safe_email}"
    return outputs_dir


def load_email_json(file_path: str) -> Dict[str, Any]:
    """Load email data from JSON file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load email data: {str(e)}")


def extract_message_id_from_filename(filename: str) -> str:
    """Extract message ID from price_change_<message_id>.json filename"""
    if filename.startswith("price_change_") and filename.endswith(".json"):
        return filename[len("price_change_"):-len(".json")]
    return filename


def get_all_price_change_emails(user_email: str) -> List[Dict[str, Any]]:
    """
    Get all price change emails from JSON files and Graph API

    Returns list of emails with metadata, state, and validation info
    """
    emails = []
    outputs_dir = get_user_outputs_directory(user_email)

    # Check if outputs directory exists
    if os.path.exists(outputs_dir):
        # Load from JSON files
        for filename in os.listdir(outputs_dir):
            if filename.startswith("price_change_") and filename.endswith(".json"):
                file_path = os.path.join(outputs_dir, filename)

                try:
                    email_data = load_email_json(file_path)
                    message_id = extract_message_id_from_filename(filename)

                    # Get state and validation
                    state = email_state_service.get_email_state(message_id)
                    validation = validation_service.validate_email_data(email_data)

                    # Build email summary
                    email_metadata = email_data.get("email_metadata", {})
                    supplier_info = email_data.get("supplier_info", {})

                    # Check for epicor update status
                    epicor_file = os.path.join(outputs_dir, f"epicor_update_{message_id}.json")
                    epicor_status = None
                    if os.path.exists(epicor_file):
                        try:
                            with open(epicor_file, 'r') as f:
                                epicor_status = json.load(f)
                        except:
                            pass

                    emails.append({
                        "message_id": message_id,
                        "subject": email_metadata.get("subject", "No Subject"),
                        "sender": email_metadata.get("sender", "Unknown"),
                        "date": email_metadata.get("date", None),
                        "supplier_name": supplier_info.get("supplier_name", "Unknown"),
                        "is_price_change": validation.get("is_price_change", True),
                        "processed": state.get("processed", False),
                        "needs_info": validation.get("needs_info", False),
                        "missing_fields_count": len(validation.get("all_missing_fields", [])),
                        "products_count": len(email_data.get("affected_products", [])),
                        "has_epicor_sync": epicor_status is not None,
                        "epicor_success_count": epicor_status.get("successful", 0) if epicor_status else 0,
                        "file_path": file_path
                    })
                except Exception as e:
                    print(f"Error loading email {filename}: {str(e)}")
                    continue

    # Sort by date (newest first)
    emails.sort(key=lambda x: x.get("date") or "", reverse=True)

    return emails


@router.get("", response_model=EmailListResponse)
async def list_emails(
    request: Request,
    filter: Optional[str] = None,  # all, price_change, non_price_change, processed, unprocessed
    search: Optional[str] = None
):
    """
    Get list of all emails for the authenticated user

    Query params:
    - filter: all, price_change, non_price_change, processed, unprocessed
    - search: search by subject or sender
    """
    user_email = get_user_from_session(request)
    emails = get_all_price_change_emails(user_email)

    # Apply filters
    if filter == "price_change":
        emails = [e for e in emails if e.get("is_price_change")]
    elif filter == "non_price_change":
        emails = [e for e in emails if not e.get("is_price_change")]
    elif filter == "processed":
        emails = [e for e in emails if e.get("processed")]
    elif filter == "unprocessed":
        emails = [e for e in emails if not e.get("processed")]

    # Apply search
    if search:
        search_lower = search.lower()
        emails = [
            e for e in emails
            if search_lower in e.get("subject", "").lower()
            or search_lower in e.get("sender", "").lower()
            or search_lower in e.get("supplier_name", "").lower()
        ]

    return EmailListResponse(emails=emails, total=len(emails))


@router.get("/{message_id}", response_model=EmailDetailResponse)
async def get_email_detail(message_id: str, request: Request):
    """Get detailed information for a specific email"""
    user_email = get_user_from_session(request)
    outputs_dir = get_user_outputs_directory(user_email)

    # Load email data
    email_file = os.path.join(outputs_dir, f"price_change_{message_id}.json")
    if not os.path.exists(email_file):
        raise HTTPException(status_code=404, detail="Email not found")

    email_data = load_email_json(email_file)

    # Get state
    state = email_state_service.get_email_state(message_id)

    # Validate data
    validation = validation_service.validate_email_data(email_data)

    # Check epicor sync status
    epicor_file = os.path.join(outputs_dir, f"epicor_update_{message_id}.json")
    epicor_status = None
    if os.path.exists(epicor_file):
        try:
            with open(epicor_file, 'r') as f:
                epicor_status = json.load(f)
        except:
            pass

    return EmailDetailResponse(
        email_data=email_data,
        state=state,
        validation=validation,
        epicor_status=epicor_status
    )


@router.patch("/{message_id}")
async def update_email_state(
    message_id: str,
    update: EmailStateUpdate,
    request: Request,
    force: bool = False
):
    """
    Update email state (e.g., mark as processed)

    When marking as processed, this will:
    1. Validate required fields are present
    2. If warnings exist and force=False, return needs_confirmation
    3. Sync to Epicor if valid (or if force=True)
    4. Update state

    Query params:
    - force: Set to true to bypass warnings and proceed with sync
    """
    user_email = get_user_from_session(request)
    outputs_dir = get_user_outputs_directory(user_email)

    # Load email data
    email_file = os.path.join(outputs_dir, f"price_change_{message_id}.json")
    if not os.path.exists(email_file):
        raise HTTPException(status_code=404, detail="Email not found")

    email_data = load_email_json(email_file)

    # If marking as processed, validate and sync to Epicor
    if update.processed is True:
        # Check if can sync to Epicor
        sync_check = validation_service.can_sync_to_epicor(email_data)

        # Block if there are critical issues
        if not sync_check["can_sync"]:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "Cannot sync to Epicor - missing critical fields",
                    "blockers": sync_check["blockers"]
                }
            )

        # If there are warnings and user hasn't confirmed, ask for confirmation
        if sync_check["warnings"] and not force:
            return {
                "success": False,
                "needs_confirmation": True,
                "warnings": sync_check["warnings"],
                "message": "Some recommended fields are missing. Do you want to proceed anyway?"
            }

        # Sync to Epicor
        try:
            epicor_service = EpicorAPIService()
            supplier_info = email_data.get("supplier_info", {})
            price_summary = email_data.get("price_change_summary", {})
            affected_products = email_data.get("affected_products", [])

            # Perform batch update
            epicor_result = epicor_service.batch_update_prices(
                products=affected_products,
                supplier_id=supplier_info.get("supplier_id"),
                effective_date=price_summary.get("effective_date")
            )

            # Save epicor result
            epicor_file = os.path.join(outputs_dir, f"epicor_update_{message_id}.json")
            with open(epicor_file, 'w') as f:
                json.dump(epicor_result, f, indent=2)

            # Mark as processed and epicor synced
            state = email_state_service.mark_as_processed(message_id, user_email)
            email_state_service.mark_as_epicor_synced(message_id)

            return {
                "success": True,
                "state": state,
                "epicor_result": epicor_result,
                "warnings_bypassed": sync_check["warnings"] if force else []
            }

        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to sync to Epicor: {str(e)}"
            )

    elif update.processed is False:
        # Mark as unprocessed
        state = email_state_service.mark_as_unprocessed(message_id)
        return {"success": True, "state": state}

    else:
        raise HTTPException(status_code=400, detail="Invalid update data")


@router.post("/{message_id}/followup")
async def generate_followup(
    message_id: str,
    followup_request: FollowupRequest,
    request: Request
):
    """Generate AI follow-up email draft for missing information"""
    user_email = get_user_from_session(request)
    outputs_dir = get_user_outputs_directory(user_email)

    # Load email data
    email_file = os.path.join(outputs_dir, f"price_change_{message_id}.json")
    if not os.path.exists(email_file):
        raise HTTPException(status_code=404, detail="Email not found")

    email_data = load_email_json(email_file)

    # Validate missing fields list
    if not followup_request.missing_fields or len(followup_request.missing_fields) == 0:
        raise HTTPException(
            status_code=400,
            detail="At least one missing field must be selected"
        )

    try:
        # Generate follow-up email
        followup_draft = generate_followup_email(
            email_data=email_data,
            missing_fields=followup_request.missing_fields
        )

        # Save the draft to state
        email_state_service.save_followup_draft(message_id, followup_draft)
        email_state_service.set_missing_fields(
            message_id,
            [f['field'] for f in followup_request.missing_fields]
        )

        return {
            "success": True,
            "followup_draft": followup_draft,
            "generated_at": datetime.utcnow().isoformat()
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate follow-up email: {str(e)}"
        )
