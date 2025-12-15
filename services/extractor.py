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

**MULTI-PRODUCT EXTRACTION (CRITICAL):**
1. Price change emails frequently contain MULTIPLE PRODUCTS in a single notification - often dozens or even hundreds. Extract ALL products listed.
2. Look for tabular data with columns like: Description, Part Number, Part#, Price, Effective Date
3. Scan for bulleted lists, numbered lists, or repeated patterns that indicate multiple product price changes
4. For PDF attachments with price lists, extract EVERY product row from ALL tables and ALL pages
5. Products may be grouped by category/section (e.g., "Size O-95 Stroke Control Blocks", "Size B Parts") - extract products from ALL sections
6. If a price shows "-" or is blank, use null for that price value

**DATA EXTRACTION:**
7. Extract ALL available information, even if incomplete
8. For missing fields, use null (not empty strings)
9. Look for price information in various formats (currency symbols like $, numbers with decimals)
10. Pay attention to effective dates - may appear in column headers (e.g., "Effective 01/01/2026") or per-product
11. Extract supplier information from email signatures, letterheads, company headers, or content
12. Identify change types: "increase", "decrease", "adjustment", "currency_change", "discount_removed"

**PART NUMBER HANDLING (CRITICAL):**
13. For each product, extract "product_id" which is the EXACT Part Number used in ERP systems
    - **PRESERVE ALL SPECIAL CHARACTERS**: Include #, -, /, spaces, and any other characters EXACTLY as they appear
    - Examples: "#FFH06-12SAE F", "O950050", "BB0025", "KO9601", "1/2" O-95"
    - DO NOT remove or modify any characters from the part number
    - If multiple part number columns exist (e.g., "PART" and "Company Part#"), prefer the customer/company part number for product_id

**SUPPLIER ID:**
14. Extract "supplier_id" which is the supplier's external identifier/vendor code (e.g., "FAST1", "USUI-001", "SUP123"). This may appear as "Vendor ID", "Supplier Code", "Vendor Code", or similar in the email.

**Expected JSON Schema:**
{
  "supplier_info": {
    "supplier_id": string,
    "supplier_name": string,
    "contact_person": string,
    "contact_email": string,
    "contact_phone": string
  },
  "price_change_summary": {
    "change_type": string,
    "effective_date": string,
    "reason": string,
    "overall_impact": string
  },
  "affected_products": [
    {
      "product_name": string,
      "product_id": string,
      "old_price": number,
      "new_price": number,
      "currency": string,
      "unit_of_measure": string
    }
  ]
}

**Email Content:**
{{content}}

**Email Metadata (for context only):**
{{metadata}}

Return ONLY valid JSON with no additional text or explanations.
"""

def extract_price_change_json(content: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract structured data from price change email using Azure OpenAI.

    Note: This function assumes the email has already been validated as a price change
    notification by the LLM detector service. It focuses solely on data extraction.
    """
    try:

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
        # Using higher max_tokens to handle large price lists from OCR-extracted PDFs
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=16000
        )

        content_response = response.choices[0].message.content.strip()

        # Try to parse the JSON response
        try:
            # Remove markdown code blocks if present
            if content_response.startswith("```"):
                # Remove ```json or ``` at start
                content_response = content_response.split("\n", 1)[1] if "\n" in content_response else content_response[3:]
                # Remove ``` at end
                if content_response.endswith("```"):
                    content_response = content_response[:-3]
                content_response = content_response.strip()

            extracted_data = json.loads(content_response)
            extracted_data = post_process_extraction(extracted_data, safe_metadata)
            return extracted_data

        except json.JSONDecodeError as e:
            print(f"❌ JSON Parse Error: {e}")
            print(f"📄 Raw response (first 1000 chars):\n{content_response[:1000]}")
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
    Post-process extracted data to ensure consistency and add computed fields.

    This function:
    1. Populates email_metadata from source metadata (not extracted by LLM to save tokens)
    2. Computes price_change_amount and price_change_percentage from old_price/new_price
    3. Ensures backwards compatibility with downstream code expecting certain fields
    """
    # Populate email_metadata from source metadata (not extracted by LLM to save tokens)
    data["email_metadata"] = {
        "subject": metadata.get("subject"),
        "sender": metadata.get("sender"),
        "date": metadata.get("date"),
        "message_id": metadata.get("message_id")
    }

    # Ensure supplier_info exists with all expected fields
    if "supplier_info" not in data:
        data["supplier_info"] = {}

    # Ensure price_change_summary exists with all expected fields
    if "price_change_summary" not in data:
        data["price_change_summary"] = {}

    # Ensure affected_products exists
    if "affected_products" not in data:
        data["affected_products"] = []

    # Compute price_change_amount and price_change_percentage for each product
    if isinstance(data["affected_products"], list):
        for product in data["affected_products"]:
            old_price = product.get("old_price")
            new_price = product.get("new_price")

            if old_price is not None and new_price is not None:
                if isinstance(old_price, (int, float)) and isinstance(new_price, (int, float)):
                    # Calculate change amount
                    product["price_change_amount"] = round(new_price - old_price, 2)

                    # Calculate percentage change
                    if old_price != 0:
                        product["price_change_percentage"] = round(((new_price - old_price) / old_price) * 100, 2)
                    else:
                        product["price_change_percentage"] = None
                else:
                    product["price_change_amount"] = None
                    product["price_change_percentage"] = None
            else:
                product["price_change_amount"] = None
                product["price_change_percentage"] = None

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


def generate_followup_email(
    email_data: Dict[str, Any],
    missing_fields: List[Dict[str, Any]],
    original_email_content: str = None
) -> str:
    """
    Generate a professional follow-up email requesting missing information

    Args:
        email_data: Extracted price change data
        missing_fields: List of missing field dictionaries with 'field', 'label', 'section'
        original_email_content: Optional original email content for context

    Returns:
        Generated follow-up email text
    """
    FOLLOWUP_GENERATION_PROMPT = """
You are a professional procurement administrator writing a follow-up email to a supplier regarding a price change notification.

**Context:**
The supplier sent a price change notification, but some required information is missing for our ERP system update.

**Original Email Information:**
- Subject: {subject}
- Sender: {sender}
- Date: {date}
- Supplier: {supplier_name}

**Extracted Data So Far:**
{extracted_data}

**Missing Required Information:**
{missing_fields_list}

**Task:**
Write a professional, polite follow-up email requesting the missing information. The email should:
1. Thank the supplier for the price change notification
2. Briefly acknowledge what information was received
3. Clearly list the missing information needed
4. Explain that this information is required to update our system
5. Request a response by a reasonable deadline (e.g., 3-5 business days)
6. Maintain a professional and courteous tone
7. Use proper email formatting (greeting, body, closing)

**Important Guidelines:**
- Be specific about which fields are missing
- Use professional business language
- Keep the tone friendly but clear about the urgency
- Do not use placeholder text like [Your Name] - just end with "Best regards,"
- Do not include any subject line or email headers (to:, from:, etc.) - just the email body

Write ONLY the email body text, ready to send.
"""

    try:
        # Prepare email metadata
        email_metadata = email_data.get("email_metadata", {})
        supplier_info = email_data.get("supplier_info", {})

        subject = email_metadata.get("subject", "Price Change Notification")
        sender = email_metadata.get("sender", "Supplier")
        date = email_metadata.get("date", "Recently")
        supplier_name = supplier_info.get("supplier_name", sender)

        # Format missing fields for the prompt
        missing_fields_formatted = []
        for field in missing_fields:
            label = field.get("label", field.get("field"))
            section = field.get("section", "")
            missing_fields_formatted.append(f"- {label} ({section})")

        missing_fields_list = "\n".join(missing_fields_formatted) if missing_fields_formatted else "- No specific fields selected"

        # Prepare extracted data summary (excluding empty/null fields)
        extracted_summary = {}
        if supplier_info:
            extracted_summary["Supplier Information"] = {k: v for k, v in supplier_info.items() if v}

        price_summary = email_data.get("price_change_summary", {})
        if price_summary:
            extracted_summary["Price Change Summary"] = {k: v for k, v in price_summary.items() if v}

        affected_products = email_data.get("affected_products", [])
        if affected_products:
            extracted_summary["Number of Products"] = len(affected_products)

        extracted_data_str = json.dumps(extracted_summary, indent=2)

        # Format the prompt
        prompt = FOLLOWUP_GENERATION_PROMPT.format(
            subject=subject,
            sender=sender,
            date=date,
            supplier_name=supplier_name,
            extracted_data=extracted_data_str,
            missing_fields_list=missing_fields_list
        )

        # Call Azure OpenAI
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,  # Slightly higher for more natural language
            max_tokens=800
        )

        followup_email = response.choices[0].message.content.strip()
        return followup_email

    except Exception as e:
        # Return a basic template if AI generation fails
        return generate_fallback_followup_email(email_data, missing_fields)


def generate_fallback_followup_email(
    email_data: Dict[str, Any],
    missing_fields: List[Dict[str, Any]]
) -> str:
    """
    Generate a simple template-based follow-up email as fallback

    Args:
        email_data: Extracted price change data
        missing_fields: List of missing field dictionaries

    Returns:
        Template-based follow-up email
    """
    supplier_info = email_data.get("supplier_info", {})
    email_metadata = email_data.get("email_metadata", {})

    supplier_name = supplier_info.get("supplier_name", "")
    subject = email_metadata.get("subject", "your recent price change notification")

    # Format missing fields
    missing_list = "\n".join([f"- {field.get('label', field.get('field'))}" for field in missing_fields])

    template = f"""Dear {supplier_name or 'Supplier'},

Thank you for {subject}.

To process this price change in our system, we need the following additional information:

{missing_list}

Could you please provide these details at your earliest convenience? We aim to update our records within the next 3-5 business days.

Thank you for your cooperation.

Best regards,"""

    return template
