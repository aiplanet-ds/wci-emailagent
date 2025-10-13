import os, json
from openai import OpenAI
from dotenv import load_dotenv
from typing import Dict, Any, List

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

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
    "supplier_contact": string,
    "supplier_id": string,
    "account_manager": string
  },
  "price_change_details": {
    "effective_date": string,
    "notification_date": string,
    "reason_for_change": string,
    "change_type": string,
    "percentage_change": string,
    "currency": string
  },
  "affected_products": [
    {
      "product_id": string,
      "product_name": string,
      "old_price": string,
      "new_price": string,
      "price_change_amount": string,
      "price_change_percentage": string,
      "category": string,
      "unit": string,
      "effective_date": string
    }
  ],
  "terms_and_conditions": {
    "payment_terms": string,
    "minimum_order_quantity": string,
    "lead_time_changes": string,
    "contract_reference": string
  },
  "action_required": {
    "response_deadline": string,
    "contact_person": string,
    "approval_needed": boolean,
    "next_steps": array
  },
  "attachments_info": {
    "price_list_attached": boolean,
    "contract_attached": boolean,
    "detailed_breakdown": boolean,
    "attachment_names": array
  }
}

**Content to Process:**
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
        r'\d+\.\d+\s*(USD|EUR|GBP|INR)',  # Currency codes
        r'\d+%\s*(increase|decrease)',     # Percentage changes
        r'effective\s+\d+[/\-]\d+[/\-]\d+',  # Effective dates
    ]
    
    for pattern in price_patterns:
        if re.search(pattern, email_content, re.IGNORECASE):
            return True
    
    return False

def extract_price_change_json(content: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract structured data from price change email using OpenAI
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
        
        # Make API call to OpenAI
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=3000  # Increased for comprehensive extraction
        )
        
        content_response = response.choices[0].message.content.strip()
        
        # Try to parse the JSON response
        try:
            extracted_data = json.loads(content_response)
            
            # Post-process the extracted data
            extracted_data = post_process_extraction(extracted_data, safe_metadata)
            
            return extracted_data
            
        except json.JSONDecodeError as e:
            print(f"❌ JSON parsing error: {e}")
            print(f"Raw response: {content_response[:500]}...")
            return {
                "error": "Invalid JSON response from AI",
                "raw_response": content_response
            }
            
    except Exception as e:
        print(f"❌ Error in price change extraction: {e}")
        return {
            "error": str(e),
            "content_length": len(content)
        }

def post_process_extraction(data: Dict[str, Any], metadata: Dict[str, Any]) -> Dict[str, Any]:
    """
    Post-process and validate the extracted data
    """
    # Ensure email_metadata is populated
    if "email_metadata" not in data:
        data["email_metadata"] = {}
    
    # Fill in metadata if missing
    for key, value in metadata.items():
        if key in ["subject", "sender", "date", "message_id"]:
            if not data["email_metadata"].get(key) and value:
                data["email_metadata"][key] = value
    
    # Ensure attachment info is populated
    if "attachments_info" not in data:
        data["attachments_info"] = {}
    
    if "attachment_names" not in data["attachments_info"]:
        data["attachments_info"]["attachment_names"] = metadata.get("attachments", [])
    
    # Set attachment flags based on filenames
    attachment_names = data["attachments_info"]["attachment_names"]
    if attachment_names:
        for filename in attachment_names:
            filename_lower = filename.lower()
            if any(word in filename_lower for word in ["price", "list", "pricing"]):
                data["attachments_info"]["price_list_attached"] = True
            if any(word in filename_lower for word in ["contract", "agreement"]):
                data["attachments_info"]["contract_attached"] = True
            if any(word in filename_lower for word in ["detail", "breakdown", "analysis"]):
                data["attachments_info"]["detailed_breakdown"] = True
    
    # Validate and clean affected_products
    if "affected_products" in data and isinstance(data["affected_products"], list):
        for product in data["affected_products"]:
            # Ensure numeric fields are properly formatted
            for price_field in ["old_price", "new_price", "price_change_amount"]:
                if price_field in product and product[price_field]:
                    # Clean up price strings
                    cleaned_price = str(product[price_field]).replace(",", "").strip()
                    product[price_field] = cleaned_price
    
    return data

def extract_json(text: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
    """
    Main extraction function - wrapper for backward compatibility
    """
    return extract_price_change_json(text, metadata)