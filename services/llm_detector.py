"""
LLM-Powered Price Change Detection Service

This module provides intelligent email detection using Large Language Models (LLMs)
to identify supplier price change notifications. Unlike keyword-based detection,
this approach analyzes the semantic meaning and context of emails.

Key Features:
- Analyzes full email content including all attachments
- Returns confidence scores (0.0 - 1.0)
- Provides reasoning for detection decisions
- Separate from extraction logic for modularity
"""

import os
import json
import logging
from typing import Dict, Any, List
from openai import AzureOpenAI

# Configure logging
logger = logging.getLogger(__name__)

# Initialize Azure OpenAI client
client = AzureOpenAI(
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-12-01-preview"),
    azure_endpoint=os.getenv("AZURE_OPENAI_API_ENDPOINT")
)
MODEL_NAME = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4.1")

# Confidence threshold for price change detection (configurable via env)
CONFIDENCE_THRESHOLD = float(os.getenv("PRICE_CHANGE_CONFIDENCE_THRESHOLD", "0.75"))

# LLM Detection Prompt
PRICE_CHANGE_DETECTION_PROMPT = """You are an expert email classifier specializing in supplier communications and procurement processes.

Your task is to analyze the provided email and determine if it is a SUPPLIER PRICE CHANGE NOTIFICATION.

A supplier price change notification is an email that:
1. Comes from a supplier/vendor about their products or services
2. Communicates changes to pricing, rates, costs, or tariffs
3. May include new price lists, price adjustments, rate revisions, or cost updates
4. May reference effective dates for price changes
5. May be in the form of formal notifications, updated price catalogs, or amended quotes

IMPORTANT: This is NOT a price change notification if:
- It's an invoice, receipt, or billing statement (these show prices but don't announce changes)
- It's a purchase order confirmation (these reference prices but don't change them)
- It's a marketing email or newsletter (even if mentioning products/prices)
- It's an internal company email (not from an external supplier)
- It's a delivery notification or shipment tracking
- It's a customer inquiry or quote request

Analyze the following email content:

EMAIL METADATA:
{{metadata}}

EMAIL CONTENT (including all attachments):
{{content}}

Respond with a JSON object in the following exact format:
{
  "is_price_change": true or false,
  "confidence": 0.95,
  "reasoning": "Brief explanation of why this is or is not a price change notification"
}

Rules:
- confidence must be a number between 0.0 and 1.0
- 0.9-1.0: Very confident this is/isn't a price change notification
- 0.7-0.9: Confident with strong indicators
- 0.5-0.7: Moderate confidence, some ambiguity
- 0.0-0.5: Low confidence, unclear or borderline case
- reasoning should be 1-2 sentences maximum
- Only return the JSON object, nothing else
"""


def llm_is_price_change_email(
    email_content: str,
    metadata: Dict[str, Any],
    confidence_threshold: float = None
) -> Dict[str, Any]:
    """
    Use LLM to detect if an email is a supplier price change notification.

    This function analyzes the full email content (body + attachments) using
    Azure OpenAI GPT-4 to intelligently determine if the email represents a
    supplier price change notification.

    Args:
        email_content: Full email content including body and all attachments
        metadata: Email metadata (subject, sender, date, etc.)
        confidence_threshold: Minimum confidence score (0.0-1.0) to consider
                            as price change. Defaults to CONFIDENCE_THRESHOLD env var.

    Returns:
        Dict with keys:
        - is_price_change (bool): Whether email is a price change notification
        - confidence (float): Confidence score 0.0-1.0
        - reasoning (str): Brief explanation of the decision
        - meets_threshold (bool): Whether confidence exceeds threshold

    Example:
        >>> result = llm_is_price_change_email(email_text, metadata)
        >>> if result["meets_threshold"]:
        ...     print(f"Price change detected with {result['confidence']} confidence")
    """
    if confidence_threshold is None:
        confidence_threshold = CONFIDENCE_THRESHOLD

    try:
        # Prepare the prompt with email content and metadata
        prompt = PRICE_CHANGE_DETECTION_PROMPT.replace("{{content}}", email_content[:15000])  # Limit content length
        prompt = prompt.replace("{{metadata}}", json.dumps(metadata, indent=2))

        logger.info(f"Calling LLM for price change detection on email: {metadata.get('subject', 'No subject')}")

        # Call Azure OpenAI API
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,  # Low temperature for consistent, deterministic responses
            max_tokens=300    # Brief response needed
        )

        # Parse LLM response
        response_text = response.choices[0].message.content.strip()

        # Handle potential markdown code blocks in response
        if response_text.startswith("```json"):
            response_text = response_text.split("```json")[1].split("```")[0].strip()
        elif response_text.startswith("```"):
            response_text = response_text.split("```")[1].split("```")[0].strip()

        result = json.loads(response_text)

        # Validate response structure
        if not all(key in result for key in ["is_price_change", "confidence", "reasoning"]):
            raise ValueError("LLM response missing required fields")

        # Ensure confidence is a float between 0 and 1
        confidence = float(result["confidence"])
        if not 0.0 <= confidence <= 1.0:
            logger.warning(f"LLM returned confidence {confidence}, clamping to 0.0-1.0 range")
            confidence = max(0.0, min(1.0, confidence))

        # Add threshold check
        result["confidence"] = confidence
        result["meets_threshold"] = result["is_price_change"] and (confidence >= confidence_threshold)

        logger.info(
            f"LLM Detection Result: is_price_change={result['is_price_change']}, "
            f"confidence={confidence:.2f}, meets_threshold={result['meets_threshold']}, "
            f"reasoning={result['reasoning']}"
        )

        return result

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse LLM response as JSON: {e}")
        logger.error(f"Raw response: {response_text}")
        return {
            "is_price_change": False,
            "confidence": 0.0,
            "reasoning": f"Error parsing LLM response: {str(e)}",
            "meets_threshold": False,
            "error": "json_parse_error"
        }

    except Exception as e:
        logger.error(f"Error in LLM price change detection: {e}", exc_info=True)
        return {
            "is_price_change": False,
            "confidence": 0.0,
            "reasoning": f"Error during LLM detection: {str(e)}",
            "meets_threshold": False,
            "error": str(e)
        }


def batch_detect_price_changes(
    emails: List[Dict[str, Any]],
    confidence_threshold: float = None
) -> List[Dict[str, Any]]:
    """
    Detect price changes for multiple emails in batch.

    Args:
        emails: List of dicts with 'content' and 'metadata' keys
        confidence_threshold: Minimum confidence score

    Returns:
        List of detection results in the same order as input
    """
    results = []
    for email in emails:
        result = llm_is_price_change_email(
            email.get("content", ""),
            email.get("metadata", {}),
            confidence_threshold
        )
        results.append(result)

    return results


def get_detection_stats(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Calculate statistics from detection results.

    Args:
        results: List of detection results from llm_is_price_change_email()

    Returns:
        Dict with statistics (total, detected, avg_confidence, etc.)
    """
    total = len(results)
    detected = sum(1 for r in results if r.get("meets_threshold", False))
    confidences = [r.get("confidence", 0.0) for r in results]

    return {
        "total_emails": total,
        "price_changes_detected": detected,
        "detection_rate": detected / total if total > 0 else 0.0,
        "average_confidence": sum(confidences) / total if total > 0 else 0.0,
        "max_confidence": max(confidences) if confidences else 0.0,
        "min_confidence": min(confidences) if confidences else 0.0
    }
