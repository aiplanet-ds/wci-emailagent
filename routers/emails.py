"""
Email API Router
Handles all email-related API endpoints for the Price-Change Inbox Dashboard
"""
from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import JSONResponse, Response
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
import json
import os
from pathlib import Path
from datetime import datetime
import base64

# Database imports
from database.config import get_db
from database.services.user_service import UserService
from database.services.email_service import EmailService
from database.services.email_state_service import EmailStateService
from database.services.epicor_sync_result_service import EpicorSyncResultService
from database.services.bom_impact_service import BomImpactService

# Legacy services
from services.validation_service import validation_service
from services.epicor_service import EpicorAPIService
from auth.multi_graph import MultiUserGraphClient
from services.extractor import generate_followup_email
from services.thread_aggregation_service import aggregate_thread_extractions


router = APIRouter(prefix="/api/emails", tags=["emails"])


# Pydantic models for request/response
class EmailStateUpdate(BaseModel):
    processed: Optional[bool] = None


class FollowupRequest(BaseModel):
    missing_fields: List[Dict[str, Any]]


class SendFollowupRequest(BaseModel):
    to_recipients: List[str]
    cc_recipients: Optional[List[str]] = None
    subject: str
    body_html: str


class EmailListResponse(BaseModel):
    emails: List[Dict[str, Any]]
    total: int
    total_threads: int = 0
    page: int = 1
    page_size: int = 15
    total_pages: int = 1
    has_next: bool = False
    has_prev: bool = False


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


async def get_user_from_db(db: AsyncSession, user_email: str):
    """Get user from database, raise 404 if not found"""
    user = await UserService.get_user_by_email(db, user_email)
    if not user:
        raise HTTPException(status_code=404, detail=f"User not found: {user_email}")
    return user


async def get_email_from_db(db: AsyncSession, message_id: str):
    """Get email from database, raise 404 if not found"""
    email = await EmailService.get_email_by_message_id(db, message_id)
    if not email:
        raise HTTPException(status_code=404, detail=f"Email not found: {message_id}")
    return email


def get_user_outputs_directory(user_email: str) -> str:
    """Get the outputs directory for a specific user (legacy function for backwards compatibility)"""
    safe_email = user_email.replace("@", "_at_").replace(".", "_dot_")
    outputs_dir = f"outputs/{safe_email}"
    return outputs_dir


def load_email_json(file_path: str) -> Dict[str, Any]:
    """Load email data from JSON file (legacy function, use database instead)"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load email data: {str(e)}")


def extract_message_id_from_filename(filename: str) -> str:
    """Extract message ID from price_change_<message_id>.json filename (deprecated)"""
    if filename.startswith("price_change_") and filename.endswith(".json"):
        return filename[len("price_change_"):-len(".json")]
    return filename


async def get_all_price_change_emails_from_db(
    db: AsyncSession,
    user_id: int,
    filter_type: Optional[str] = None,
    search: Optional[str] = None,
    page: int = 1,
    page_size: int = 15,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
) -> Dict[str, Any]:
    """
    Get all price change emails from database with optional filtering and thread-level pagination

    Args:
        db: Database session
        user_id: User ID
        filter_type: Filter type (all, processed, unprocessed, pending_verification, etc.)
        search: Search term for subject or sender
        page: Page number (1-indexed)
        page_size: Number of threads per page (default 15)
        start_date: Filter emails from this date
        end_date: Filter emails until this date

    Returns:
        Dict with emails list and pagination metadata
    """
    from sqlalchemy import select, and_, or_, func, distinct
    from database.models import Email, EmailState, EpicorSyncResult
    from sqlalchemy.orm import joinedload

    # Base filter conditions
    base_conditions = [Email.user_id == user_id]

    # Exclude sent emails from inbox list (only show received emails)
    # Sent emails will still appear in thread timeline for full conversation context
    base_conditions.append(Email.is_outgoing == False)

    # Only show main/first emails in inbox (exclude reply emails)
    # Reply emails are visible when viewing the thread detail
    base_conditions.append(or_(Email.is_reply == False, Email.is_reply == None))

    # Apply date range filter
    if start_date:
        base_conditions.append(Email.received_at >= start_date)
    if end_date:
        base_conditions.append(Email.received_at <= end_date)

    # Build base query for filtering
    base_query = select(Email).where(and_(*base_conditions))

    # Apply status filters (requires join with EmailState)
    if filter_type and filter_type != "all":
        base_query = base_query.join(EmailState, Email.id == EmailState.email_id, isouter=True)

        if filter_type == "price_change":
            base_query = base_query.where(EmailState.is_price_change == True)
        elif filter_type == "non_price_change":
            base_query = base_query.where(or_(EmailState.is_price_change == False, EmailState.is_price_change == None))
        elif filter_type == "processed":
            base_query = base_query.where(EmailState.processed == True)
        elif filter_type == "unprocessed":
            base_query = base_query.where(or_(EmailState.processed == False, EmailState.processed == None))
        elif filter_type == "pending_verification":
            base_query = base_query.where(EmailState.verification_status == "pending_review")
        elif filter_type == "rejected":
            base_query = base_query.where(EmailState.verification_status == "rejected")

    # Apply search filter
    if search:
        search_pattern = f"%{search}%"
        base_query = base_query.where(
            or_(
                Email.subject.ilike(search_pattern),
                Email.sender_email.ilike(search_pattern)
            )
        )

    # THREAD-LEVEL PAGINATION
    # Step 1: Get distinct conversation_ids with their latest email date, paginated
    # Use COALESCE to handle NULL conversation_id (treat each as unique thread)
    conversation_query = (
        select(
            func.coalesce(Email.conversation_id, Email.message_id).label('thread_id'),
            func.max(Email.received_at).label('latest_date')
        )
        .where(and_(*base_conditions))
    )

    # Apply same filters to conversation query
    if filter_type and filter_type != "all":
        conversation_query = conversation_query.join(EmailState, Email.id == EmailState.email_id, isouter=True)
        if filter_type == "price_change":
            conversation_query = conversation_query.where(EmailState.is_price_change == True)
        elif filter_type == "non_price_change":
            conversation_query = conversation_query.where(or_(EmailState.is_price_change == False, EmailState.is_price_change == None))
        elif filter_type == "processed":
            conversation_query = conversation_query.where(EmailState.processed == True)
        elif filter_type == "unprocessed":
            conversation_query = conversation_query.where(or_(EmailState.processed == False, EmailState.processed == None))
        elif filter_type == "pending_verification":
            conversation_query = conversation_query.where(EmailState.verification_status == "pending_review")
        elif filter_type == "rejected":
            conversation_query = conversation_query.where(EmailState.verification_status == "rejected")

    if search:
        search_pattern = f"%{search}%"
        conversation_query = conversation_query.where(
            or_(
                Email.subject.ilike(search_pattern),
                Email.sender_email.ilike(search_pattern)
            )
        )

    conversation_query = (
        conversation_query
        .group_by(func.coalesce(Email.conversation_id, Email.message_id))
        .order_by(func.max(Email.received_at).desc())
    )

    # Step 2: Count total threads
    count_subquery = conversation_query.subquery()
    total_threads_result = await db.execute(select(func.count()).select_from(count_subquery))
    total_threads = total_threads_result.scalar() or 0

    # Calculate pagination
    total_pages = max(1, (total_threads + page_size - 1) // page_size)
    page = max(1, min(page, total_pages))  # Clamp page to valid range
    offset = (page - 1) * page_size
    has_next = page < total_pages
    has_prev = page > 1

    # Step 3: Get paginated thread IDs
    paginated_threads_query = conversation_query.offset(offset).limit(page_size)
    paginated_result = await db.execute(paginated_threads_query)
    thread_rows = paginated_result.all()
    thread_ids = [row.thread_id for row in thread_rows]

    # Step 4: Get all emails for these threads
    if thread_ids:
        emails_query = (
            select(Email)
            .where(
                and_(
                    Email.user_id == user_id,
                    or_(
                        Email.conversation_id.in_(thread_ids),
                        Email.message_id.in_(thread_ids)
                    )
                )
            )
            .options(joinedload(Email.email_state))
            .order_by(Email.received_at.desc())
        )

        # Apply date filter to emails as well
        if start_date:
            emails_query = emails_query.where(Email.received_at >= start_date)
        if end_date:
            emails_query = emails_query.where(Email.received_at <= end_date)

        result = await db.execute(emails_query)
        emails_db = result.unique().scalars().all()
    else:
        emails_db = []

    # Build response list
    emails = []
    for email in emails_db:
        state = email.email_state

        # Get Epicor sync result if exists
        epicor_result = await EpicorSyncResultService.get_sync_result_by_email_id(db, email.id)

        # Validate email data only if email has extraction data
        # Skip validation for emails without data (e.g., replies to follow-ups)
        has_extraction_data = (
            email.supplier_info or
            email.price_change_summary or
            email.affected_products
        )

        if has_extraction_data:
            email_dict = {
                "supplier_info": email.supplier_info,
                "price_change_summary": email.price_change_summary,
                "affected_products": email.affected_products,
                "additional_details": email.additional_details
            }
            validation = validation_service.validate_email_data(email_dict)
        else:
            # No extraction data - skip validation
            validation = {"is_valid": True, "needs_info": False, "all_missing_fields": []}

        emails.append({
            "message_id": email.message_id,
            "subject": email.subject or "No Subject",
            "sender": email.sender_email or "Unknown",
            "date": email.received_at.isoformat() if email.received_at else None,
            "supplier_name": email.supplier_info.get("supplier_name") if email.supplier_info else "Unknown",
            "is_price_change": state.is_price_change if state else None,
            "processed": state.processed if state else False,
            "needs_info": validation.get("needs_info", False),
            "missing_fields_count": len(validation.get("all_missing_fields", [])),
            "products_count": len(email.affected_products) if email.affected_products else 0,
            "has_epicor_sync": epicor_result is not None,
            "epicor_success_count": epicor_result.successful_updates if epicor_result else 0,
            "verification_status": state.verification_status if state else None,
            "vendor_verified": state.vendor_verified if state else False,
            "verification_method": state.verification_method if state else None,
            "flagged_reason": state.flagged_reason if state else None,
            "epicor_synced": state.epicor_synced if state else False,
            "llm_detection_performed": state.llm_detection_performed if state else False,
            "received_time": email.received_at.isoformat() if email.received_at else None,
            "email_id": email.id,
            # Threading fields
            "conversation_id": email.conversation_id,
            "conversation_index": email.conversation_index,
            "is_reply": email.is_reply if email.is_reply is not None else False,
            "is_forward": email.is_forward if email.is_forward is not None else False,
            "thread_subject": email.thread_subject,
            # Pinning fields
            "pinned": state.pinned if state and state.pinned else False,
            "pinned_at": state.pinned_at.isoformat() if state and state.pinned_at else None,
            # Followup fields
            "followup_sent": state.followup_sent if state and state.followup_sent else False,
            "followup_sent_at": state.followup_sent_at.isoformat() if state and state.followup_sent_at else None,
        })

    return {
        "emails": emails,
        "total": len(emails),
        "total_threads": total_threads,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
        "has_next": has_next,
        "has_prev": has_prev
    }


@router.get("", response_model=EmailListResponse)
async def list_emails(
    request: Request,
    db: AsyncSession = Depends(get_db),
    filter: Optional[str] = None,  # all, price_change, non_price_change, processed, unprocessed, pending_verification, rejected
    search: Optional[str] = None,
    page: int = 1,
    page_size: int = 15,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    """
    Get list of all emails from database for the authenticated user with thread-level pagination

    Query params:
    - filter: all, price_change, non_price_change, processed, unprocessed, pending_verification, rejected
    - search: search by subject or sender
    - page: page number (1-indexed, default 1)
    - page_size: number of threads per page (default 15)
    - start_date: filter emails from this date (ISO format)
    - end_date: filter emails until this date (ISO format)
    """
    user_email = get_user_from_session(request)
    user = await get_user_from_db(db, user_email)

    # Parse date strings to datetime objects
    start_dt = None
    end_dt = None
    if start_date:
        try:
            start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        except ValueError:
            pass
    if end_date:
        try:
            end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
        except ValueError:
            pass

    # Get emails from database with filters and pagination
    result = await get_all_price_change_emails_from_db(
        db=db,
        user_id=user.id,
        filter_type=filter,
        search=search,
        page=page,
        page_size=page_size,
        start_date=start_dt,
        end_date=end_dt
    )

    return EmailListResponse(
        emails=result["emails"],
        total=result["total"],
        total_threads=result["total_threads"],
        page=result["page"],
        page_size=result["page_size"],
        total_pages=result["total_pages"],
        has_next=result["has_next"],
        has_prev=result["has_prev"]
    )


# ============================================================================
# STATIC ROUTES (must be defined BEFORE dynamic /{message_id} routes)
# ============================================================================

@router.get("/pending-verification", response_model=EmailListResponse)
async def list_pending_verification_emails(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Get all emails pending vendor verification"""
    user_email = get_user_from_session(request)
    user = await get_user_from_db(db, user_email)

    # Get all emails with pending_review verification status from database
    # No pagination for pending verification - return all
    result = await get_all_price_change_emails_from_db(
        db=db,
        user_id=user.id,
        filter_type="pending_verification",
        page=1,
        page_size=1000  # Return all pending emails
    )

    return EmailListResponse(
        emails=result["emails"],
        total=result["total"],
        total_threads=result["total_threads"],
        page=result["page"],
        page_size=result["page_size"],
        total_pages=result["total_pages"],
        has_next=result["has_next"],
        has_prev=result["has_prev"]
    )


@router.get("/vendors/cache-status")
async def get_vendor_cache_status(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Get vendor cache information"""
    get_user_from_session(request)  # Verify authentication

    from services.vendor_verification_service import vendor_verification_service

    status = await vendor_verification_service.get_cache_status()
    return status


@router.post("/vendors/refresh-cache")
async def refresh_vendor_cache(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Manually refresh vendor cache from Epicor"""
    get_user_from_session(request)  # Verify authentication

    from services.vendor_verification_service import vendor_verification_service

    try:
        result = await vendor_verification_service.refresh_cache()
        cache_status = await vendor_verification_service.get_cache_status()
        return {
            "success": True,
            "message": "Vendor cache refreshed successfully",
            "cache_status": cache_status
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to refresh vendor cache: {str(e)}"
        )


# ============================================================================
# DYNAMIC ROUTES (with /{message_id} path parameter)
# ============================================================================

@router.get("/{message_id}", response_model=EmailDetailResponse)
async def get_email_detail(
    message_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Get detailed information for a specific email from database"""
    user_email = get_user_from_session(request)
    user = await get_user_from_db(db, user_email)

    # Get email from database
    email = await get_email_from_db(db, message_id)

    # Verify email belongs to user
    if email.user_id != user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Get email state
    state = await EmailStateService.get_state_by_message_id(db, message_id)

    # Get Epicor sync result
    epicor_result = await EpicorSyncResultService.get_sync_result_by_email_id(db, email.id)

    # Build email data response
    email_data = {
        "supplier_info": email.supplier_info or {},
        "price_change_summary": email.price_change_summary or {},
        "affected_products": email.affected_products or [],
        "additional_details": email.additional_details or {},
        "email_metadata": {
            "subject": email.subject,
            "sender": email.sender_email,
            "date": email.received_at.isoformat() if email.received_at else None,
            "message_id": email.message_id,
            "attachments": []
        },
        "is_outgoing": email.is_outgoing or False,
        "is_reply": email.is_reply or False
    }

    # Validate email data
    validation = validation_service.validate_email_data(email_data)

    # Build state response
    state_dict = {
        "processed": state.processed if state else False,
        "epicor_synced": state.epicor_synced if state else False,
        "needs_info": state.needs_info if state else False,
        "selected_missing_fields": state.selected_missing_fields if state else [],
        "followup_draft": state.followup_draft if state else None,
        "verification_status": state.verification_status if state else None,
        "vendor_verified": state.vendor_verified if state else False,
        "verification_method": state.verification_method if state else None,
        "flagged_reason": state.flagged_reason if state else None,
        "is_price_change": state.is_price_change if state else None,
        "llm_confidence": state.llm_confidence if state else None,
        "llm_reasoning": state.llm_reasoning if state else None,
        "pinned": state.pinned if state and state.pinned else False,
        "pinned_at": state.pinned_at.isoformat() if state and state.pinned_at else None,
        "epicor_validation_performed": state.epicor_validation_performed if state else False,
        "epicor_validation_result": state.epicor_validation_result if state else None,
        "followup_sent": state.followup_sent if state and state.followup_sent else False,
        "followup_sent_at": state.followup_sent_at.isoformat() if state and state.followup_sent_at else None,
        "llm_detection_performed": state.llm_detection_performed if state else False
    }

    # Build Epicor status response
    epicor_status = None
    if epicor_result:
        # Extract details from results_summary for frontend compatibility
        results_summary = epicor_result.results_summary or {}
        epicor_status = {
            "successful": epicor_result.successful_updates,
            "failed": epicor_result.failed_updates,
            "total": epicor_result.total_products,
            "skipped": results_summary.get("skipped", 0),
            "status": epicor_result.sync_status,
            "details": results_summary.get("details", []),
            "workflow_used": results_summary.get("workflow_used", ""),
            "synced_at": epicor_result.synced_at.isoformat() if epicor_result.synced_at else None
        }

    return EmailDetailResponse(
        email_data=email_data,
        state=state_dict,
        validation=validation,
        epicor_status=epicor_status
    )


@router.get("/{message_id}/thread")
async def get_email_thread(
    message_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Get all emails in the same conversation thread as the specified email.

    Returns emails sorted by received_at in chronological order.
    """
    user_email = get_user_from_session(request)
    user = await get_user_from_db(db, user_email)

    # Get the email to find its conversation_id
    email = await get_email_from_db(db, message_id)

    # Verify email belongs to user
    if email.user_id != user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    # If no conversation_id, return just this email
    if not email.conversation_id:
        return {
            "conversation_id": None,
            "thread_subject": email.thread_subject or email.subject,
            "emails": [{
                "message_id": email.message_id,
                "subject": email.subject,
                "sender": email.sender_email,
                "received_at": email.received_at.isoformat() if email.received_at else None,
                "verification_status": None,
                "is_reply": email.is_reply or False,
                "is_forward": email.is_forward or False,
                "folder": email.folder or "inbox",
                "is_outgoing": email.is_outgoing or False,
            }],
            "total_count": 1
        }

    # Get all emails in the same conversation thread
    thread_emails = await EmailService.get_emails_by_conversation_id(
        db, email.conversation_id, user.id
    )

    # Get states for all emails in thread
    thread_data = []
    for thread_email in thread_emails:
        state = await EmailStateService.get_state_by_message_id(db, thread_email.message_id)
        thread_data.append({
            "message_id": thread_email.message_id,
            "subject": thread_email.subject,
            "sender": thread_email.sender_email,
            "received_at": thread_email.received_at.isoformat() if thread_email.received_at else None,
            "verification_status": state.verification_status if state else None,
            "is_reply": thread_email.is_reply or False,
            "is_forward": thread_email.is_forward or False,
            "folder": thread_email.folder or "inbox",
            "is_outgoing": thread_email.is_outgoing or False,
        })

    return {
        "conversation_id": email.conversation_id,
        "thread_subject": email.thread_subject or email.subject,
        "emails": thread_data,
        "total_count": len(thread_data)
    }


@router.get("/{message_id}/thread/bom-impact")
async def get_thread_bom_impact(
    message_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Get aggregated BOM impact analysis for all emails in a conversation thread.

    Combines impact data from multiple emails affecting the same parts to show
    cumulative thread-level impact.
    """
    from database.services.bom_impact_service import BomImpactService

    user_email = get_user_from_session(request)
    user = await get_user_from_db(db, user_email)

    # Get the email to find its conversation_id
    email = await get_email_from_db(db, message_id)
    if email.user_id != user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    # If no conversation_id, just return single email's BOM impact
    if not email.conversation_id:
        impacts = await BomImpactService.get_by_email_id(db, email.id)
        return {
            "conversation_id": None,
            "thread_subject": email.thread_subject or email.subject,
            "total_emails": 1,
            "emails_with_bom_data": 1 if impacts else 0,
            "aggregated_impacts": {},
            "total_annual_impact": sum(i.total_annual_cost_impact or 0 for i in impacts),
            "total_parts_affected": len(impacts),
            "impacts_by_email": [{
                "message_id": email.message_id,
                "subject": email.subject,
                "impacts": [BomImpactService.to_dict(i) for i in impacts]
            }]
        }

    # Get all emails in thread
    thread_emails = await EmailService.get_emails_by_conversation_id(
        db, email.conversation_id, user.id
    )

    # Collect BOM impacts from all emails
    impacts_by_email = []
    aggregated_by_part = {}  # part_num -> aggregated data
    total_annual_impact = 0

    for thread_email in thread_emails:
        impacts = await BomImpactService.get_by_email_id(db, thread_email.id)
        if impacts:
            email_impacts = []
            for impact in impacts:
                impact_dict = BomImpactService.to_dict(impact)
                email_impacts.append(impact_dict)
                total_annual_impact += impact.total_annual_cost_impact or 0

                # Aggregate by part number
                part_num = impact.part_num
                if part_num:
                    if part_num not in aggregated_by_part:
                        aggregated_by_part[part_num] = {
                            "part_num": part_num,
                            "product_name": impact.product_name,
                            "emails_count": 0,
                            "total_annual_impact": 0,
                            "total_assemblies_affected": 0,
                            "latest_old_price": None,
                            "latest_new_price": None,
                            "price_updates": [],
                            "approval_status": "pending"
                        }
                    aggregated_by_part[part_num]["emails_count"] += 1
                    aggregated_by_part[part_num]["total_annual_impact"] += impact.total_annual_cost_impact or 0
                    if impact.summary:
                        aggregated_by_part[part_num]["total_assemblies_affected"] = max(
                            aggregated_by_part[part_num]["total_assemblies_affected"],
                            impact.summary.get("total_assemblies_affected", 0) if isinstance(impact.summary, dict) else 0
                        )
                    aggregated_by_part[part_num]["latest_old_price"] = impact.old_price
                    aggregated_by_part[part_num]["latest_new_price"] = impact.new_price
                    aggregated_by_part[part_num]["price_updates"].append({
                        "email_id": thread_email.id,
                        "message_id": thread_email.message_id,
                        "old_price": impact.old_price,
                        "new_price": impact.new_price,
                        "received_at": thread_email.received_at.isoformat() if thread_email.received_at else None
                    })
                    # Track approval status
                    if impact.approved:
                        aggregated_by_part[part_num]["approval_status"] = "approved"
                    elif impact.rejected:
                        aggregated_by_part[part_num]["approval_status"] = "rejected"

            impacts_by_email.append({
                "message_id": thread_email.message_id,
                "subject": thread_email.subject,
                "received_at": thread_email.received_at.isoformat() if thread_email.received_at else None,
                "impacts": email_impacts
            })

    return {
        "conversation_id": email.conversation_id,
        "thread_subject": email.thread_subject or email.subject,
        "total_emails": len(thread_emails),
        "emails_with_bom_data": len(impacts_by_email),
        "aggregated_impacts": aggregated_by_part,
        "total_annual_impact": total_annual_impact,
        "total_parts_affected": len(aggregated_by_part),
        "impacts_by_email": impacts_by_email
    }


@router.get("/{message_id}/thread/extracted-data")
async def get_thread_extracted_data(
    message_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Get aggregated LLM-extracted data from all RECEIVED emails in a conversation thread.

    Aggregates supplier_info, price_change_summary, and affected_products from all
    received emails (excluding sent/outgoing). Later replies override earlier values
    when fields conflict.

    This enables showing combined extraction data that includes information from
    supplier replies to follow-up emails.
    """
    from services.thread_aggregation_service import aggregate_thread_extractions

    user_email = get_user_from_session(request)
    user = await get_user_from_db(db, user_email)

    # Get the email to find its conversation_id
    email = await get_email_from_db(db, message_id)
    if email.user_id != user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    # If no conversation_id, just return single email's extracted data
    if not email.conversation_id:
        # For single email, return its data directly (if it's a received email)
        is_received = not email.is_outgoing
        return {
            "conversation_id": None,
            "thread_subject": email.thread_subject or email.subject,
            "total_emails": 1,
            "received_emails_count": 1 if is_received else 0,
            "emails_with_extractions": 1 if is_received and (email.supplier_info or email.price_change_summary or email.affected_products) else 0,
            "aggregated_supplier_info": {
                "data": email.supplier_info or {},
                "sources": {}
            } if is_received else {"data": {}, "sources": {}},
            "aggregated_price_change_summary": {
                "data": email.price_change_summary or {},
                "sources": {}
            } if is_received else {"data": {}, "sources": {}},
            "aggregated_affected_products": [
                {**p, "source_message_id": email.message_id, "source_received_at": email.received_at.isoformat() if email.received_at else None}
                for p in (email.affected_products or [])
            ] if is_received else [],
            "extractions_by_email": [{
                "message_id": email.message_id,
                "subject": email.subject,
                "received_at": email.received_at.isoformat() if email.received_at else None,
                "is_outgoing": email.is_outgoing or False,
                "supplier_info": email.supplier_info,
                "price_change_summary": email.price_change_summary,
                "affected_products": email.affected_products
            }] if is_received else []
        }

    # Get all emails in thread
    thread_emails = await EmailService.get_emails_by_conversation_id(
        db, email.conversation_id, user.id
    )

    # Aggregate using service
    result = aggregate_thread_extractions(thread_emails, email.thread_subject or email.subject)
    result["conversation_id"] = email.conversation_id

    return result


class PinRequest(BaseModel):
    pinned: bool


@router.patch("/{message_id}/pin")
async def toggle_email_pin(
    message_id: str,
    pin_request: PinRequest,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Pin or unpin an email (bookmark for important threads).
    """
    user_email = get_user_from_session(request)
    user = await get_user_from_db(db, user_email)

    # Get email from database
    email = await get_email_from_db(db, message_id)

    # Verify access
    if email.user_id != user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Update pin status
    pinned_at = datetime.utcnow() if pin_request.pinned else None
    await EmailStateService.update_state(
        db=db,
        message_id=message_id,
        pinned=pin_request.pinned,
        pinned_at=pinned_at
    )

    return {
        "success": True,
        "message_id": message_id,
        "pinned": pin_request.pinned,
        "pinned_at": pinned_at.isoformat() if pinned_at else None
    }


@router.get("/{message_id}/raw")
async def get_raw_email_content(
    message_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Get raw email body content and attachment metadata

    Returns:
    - body: Full HTML or text email body
    - bodyType: 'html' or 'text'
    - attachments: List of attachment metadata (name, size, contentType, id)
    """
    user_email = get_user_from_session(request)
    user = await get_user_from_db(db, user_email)

    # Verify the email belongs to this user
    email = await get_email_from_db(db, message_id)
    if email.user_id != user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    try:
        # Fetch full email from Microsoft Graph API
        graph_client = MultiUserGraphClient()
        msg = await graph_client.get_user_message_by_id(user_email, message_id)

        # Extract email body
        body_data = msg.get("body", {})
        body_content = body_data.get("content", "")
        body_type = body_data.get("contentType", "text").lower()

        # Get attachment metadata if email has attachments
        attachments_meta = []
        if msg.get("hasAttachments", False):
            attachments = await graph_client.get_user_message_attachments(user_email, message_id)

            for att in attachments:
                if att.get("@odata.type", "").endswith("fileAttachment"):
                    attachments_meta.append({
                        "id": att.get("id", ""),
                        "name": att.get("name", "unknown"),
                        "contentType": att.get("contentType", "application/octet-stream"),
                        "size": att.get("size", 0)
                    })

        return {
            "body": body_content,
            "bodyType": body_type,
            "attachments": attachments_meta,
            "subject": msg.get("subject", "No Subject"),
            "from": msg.get("from", {}).get("emailAddress", {}),
            "receivedDateTime": msg.get("receivedDateTime", "")
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch raw email content: {str(e)}"
        )


@router.get("/{message_id}/attachments/{attachment_id}")
async def download_attachment(
    message_id: str,
    attachment_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Download a specific attachment by ID

    Returns the attachment file as a downloadable response
    """
    user_email = get_user_from_session(request)
    user = await get_user_from_db(db, user_email)

    # Verify the email belongs to this user
    email = await get_email_from_db(db, message_id)
    if email.user_id != user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    try:
        # Get attachment from Microsoft Graph API
        graph_client = MultiUserGraphClient()
        attachments = await graph_client.get_user_message_attachments(user_email, message_id)

        # Find the specific attachment
        target_attachment = None
        for att in attachments:
            if att.get("id") == attachment_id:
                target_attachment = att
                break

        if not target_attachment:
            raise HTTPException(status_code=404, detail="Attachment not found")

        # Decode attachment content
        content_bytes_b64 = target_attachment.get("contentBytes")
        if not content_bytes_b64:
            raise HTTPException(status_code=404, detail="Attachment has no content")

        # Decode base64 content
        if isinstance(content_bytes_b64, str):
            content = base64.b64decode(content_bytes_b64)
        else:
            content = content_bytes_b64

        # Get attachment metadata
        filename = target_attachment.get("name", "attachment")
        content_type = target_attachment.get("contentType", "application/octet-stream")

        # Return as downloadable file
        return Response(
            content=content,
            media_type=content_type,
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"'
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to download attachment: {str(e)}"
        )


@router.patch("/{message_id}")
async def update_email_state(
    message_id: str,
    update: EmailStateUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
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
    user = await get_user_from_db(db, user_email)

    # Get email from database
    email = await get_email_from_db(db, message_id)

    # Verify access
    if email.user_id != user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Build email_data dict for validation service
    # If email is part of a thread, use AGGREGATED data from all received emails
    # This ensures reason from reply emails, updated supplier info, etc. are included
    if email.conversation_id:
        # Get all emails in the thread
        thread_emails = await EmailService.get_emails_by_conversation_id(
            db, email.conversation_id, user.id
        )

        # Aggregate data from all received emails in the thread
        aggregated = aggregate_thread_extractions(thread_emails, email.thread_subject or email.subject)

        # Use aggregated data for validation and sync
        email_data = {
            "supplier_info": aggregated["aggregated_supplier_info"]["data"],
            "price_change_summary": aggregated["aggregated_price_change_summary"]["data"],
            "affected_products": [
                # Strip source tracking fields for validation/sync
                {k: v for k, v in p.items() if not k.startswith("source_")}
                for p in aggregated["aggregated_affected_products"]
            ],
            "additional_details": email.additional_details or {}
        }

        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Using AGGREGATED thread data for Epicor sync:")
        logger.info(f"  Thread has {aggregated['received_emails_count']} received emails")
        logger.info(f"  Aggregated supplier_id: {email_data['supplier_info'].get('supplier_id')}")
        logger.info(f"  Aggregated reason: {email_data['price_change_summary'].get('reason', 'None')[:50] if email_data['price_change_summary'].get('reason') else 'None'}")
        logger.info(f"  Total products: {len(email_data['affected_products'])}")
    else:
        # Single email (no thread) - use individual email data
        email_data = {
            "supplier_info": email.supplier_info or {},
            "price_change_summary": email.price_change_summary or {},
            "affected_products": email.affected_products or [],
            "additional_details": email.additional_details or {}
        }

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

        # Check supplier validation status from email state
        state = await EmailStateService.get_state_by_message_id(db, message_id)
        epicor_validation = state.epicor_validation_result if state else None
        if epicor_validation:
            summary = epicor_validation.get("summary", {})
            if summary.get("suppliers_validated", 0) == 0:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "error": "Cannot process - Supplier ID not verified in Epicor",
                        "blockers": ["Supplier ID not found in Epicor. Email cannot be processed."]
                    }
                )

        # Check BOM impact supplier-part validation
        bom_impacts = await BomImpactService.get_by_email_id(db, email.id)
        unverified_parts = [
            b.part_num for b in bom_impacts
            if not b.supplier_part_validated and b.status != 'error'
        ]
        if unverified_parts:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "Cannot process - unverified part-supplier relationships",
                    "blockers": [f"Parts with unverified supplier relationship: {', '.join(unverified_parts)}"]
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

        # Sync to Epicor using VendPartSvc (direct update - no re-verification)
        try:
            epicor_service = EpicorAPIService()
            supplier_info = email_data.get("supplier_info", {})
            price_summary = email_data.get("price_change_summary", {})
            effective_date = price_summary.get("effective_date")

            # Get approved BomImpactResults for this email (with pre-validated vendor_num)
            bom_impact_results = await BomImpactService.get_by_email_id(db, email.id)

            # Build products list from approved BomImpactResults
            # Each result has vendor_num pre-validated during Phase 1
            products = []
            for bom_result in bom_impact_results:
                # Only update approved products (not rejected)
                if bom_result.approved and not bom_result.rejected:
                    if bom_result.vendor_num is None:
                        # Fallback warning - vendor_num should be set during verification
                        import logging
                        logging.getLogger(__name__).warning(
                            f"Missing vendor_num for part {bom_result.part_num} - skipping"
                        )
                        continue

                    products.append({
                        "part_num": bom_result.part_num,
                        "new_price": float(bom_result.new_price) if bom_result.new_price else None,
                        "old_price": float(bom_result.old_price) if bom_result.old_price else None,
                        "vendor_num": bom_result.vendor_num,  # Pre-validated from Phase 1
                        "product_name": bom_result.product_name
                    })

            # If no products to update, return error (no fallback)
            if not products:
                raise HTTPException(
                    status_code=400,
                    detail="No approved products with vendor_num found. Please ensure all products have been verified and approved in BOM Impact Analysis."
                )

            # Use VendPartSvc direct update (no verification)
            # Build comment with supplier name and reason for price change
            supplier_name = supplier_info.get('supplier_name', 'Unknown Supplier')
            price_change_reason = price_summary.get('reason', '')
            if price_change_reason:
                comment = f"Price update from {supplier_name} - Reason: {price_change_reason}"
            else:
                comment = f"Price update from {supplier_name}"

            epicor_result = await epicor_service.batch_update_vendpart_prices_direct(
                products=products,
                effective_date=effective_date,
                email_id=message_id,
                comment=comment
            )

            # Save epicor result to DATABASE (not JSON file)
            # Determine sync status based on results
            successful_updates = epicor_result.get("successful", 0)
            failed_updates = epicor_result.get("failed", 0)
            total_products = epicor_result.get("total", len(products) if products else 0)

            # Set sync_status based on results
            if failed_updates == 0 and successful_updates > 0:
                sync_status = "success"
            elif successful_updates > 0 and failed_updates > 0:
                sync_status = "partial"
            elif failed_updates > 0:
                sync_status = "failed"
            else:
                sync_status = "success"

            # Create sync result record in database
            sync_result = await EpicorSyncResultService.create_sync_result(
                db=db,
                email_id=email.id,
                user_id=user.id,
                sync_status=sync_status,
                total_products=total_products,
                successful_updates=successful_updates,
                failed_updates=failed_updates,
                results_summary=epicor_result,
                error_message=None
            )

            # Update email state in database (mark as processed and synced)
            state = await EmailStateService.get_state_by_message_id(db, message_id)
            if state:
                await EmailStateService.update_state(
                    db=db,
                    message_id=message_id,
                    processed=True,
                    epicor_synced=True
                )
            else:
                state = await EmailStateService.create_state(
                    db=db,
                    message_id=message_id,
                    user_id=user.id,
                    processed=True,
                    epicor_synced=True
                )

            await db.commit()

            # Return state as dict for response
            state_dict = {
                "message_id": state.message_id,
                "processed": state.processed,
                "epicor_synced": state.epicor_synced,
                "vendor_verified": state.vendor_verified,
                "verification_status": state.verification_status
            }

            return {
                "success": True,
                "state": state_dict,
                "epicor_result": epicor_result,
                "warnings_bypassed": sync_check["warnings"] if force else []
            }

        except Exception as e:
            await db.rollback()
            raise HTTPException(
                status_code=500,
                detail=f"Failed to sync to Epicor: {str(e)}"
            )

    elif update.processed is False:
        # Mark as unprocessed in database
        state = await EmailStateService.get_state_by_message_id(db, message_id)
        if state:
            await EmailStateService.update_state(
                db=db,
                message_id=message_id,
                processed=False,
                epicor_synced=False
            )
        else:
            state = await EmailStateService.create_state(
                db=db,
                message_id=message_id,
                user_id=user.id,
                processed=False,
                epicor_synced=False
            )

        await db.commit()

        # Return state as dict
        state_dict = {
            "message_id": state.message_id,
            "processed": state.processed,
            "epicor_synced": state.epicor_synced,
            "vendor_verified": state.vendor_verified,
            "verification_status": state.verification_status
        }

        return {"success": True, "state": state_dict}

    else:
        raise HTTPException(status_code=400, detail="Invalid update data")


@router.post("/{message_id}/followup")
async def generate_followup(
    message_id: str,
    followup_request: FollowupRequest,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Generate AI follow-up email draft for missing information"""
    user_email = get_user_from_session(request)
    user = await get_user_from_db(db, user_email)

    # Get email from database
    email = await get_email_from_db(db, message_id)

    # Verify access
    if email.user_id != user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Build email_data dict for followup generation
    email_data = {
        "supplier_info": email.supplier_info or {},
        "price_change_summary": email.price_change_summary or {},
        "affected_products": email.affected_products or [],
        "additional_details": email.additional_details or {}
    }

    # Validate missing fields list
    if not followup_request.missing_fields or len(followup_request.missing_fields) == 0:
        raise HTTPException(
            status_code=400,
            detail="At least one missing field must be selected"
        )

    try:
        # Generate follow-up email (async)
        followup_draft = await generate_followup_email(
            email_data=email_data,
            missing_fields=followup_request.missing_fields
        )

        # Get or create email state in database
        state = await EmailStateService.get_state_by_message_id(db, message_id)
        if not state:
            state = await EmailStateService.create_state(
                db=db,
                message_id=message_id,
                user_id=user.id
            )

        # Save the draft to state in database
        missing_field_names = [f['field'] for f in followup_request.missing_fields]
        await EmailStateService.update_state(
            db=db,
            message_id=message_id,
            followup_draft=followup_draft,
            missing_fields=missing_field_names
        )

        await db.commit()

        return {
            "success": True,
            "followup_draft": followup_draft,
            "generated_at": datetime.utcnow().isoformat()
        }

    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate follow-up email: {str(e)}"
        )


@router.post("/{message_id}/send-followup")
async def send_followup(
    message_id: str,
    send_request: SendFollowupRequest,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Send the follow-up email directly via Microsoft Graph API.

    The email will be sent as a reply to the original email thread for proper threading.
    """
    user_email = get_user_from_session(request)
    user = await get_user_from_db(db, user_email)

    # Get email from database
    email = await get_email_from_db(db, message_id)

    # Verify access
    if email.user_id != user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Validate recipients
    if not send_request.to_recipients or len(send_request.to_recipients) == 0:
        raise HTTPException(
            status_code=400,
            detail="At least one recipient is required"
        )

    if not send_request.subject or not send_request.subject.strip():
        raise HTTPException(
            status_code=400,
            detail="Subject is required"
        )

    if not send_request.body_html or not send_request.body_html.strip():
        raise HTTPException(
            status_code=400,
            detail="Email body is required"
        )

    try:
        # Initialize Graph client
        graph_client = MultiUserGraphClient()

        # Send the email as a reply for proper threading
        result = await graph_client.send_email(
            user_email=user_email,
            to_recipients=send_request.to_recipients,
            subject=send_request.subject,
            body_content=send_request.body_html,
            body_type="HTML",
            cc_recipients=send_request.cc_recipients,
            reply_to_message_id=message_id
        )

        # Update email state to record that a followup was sent
        state = await EmailStateService.get_state_by_message_id(db, message_id)
        if state:
            await EmailStateService.update_state(
                db=db,
                message_id=message_id,
                followup_sent=True,
                followup_sent_at=datetime.utcnow()
            )
            await db.commit()

        return {
            "success": True,
            "message": "Follow-up email sent successfully",
            "sent_at": datetime.utcnow().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to send follow-up email: {str(e)}"
        )


@router.post("/{message_id}/approve-and-process")
async def approve_and_process_email(
    message_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Manually approve unverified email and trigger LLM detection + AI extraction.

    New Workflow:
    1. Mark as manually approved
    2. Run LLM price change detection
    3. If detected as price change → run AI extraction
    4. If NOT detected as price change → save result, skip extraction
    """
    user_email = get_user_from_session(request)
    user = await get_user_from_db(db, user_email)

    # Get email from database
    email = await get_email_from_db(db, message_id)

    # Verify access
    if email.user_id != user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Check if already processed
    state = await EmailStateService.get_state_by_message_id(db, message_id)
    if not state or state.verification_status != "pending_review":
        raise HTTPException(
            status_code=400,
            detail="Email is not pending verification"
        )

    # Mark as manually approved in database
    await EmailStateService.update_state(
        db=db,
        message_id=message_id,
        vendor_verified=True,
        manually_approved_by=user_email,
        manually_approved_at=datetime.utcnow()
    )
    await db.commit()

    try:
        # Get original message from Graph API
        graph_client = MultiUserGraphClient()
        msg = await graph_client.get_user_message_by_id(user_email, message_id)

        # STEP 1: Run LLM Price Change Detection
        from services.llm_detector import llm_is_price_change_email
        from utils.processors import process_all_content
        import base64

        # Extract email body
        email_body = ""
        body_data = msg.get("body", {})
        if body_data:
            email_body = body_data.get("content", "")

        # Process attachments (if any)
        attachment_paths = []
        if msg.get("hasAttachments", False):
            attachments = await graph_client.get_user_message_attachments(user_email, message_id)

            # Create user-specific downloads directory
            safe_email = user_email.replace("@", "_at_").replace(".", "_dot_")
            user_downloads_dir = os.path.join("downloads", safe_email)
            os.makedirs(user_downloads_dir, exist_ok=True)

            for att in attachments:
                if att.get("@odata.type", "").endswith("fileAttachment"):
                    filename = att.get("name", "unknown")
                    content_bytes = att.get("contentBytes")

                    if content_bytes:
                        try:
                            if isinstance(content_bytes, str):
                                decoded_content = base64.b64decode(content_bytes)
                            else:
                                decoded_content = content_bytes

                            path = os.path.join(user_downloads_dir, filename)
                            with open(path, "wb") as f:
                                f.write(decoded_content)

                            attachment_paths.append(path)
                        except Exception as e:
                            print(f"Warning: Could not save attachment {filename}: {e}")

        # Process all content
        combined_content = process_all_content(email_body, attachment_paths)

        # Prepare metadata
        subject = msg.get('subject', 'No Subject')
        sender_info = msg.get('from', {}).get('emailAddress', {})
        sender = sender_info.get('address', '') if sender_info else ''
        date_received = msg.get('receivedDateTime', '')

        metadata = {
            'subject': subject,
            'sender': sender,
            'date': date_received,
            'message_id': message_id,
            'has_attachments': msg.get('hasAttachments', False)
        }

        # Run LLM detection (async)
        print(f"Running LLM price change detection for approved email...")
        detection_result = await llm_is_price_change_email(combined_content, metadata)

        # Update email state with detection result in database
        await EmailStateService.update_state(
            db=db,
            message_id=message_id,
            llm_detection_performed=True,
            llm_detection_result=detection_result,
            awaiting_llm_detection=False
        )
        await db.commit()

        # STEP 2: Process based on detection result
        if detection_result.get("meets_threshold", False):
            # Detected as price change - proceed with AI extraction
            confidence = detection_result.get("confidence", 0.0)
            reasoning = detection_result.get("reasoning", "N/A")
            print(f"✅ PRICE CHANGE DETECTED (Confidence: {confidence:.2f})")
            print(f"💡 Reasoning: {reasoning}")

            # Run AI extraction inline (async)
            from services.extractor import extract_price_change_json

            print(f"\nSTAGE 2: AI ENTITY EXTRACTION")
            print("-" * 80)
            print(f"Azure OpenAI GPT-4.1 Processing...")

            # Extract entities using AI (combined_content and metadata already prepared above)
            result = await extract_price_change_json(combined_content, metadata)

            print(f"AI Extraction Complete")

            # Save extracted data to database
            await EmailService.update_email(
                db,
                email_id=email.id,
                supplier_info=result.get("supplier_info"),
                price_change_summary=result.get("price_change_summary"),
                affected_products=result.get("affected_products"),
                additional_details=result.get("additional_details")
            )

            # Update email state to manually approved (not processed yet - waiting for Epicor sync)
            await EmailStateService.update_state(
                db=db,
                message_id=message_id,
                processed=False,
                verification_status="manually_approved",
                is_price_change=True
            )

            await db.commit()

            # ========== EPICOR VALIDATION (PRE-BOM CHECK) ==========
            # Run validation to check part exists, supplier exists, and supplier-part relationship
            affected_products = result.get("affected_products", [])
            supplier_info = result.get("supplier_info", {})
            supplier_id = supplier_info.get("supplier_id", "") if supplier_info else ""

            validation_results = None
            if affected_products and supplier_id:
                print(f"\n🔍 Running Epicor Validation for {len(affected_products)} products...")
                try:
                    epicor_service = EpicorAPIService()

                    validation_results = {
                        "all_products_valid": True,
                        "any_product_can_proceed": False,
                        "product_validations": [],
                        "summary": {
                            "total_products": len(affected_products),
                            "parts_validated": 0,
                            "suppliers_validated": 0,
                            "supplier_parts_validated": 0,
                            "products_blocked": 0
                        }
                    }

                    for idx, product in enumerate(affected_products):
                        part_num = product.get("product_id") or product.get("product_code") or product.get("part_number", "")
                        if not part_num:
                            print(f"   ⚠️ Product {idx + 1}: No part number, skipping validation")
                            validation_results["product_validations"].append({
                                "idx": idx,
                                "part_num": "",
                                "validation_result": {
                                    "all_valid": False,
                                    "part_validated": False,
                                    "supplier_validated": False,
                                    "supplier_part_validated": False,
                                    "validation_errors": ["Missing product_id"],
                                    "can_proceed_with_bom_analysis": False
                                }
                            })
                            validation_results["summary"]["products_blocked"] += 1
                            validation_results["all_products_valid"] = False
                            continue

                        print(f"   🔍 Validating Product {idx + 1}/{len(affected_products)}: {part_num}")

                        # Run validation for this product
                        validation = await epicor_service.validate_supplier_part_for_email(
                            part_num=part_num,
                            supplier_id=supplier_id
                        )

                        validation_results["product_validations"].append({
                            "idx": idx,
                            "part_num": part_num,
                            "validation_result": validation
                        })

                        # Update summary counts
                        if validation.get("part_validated"):
                            validation_results["summary"]["parts_validated"] += 1
                        if validation.get("supplier_validated"):
                            validation_results["summary"]["suppliers_validated"] += 1
                        if validation.get("supplier_part_validated"):
                            validation_results["summary"]["supplier_parts_validated"] += 1

                        if not validation.get("all_valid"):
                            validation_results["all_products_valid"] = False
                            if not validation.get("can_proceed_with_bom_analysis"):
                                validation_results["summary"]["products_blocked"] += 1

                        if validation.get("can_proceed_with_bom_analysis"):
                            validation_results["any_product_can_proceed"] = True

                    # Store validation results in email state
                    await EmailStateService.update_state(
                        db=db,
                        message_id=message_id,
                        epicor_validation_performed=True,
                        epicor_validation_result={
                            "all_products_valid": validation_results["all_products_valid"],
                            "summary": validation_results["summary"],
                            "product_validations": [
                                {
                                    "idx": pv["idx"],
                                    "part_num": pv["part_num"],
                                    "all_valid": pv["validation_result"].get("all_valid"),
                                    "part_validated": pv["validation_result"].get("part_validated"),
                                    "supplier_validated": pv["validation_result"].get("supplier_validated"),
                                    "supplier_part_validated": pv["validation_result"].get("supplier_part_validated"),
                                    "validation_errors": pv["validation_result"].get("validation_errors", [])
                                }
                                for pv in validation_results["product_validations"]
                            ]
                        }
                    )
                    await db.commit()

                    print(f"   ✅ Epicor Validation Complete")
                    print(f"      Parts validated: {validation_results['summary']['parts_validated']}/{len(affected_products)}")
                    print(f"      Supplier-Part links: {validation_results['summary']['supplier_parts_validated']}/{len(affected_products)}")

                except Exception as e:
                    print(f"   ⚠️ Epicor Validation error (non-blocking): {e}")
                    validation_results = None

            # ========== BOM IMPACT ANALYSIS ==========
            # Run BOM impact analysis for products that passed validation
            if affected_products:
                # Check if we should proceed with BOM analysis
                should_proceed = True
                if validation_results:
                    should_proceed = validation_results.get("any_product_can_proceed", False)
                    if not should_proceed:
                        print(f"   ⚠️ Skipping BOM analysis - all products failed Epicor validation")

                if should_proceed:
                    print(f"\n📊 Running BOM Impact Analysis for {len(affected_products)} products...")
                    try:
                        if not epicor_service:
                            epicor_service = EpicorAPIService()

                        for idx, product in enumerate(affected_products):
                            part_num = product.get("product_id") or product.get("product_code") or product.get("part_number", "")
                            old_price = product.get("old_price", 0)
                            new_price = product.get("new_price", 0)

                            if not part_num:
                                print(f"   ⚠️ Product {idx + 1}: No part number, skipping")
                                continue

                            print(f"   📦 Product {idx + 1}/{len(affected_products)}: {part_num}")

                            # Look up pre-validated data for this product
                            pre_validated = None
                            if validation_results:
                                for pv in validation_results.get("product_validations", []):
                                    if pv["idx"] == idx:
                                        pre_validated = pv.get("validation_result")
                                        break

                            try:
                                # Run the BOM impact analysis (async)
                                impact_result = await epicor_service.process_supplier_price_change(
                                    part_num=part_num,
                                    supplier_id=supplier_id,
                                    old_price=float(old_price) if old_price else 0,
                                    new_price=float(new_price) if new_price else 0,
                                    effective_date=result.get("price_change_summary", {}).get("effective_date"),
                                    email_metadata=None,
                                    pre_validated_data=pre_validated
                                )

                                # Store the result in database
                                await BomImpactService.create(
                                    db,
                                    email_id=email.id,
                                    product_index=idx,
                                    impact_data=impact_result
                                )

                                # Log summary
                                status = impact_result.get("status", "unknown")
                                summary = impact_result.get("bom_impact", {}).get("summary", {})
                                total_assemblies = summary.get("total_assemblies_affected", 0)
                                print(f"      ✅ Analysis: {status}, {total_assemblies} assemblies affected")

                            except Exception as e:
                                print(f"      ❌ Error analyzing {part_num}: {e}")
                                # Store error result with pre-validated data
                                error_result = {
                                    "status": "error",
                                    "processing_errors": [str(e)],
                                    "component": {"part_num": part_num, "validated": False},
                                    "supplier": {"supplier_id": supplier_id, "validated": False},
                                    "price_change": {"part_num": part_num, "old_price": old_price, "new_price": new_price},
                                    "bom_impact": {"summary": {}, "impact_details": [], "high_risk_assemblies": []},
                                    "actions_required": [],
                                    "can_auto_approve": False
                                }
                                # Use pre-validated data for correct validation flags
                                if pre_validated:
                                    error_result["supplier_part_validated"] = pre_validated.get("supplier_part_validated", False)
                                    error_result["supplier_part_validation_error"] = pre_validated.get("supplier_part_error")
                                    if pre_validated.get("part_validated") and pre_validated.get("part_data"):
                                        pd = pre_validated["part_data"]
                                        error_result["component"] = {
                                            "part_num": part_num,
                                            "description": pd.get("description", ""),
                                            "type_code": pd.get("type_code", ""),
                                            "uom": pd.get("uom", ""),
                                            "current_cost": pd.get("current_cost", 0),
                                            "validated": True
                                        }
                                    if pre_validated.get("supplier_validated") and pre_validated.get("supplier_data"):
                                        sd = pre_validated["supplier_data"]
                                        error_result["supplier"] = {
                                            "supplier_id": supplier_id,
                                            "vendor_num": sd.get("vendor_num"),
                                            "name": sd.get("name", ""),
                                            "validated": True
                                        }
                                    supplier_part_data = pre_validated.get("supplier_part_data", {}) or {}
                                    supplier_data_pre = pre_validated.get("supplier_data", {}) or {}
                                    vendor_num = supplier_part_data.get("vendor_num") or supplier_data_pre.get("vendor_num")
                                    if vendor_num:
                                        error_result["vendor_num"] = vendor_num
                                await BomImpactService.create(db, email_id=email.id, product_index=idx, impact_data=error_result)

                        await db.commit()
                        print(f"   ✅ BOM Impact Analysis Complete")

                    except Exception as e:
                        print(f"   ⚠️ BOM Impact Analysis error (non-blocking): {e}")

            # Reload email data from database
            await db.refresh(email)
            state = await EmailStateService.get_state_by_message_id(db, message_id)

            # Build email_data dict
            email_data = {
                "supplier_info": email.supplier_info or {},
                "price_change_summary": email.price_change_summary or {},
                "affected_products": email.affected_products or [],
                "additional_details": email.additional_details or {}
            }

            validation = validation_service.validate_email_data(email_data)

            # Convert state to dict
            state_dict = {
                "message_id": state.message_id,
                "processed": state.processed,
                "epicor_synced": state.epicor_synced,
                "vendor_verified": state.vendor_verified,
                "verification_status": state.verification_status,
                "is_price_change": state.is_price_change
            } if state else {}

            return {
                "success": True,
                "message": "Email approved and processed successfully",
                "is_price_change": True,
                "detection_confidence": confidence,
                "detection_reasoning": reasoning,
                "email_data": email_data,
                "state": state_dict,
                "validation": validation
            }

        else:
            # NOT detected as price change - skip extraction
            confidence = detection_result.get("confidence", 0.0)
            reasoning = detection_result.get("reasoning", "N/A")
            print(f"⏭️ NOT A PRICE CHANGE (Confidence: {confidence:.2f})")
            print(f"💡 Reasoning: {reasoning}")

            # Update email state to reflect it's not a price change in database
            await EmailStateService.update_state(
                db=db,
                message_id=message_id,
                verification_status="manually_approved",
                approved_reason=f"Manually approved - LLM confirmed not a price change (Confidence: {confidence:.2f})",
                is_price_change=False,
                processed=False
            )
            await db.commit()

            return {
                "success": True,
                "message": "Email approved but LLM detected it is not a price change notification",
                "is_price_change": False,
                "detection_confidence": confidence,
                "detection_reasoning": reasoning,
                "action": "skipped_extraction"
            }

    except Exception as e:
        # Revert approval if processing failed
        await EmailStateService.update_state(
            db=db,
            message_id=message_id,
            verification_status="pending_review",
            vendor_verified=False,
            manually_approved_by=None,
            manually_approved_at=None,
            awaiting_llm_detection=True
        )
        await db.commit()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process approved email: {str(e)}"
        )


@router.post("/{message_id}/reject")
async def reject_email(
    message_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Reject/ignore unverified email"""
    user_email = get_user_from_session(request)
    user = await get_user_from_db(db, user_email)

    # Get email from database
    email = await get_email_from_db(db, message_id)

    # Verify access
    if email.user_id != user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Check if email exists and is pending verification
    state = await EmailStateService.get_state_by_message_id(db, message_id)
    if not state or state.verification_status != "pending_review":
        raise HTTPException(
            status_code=400,
            detail="Email is not pending verification"
        )

    # Mark as rejected (simple, no detailed tracking) in database
    await EmailStateService.update_state(
        db=db,
        message_id=message_id,
        verification_status="rejected",
        awaiting_llm_detection=False,
        llm_detection_performed=False
    )
    await db.commit()

    return {
        "success": True,
        "message": "Email rejected successfully"
    }


# ============================================================================
# BOM IMPACT ANALYSIS ENDPOINTS
# ============================================================================

@router.get("/{message_id}/bom-impact")
async def get_bom_impact(
    message_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Get BOM impact analysis results for an email.

    Returns all BOM impact results for each product in the email.
    """
    from database.services.bom_impact_service import BomImpactService

    user_email = get_user_from_session(request)
    user = await get_user_from_db(db, user_email)

    # Get email and verify access
    email = await get_email_from_db(db, message_id)
    if email.user_id != user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Get BOM impact results
    impacts = await BomImpactService.get_by_email_id(db, email.id)

    return {
        "email_id": email.id,
        "message_id": message_id,
        "total_products": len(impacts),
        "impacts": [BomImpactService.to_dict(impact) for impact in impacts]
    }


class BomImpactApprovalRequest(BaseModel):
    approval_notes: Optional[str] = None


class BomImpactRejectionRequest(BaseModel):
    rejection_reason: Optional[str] = None


# Static BOM routes must come before dynamic /{product_index} routes
@router.post("/{message_id}/bom-impact/approve-all")
async def approve_all_bom_impacts(
    message_id: str,
    approval_request: BomImpactApprovalRequest,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Approve all products in an email for Epicor sync.

    This is a convenience endpoint to approve all products at once.
    """
    from database.services.bom_impact_service import BomImpactService

    user_email = get_user_from_session(request)
    user = await get_user_from_db(db, user_email)

    # Get email and verify access
    email = await get_email_from_db(db, message_id)
    if email.user_id != user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Get BOM impact results for this email
    impacts = await BomImpactService.get_by_email_id(db, email.id)

    if not impacts:
        raise HTTPException(
            status_code=404,
            detail="No BOM impact results found for this email"
        )

    approved_count = 0
    already_approved = 0

    for impact in impacts:
        if impact.approved:
            already_approved += 1
            continue

        await BomImpactService.approve(
            db,
            impact_id=impact.id,
            approved_by_id=user.id,
            approval_notes=approval_request.approval_notes
        )
        approved_count += 1

    await db.commit()

    return {
        "success": True,
        "message": f"Approved {approved_count} product(s) for Epicor sync",
        "approved_count": approved_count,
        "already_approved": already_approved,
        "total_products": len(impacts)
    }


@router.post("/{message_id}/bom-impact/{product_index}/approve")
async def approve_bom_impact(
    message_id: str,
    product_index: int,
    approval_request: BomImpactApprovalRequest,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Approve a specific product's BOM impact for Epicor sync.

    This marks the product as approved for price update in Epicor.
    """
    from database.services.bom_impact_service import BomImpactService

    user_email = get_user_from_session(request)
    user = await get_user_from_db(db, user_email)

    # Get email and verify access
    email = await get_email_from_db(db, message_id)
    if email.user_id != user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Get BOM impact results for this email
    impacts = await BomImpactService.get_by_email_id(db, email.id)

    # Find the specific product
    target_impact = None
    for impact in impacts:
        if impact.product_index == product_index:
            target_impact = impact
            break

    if not target_impact:
        raise HTTPException(
            status_code=404,
            detail=f"BOM impact result not found for product index {product_index}"
        )

    if target_impact.approved:
        raise HTTPException(
            status_code=400,
            detail="This product has already been approved"
        )

    # Approve the BOM impact
    approved_impact = await BomImpactService.approve(
        db,
        impact_id=target_impact.id,
        approved_by_id=user.id,
        approval_notes=approval_request.approval_notes
    )
    await db.commit()

    return {
        "success": True,
        "message": f"Product {target_impact.part_num} approved for Epicor sync",
        "impact": BomImpactService.to_dict(approved_impact)
    }


@router.post("/{message_id}/bom-impact/{product_index}/reject")
async def reject_bom_impact(
    message_id: str,
    product_index: int,
    rejection_request: BomImpactRejectionRequest,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Reject a specific product's BOM impact (will not sync to Epicor).

    This marks the product as rejected - the price change will not be applied in Epicor.
    """
    from database.services.bom_impact_service import BomImpactService

    user_email = get_user_from_session(request)
    user = await get_user_from_db(db, user_email)

    # Get email and verify access
    email = await get_email_from_db(db, message_id)
    if email.user_id != user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Get BOM impact results for this email
    impacts = await BomImpactService.get_by_email_id(db, email.id)

    # Find the specific product
    target_impact = None
    for impact in impacts:
        if impact.product_index == product_index:
            target_impact = impact
            break

    if not target_impact:
        raise HTTPException(
            status_code=404,
            detail=f"BOM impact result not found for product index {product_index}"
        )

    if target_impact.rejected:
        raise HTTPException(
            status_code=400,
            detail="This product has already been rejected"
        )

    # Reject the BOM impact
    rejected_impact = await BomImpactService.reject(
        db,
        impact_id=target_impact.id,
        rejected_by_id=user.id,
        rejection_reason=rejection_request.rejection_reason
    )
    await db.commit()

    return {
        "success": True,
        "message": f"Product {target_impact.part_num} rejected - will not sync to Epicor",
        "impact": BomImpactService.to_dict(rejected_impact)
    }


@router.post("/{message_id}/reanalyze-bom-impact")
async def reanalyze_bom_impact(
    message_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Re-run BOM impact analysis for an email.

    This deletes existing results and runs the analysis again.
    Useful if Epicor data has changed or if there was an error.
    """
    from database.services.bom_impact_service import BomImpactService
    from email_processor import run_bom_impact_analysis

    user_email = get_user_from_session(request)
    user = await get_user_from_db(db, user_email)

    # Get email and verify access
    email = await get_email_from_db(db, message_id)
    if email.user_id != user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Check if email has affected products
    if not email.affected_products:
        raise HTTPException(
            status_code=400,
            detail="Email has no affected products to analyze"
        )

    # Build extraction result from email data
    extraction_result = {
        "affected_products": email.affected_products,
        "price_change_summary": email.price_change_summary,
        "supplier_info": email.supplier_info
    }

    try:
        # Run BOM impact analysis (this will delete existing results first)
        await run_bom_impact_analysis(
            email_id=email.id,
            extraction_result=extraction_result,
            supplier_info=email.supplier_info
        )

        # Get updated results
        impacts = await BomImpactService.get_by_email_id(db, email.id)

        return {
            "success": True,
            "message": f"BOM impact analysis completed for {len(impacts)} product(s)",
            "impacts": [BomImpactService.to_dict(impact) for impact in impacts]
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"BOM impact analysis failed: {str(e)}"
        )
