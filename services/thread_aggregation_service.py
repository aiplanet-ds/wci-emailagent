"""
Thread Aggregation Service

Aggregates LLM-extracted data from all RECEIVED emails in a conversation thread.
Later replies override earlier values for conflicting fields.
Sent/outgoing emails are excluded from aggregation.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from database.models import Email


def merge_supplier_info(sorted_emails: List[Email]) -> Dict[str, Any]:
    """
    Merge supplier_info from all received emails.
    Later emails (by received_at) override earlier values for conflicts.

    Args:
        sorted_emails: List of Email objects sorted by received_at ascending (oldest first)

    Returns:
        Dict with 'data' (merged supplier info) and 'sources' (which email provided each field)
    """
    merged = {
        "supplier_id": None,
        "supplier_name": None,
        "contact_person": None,
        "contact_email": None,
        "contact_phone": None,
    }
    sources = {}

    for email in sorted_emails:
        if not email.supplier_info:
            continue
        for key in merged.keys():
            value = email.supplier_info.get(key)
            if value:  # Non-null value overwrites
                merged[key] = value
                sources[key] = {
                    "message_id": email.message_id,
                    "received_at": email.received_at.isoformat() if email.received_at else None
                }

    return {"data": merged, "sources": sources}


def merge_price_change_summary(sorted_emails: List[Email]) -> Dict[str, Any]:
    """
    Merge price_change_summary from all received emails.
    Critical fields like 'reason' from later emails override earlier ones.

    Args:
        sorted_emails: List of Email objects sorted by received_at ascending (oldest first)

    Returns:
        Dict with 'data' (merged summary) and 'sources' (which email provided each field)
    """
    merged = {
        "change_type": None,
        "effective_date": None,
        "reason": None,
        "overall_impact": None,
    }
    sources = {}

    for email in sorted_emails:
        if not email.price_change_summary:
            continue
        for key in merged.keys():
            value = email.price_change_summary.get(key)
            if value:
                merged[key] = value
                sources[key] = {
                    "message_id": email.message_id,
                    "received_at": email.received_at.isoformat() if email.received_at else None
                }

    return {"data": merged, "sources": sources}


def merge_affected_products(sorted_emails: List[Email]) -> List[Dict[str, Any]]:
    """
    Merge affected_products from all received emails.

    Strategy:
    1. Use product_id as unique key for deduplication
    2. Later email's data for same product_id overwrites earlier
    3. Products without product_id are kept separate (append all)
    4. Track source email for each product

    Args:
        sorted_emails: List of Email objects sorted by received_at ascending (oldest first)

    Returns:
        List of products with source information
    """
    products_by_id: Dict[str, Dict[str, Any]] = {}  # product_id -> product_data
    products_without_id: List[Dict[str, Any]] = []  # Products with no product_id

    for email in sorted_emails:
        if not email.affected_products:
            continue
        for product in email.affected_products:
            product_id = product.get("product_id")
            enriched_product = {
                **product,
                "source_message_id": email.message_id,
                "source_received_at": email.received_at.isoformat() if email.received_at else None
            }

            if product_id:
                # Later email overwrites earlier for same product_id
                products_by_id[product_id] = enriched_product
            else:
                products_without_id.append(enriched_product)

    return list(products_by_id.values()) + products_without_id


def count_with_extractions(emails: List[Email]) -> int:
    """Count emails that have any extracted data."""
    count = 0
    for email in emails:
        if email.supplier_info or email.price_change_summary or email.affected_products:
            count += 1
    return count


def build_per_email_breakdown(sorted_emails: List[Email]) -> List[Dict[str, Any]]:
    """Build per-email breakdown of extractions for reference."""
    breakdown = []
    for email in sorted_emails:
        breakdown.append({
            "message_id": email.message_id,
            "subject": email.subject,
            "received_at": email.received_at.isoformat() if email.received_at else None,
            "is_outgoing": email.is_outgoing or False,
            "supplier_info": email.supplier_info,
            "price_change_summary": email.price_change_summary,
            "affected_products": email.affected_products
        })
    return breakdown


def aggregate_thread_extractions(emails: List[Email], thread_subject: str) -> Dict[str, Any]:
    """
    Aggregate extracted data from all RECEIVED emails in a thread.

    Args:
        emails: All emails in the thread (including sent)
        thread_subject: The thread subject for the response

    Returns:
        Aggregated extraction data with sources
    """
    # Filter to received emails only (exclude sent/outgoing)
    received_emails = [e for e in emails if not e.is_outgoing]

    # Sort by received_at ascending (oldest first, so later overwrites)
    sorted_emails = sorted(
        received_emails,
        key=lambda e: e.received_at or datetime.min
    )

    return {
        "thread_subject": thread_subject,
        "total_emails": len(emails),
        "received_emails_count": len(received_emails),
        "emails_with_extractions": count_with_extractions(received_emails),
        "aggregated_supplier_info": merge_supplier_info(sorted_emails),
        "aggregated_price_change_summary": merge_price_change_summary(sorted_emails),
        "aggregated_affected_products": merge_affected_products(sorted_emails),
        "extractions_by_email": build_per_email_breakdown(sorted_emails)
    }
