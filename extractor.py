import os, json
from openai import AzureOpenAI
from dotenv import load_dotenv
from typing import Dict, Any, List

load_dotenv()

# Azure OpenAI configuration
client = AzureOpenAI(
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-12-01-preview"),
    azure_endpoint=os.getenv("AZURE_OPENAI_API_ENDPOINT")
)
MODEL_NAME = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4.1")

PRICE_CHANGE_EXTRACTION_PROMPT = """
You are a specialized JSON extractor for supplier price change emails. Extract information from the following email content and convert it into structured JSON.

**IMPORTANT INSTRUCTIONS:**
1. Extract ALL available information, even if incomplete
2. For missing fields, use null (not empty strings)
3. For arrays like affected_products, extract as many products as you can find
4. Look for price information in various formats (currency symbols, numbers, percentages)
5. Pay attention to dates (effective dates, deadlines, notification dates)
6. Extract supplier information from email signatures, letterheads, or content
7. Identify change types: "increase", "decrease", "adjustment", "currency_change", "discount_removed"
8. **CRITICAL**: For each product, extract "product_id" which is the Part Number used in ERP systems (e.g., "TEST-001", "PART-ABC-123")
9. "product_id" and "product_code" may be the same value - extract the part number/SKU/item code as "product_id"

**Expected JSON Schema:**
{
  "email_metadata": {
    "subject": string,
    "sender": string,
    "date": string,
    "message_id": string
  },
  "supplier_info": {
    "supplier_name": string,
    "contact_person": string,
    "contact_email": string,
    "contact_phone": string
  },
  "price_change_summary": {
    "change_type": string,
    "effective_date": string,
    "notification_date": string,
    "reason": string,
    "overall_impact": string
  },
  "affected_products": [
    {
      "product_name": string,
      "product_id": string,
      "product_code": string,
      "old_price": number,
      "new_price": number,
      "price_change_amount": number,
      "price_change_percentage": number,
      "currency": string,
      "unit_of_measure": string
    }
  ],
  "additional_details": {
    "terms_and_conditions": string,
    "payment_terms": string,
    "minimum_order_quantity": string,
    "notes": string
  }
}

**Email Content:**
{{content}}

**Email Metadata:**
{{metadata}}

Return ONLY valid JSON with no additional text or explanations.
"""

def is_price_change_email(email_content: str, metadata: Dict[str, Any]) -> bool:
    """
    Determine if an email is a price change notification
    """
    # Keywords that indicate price change emails
    price_change_keywords = [
        'price change', 'price increase', 'price decrease', 'price adjustment',
        'new pricing', 'pricing update', 'cost increase', 'rate change',
        'tariff', 'price list', 'effective date', 'price revision',
        'currency change', 'discount removed', 'pricing notification'
    ]

    # Check subject line
    subject = metadata.get('subject', '').lower()
    email_body = email_content.lower()

    # Check for keywords in subject or content
    for keyword in price_change_keywords:
        if keyword in subject or keyword in email_body:
            return True

    # Check for price-related patterns
    import re
    price_patterns = [
        r'\$\d+\.?\d*',  # Dollar amounts
        r'€\d+\.?\d*',   # Euro amounts
        r'£\d+\.?\d*',   # Pound amounts
        r'\d+%\s*(increase|decrease)',  # Percentage changes
        r'(old|new|current|previous)\s*price',
        r'effective\s*(date|from)',
    ]

    for pattern in price_patterns:
        if re.search(pattern, email_body, re.IGNORECASE):
            return True

    return False


def extract_price_change_json(content: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract structured data from price change email using Azure OpenAI
    """
    try:
        # Check if this is actually a price change email
        if not is_price_change_email(content, metadata):
            return {
                "error": "Email does not appear to be a price change notification",
                "email_type": "not_price_change"
            }

        # Prepare metadata for the prompt
        safe_metadata = {
            "subject": metadata.get("subject", None),
            "sender": metadata.get("from", None),
            "date": metadata.get("date", None),
            "message_id": metadata.get("message_id", None),
            "attachments": metadata.get("attachments", [])
        }

        # Substitute content and metadata in the prompt
        prompt = PRICE_CHANGE_EXTRACTION_PROMPT.replace("{{content}}", content)
        prompt = prompt.replace("{{metadata}}", json.dumps(safe_metadata, indent=2))

        # Make API call to Azure OpenAI
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=3000
        )

        content_response = response.choices[0].message.content.strip()

        # Try to parse the JSON response
        try:
            extracted_data = json.loads(content_response)
            extracted_data = post_process_extraction(extracted_data, safe_metadata)
            return extracted_data

        except json.JSONDecodeError as e:
            return {
                "error": f"Failed to parse AI response as JSON: {str(e)}",
                "raw_response": content_response[:500]
            }

    except Exception as e:
        return {
            "error": f"Extraction failed: {str(e)}",
            "email_type": "extraction_error"
        }

def post_process_extraction(data: Dict[str, Any], metadata: Dict[str, Any]) -> Dict[str, Any]:
    """
    Post-process extracted data to ensure consistency and add computed fields
    """
    # Ensure email_metadata exists
    if "email_metadata" not in data:
        data["email_metadata"] = {}

    # Fill in metadata from source if missing
    data["email_metadata"]["subject"] = data["email_metadata"].get("subject") or metadata.get("subject")
    data["email_metadata"]["sender"] = data["email_metadata"].get("sender") or metadata.get("sender")
    data["email_metadata"]["date"] = data["email_metadata"].get("date") or metadata.get("date")
    data["email_metadata"]["message_id"] = data["email_metadata"].get("message_id") or metadata.get("message_id")

    # Calculate price changes if not present
    if "affected_products" in data and isinstance(data["affected_products"], list):
        for product in data["affected_products"]:
            if "old_price" in product and "new_price" in product:
                old_price = product.get("old_price")
                new_price = product.get("new_price")

                if old_price and new_price and isinstance(old_price, (int, float)) and isinstance(new_price, (int, float)):
                    # Calculate change amount
                    if "price_change_amount" not in product or product["price_change_amount"] is None:
                        product["price_change_amount"] = round(new_price - old_price, 2)

                    # Calculate percentage change
                    if "price_change_percentage" not in product or product["price_change_percentage"] is None:
                        if old_price != 0:
                            product["price_change_percentage"] = round(((new_price - old_price) / old_price) * 100, 2)

    return data

def extract_from_email(email_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Main entry point for email extraction

    Args:
        email_data: Dictionary containing email content and metadata

    Returns:
        Dictionary with extracted price change information
    """
    content = email_data.get("body", "")
    metadata = {
        "subject": email_data.get("subject", ""),
        "from": email_data.get("from", ""),
        "date": email_data.get("date", ""),
        "message_id": email_data.get("id", ""),
        "attachments": email_data.get("attachments", [])
    }

    return extract_price_change_json(content, metadata)
