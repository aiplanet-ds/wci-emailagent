"""
Discover ListType values used in existing Epicor price lists
This helps identify what ListType value to use when creating new price lists
"""

import sys
import logging
from pathlib import Path
# Add parent directory to path to allow imports from project root
sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

import os
import requests
from dotenv import load_dotenv
from collections import Counter

load_dotenv()

BASE_URL = os.getenv("EPICOR_BASE_URL")
API_KEY = os.getenv("EPICOR_API_KEY")
BEARER_TOKEN = os.getenv("EPICOR_BEARER_TOKEN")
COMPANY_ID = os.getenv("EPICOR_COMPANY_ID")


def get_headers():
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    if BEARER_TOKEN and BEARER_TOKEN != "your-epicor-bearer-token-here":
        headers["Authorization"] = f"Bearer {BEARER_TOKEN}"
    if API_KEY:
        headers["X-api-Key"] = API_KEY
    return headers


def main():
    logger.info("=" * 80)
    logger.info("DISCOVERING LISTTYPE VALUES IN EPICOR PRICE LISTS")
    logger.info("=" * 80)

    # Query all price lists
    url = f"{BASE_URL}/{COMPANY_ID}/Erp.BO.PriceLstSvc/PriceLsts"
    params = {
        "$filter": f"Company eq '{COMPANY_ID}'",
        "$top": "100"  # Get up to 100 price lists
    }

    logger.info("Querying price lists...")
    logger.info(f"URL: {url}")

    response = requests.get(url, headers=get_headers(), params=params, timeout=10)

    logger.info(f"Status: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        price_lists = data.get("value", [])

        logger.info(f"Found {len(price_lists)} price lists")

        if price_lists:
            # Extract all ListType values
            list_types = []
            list_type_examples = {}

            for pl in price_lists:
                list_type = pl.get("ListType", "NOT SET")
                list_code = pl.get("ListCode", "")
                description = pl.get("ListDescription", "")

                list_types.append(list_type)

                # Store an example for each ListType
                if list_type not in list_type_examples:
                    list_type_examples[list_type] = {
                        "ListCode": list_code,
                        "ListDescription": description,
                        "full_record": pl
                    }

            # Count occurrences of each ListType
            type_counts = Counter(list_types)

            logger.info("=" * 80)
            logger.info("LISTTYPE ANALYSIS")
            logger.info("=" * 80)

            logger.info(f"Unique ListType values found: {len(type_counts)}")
            logger.info("ListType Distribution:")
            for list_type, count in type_counts.most_common():
                percentage = (count / len(price_lists)) * 100
                logger.info(f"  '{list_type}': {count} price lists ({percentage:.1f}%)")

            # Show examples of each ListType
            logger.info("=" * 80)
            logger.info("EXAMPLES OF EACH LISTTYPE")
            logger.info("=" * 80)

            for list_type, example in list_type_examples.items():
                logger.info(f"ListType: '{list_type}'")
                logger.info(f"  Example Code: {example['ListCode']}")
                logger.info(f"  Example Description: {example['ListDescription']}")

            # Determine most common ListType
            most_common_type = type_counts.most_common(1)[0][0]

            logger.info("=" * 80)
            logger.info("RECOMMENDATION")
            logger.info("=" * 80)

            logger.info(f"Most commonly used ListType: '{most_common_type}'")
            logger.info(f"Used in {type_counts[most_common_type]} out of {len(price_lists)} price lists")

            logger.info(f"For creating new supplier price lists, use:")
            logger.info(f"  ListType: '{most_common_type}'")

            # Show full structure of one price list
            logger.info("=" * 80)
            logger.info("FULL STRUCTURE OF A SAMPLE PRICE LIST")
            logger.info("=" * 80)

            sample = list_type_examples[most_common_type]['full_record']
            logger.info(f"Sample Price List: {sample.get('ListCode')}")
            logger.info("All fields:")
            for key, value in sorted(sample.items()):
                if key not in ['SysRowID', 'SysRevID', 'RowMod'] and value is not None:
                    logger.info(f"  {key}: {value}")

            # Generate code snippet
            logger.info("=" * 80)
            logger.info("CODE SNIPPET TO USE")
            logger.info("=" * 80)

            logger.info(f"""
Add this field to your price list creation payload:

new_price_list = {{
    "Company": self.company_id,
    "ListCode": list_code,
    "ListDescription": description,
    "ListType": "{most_common_type}",  # <-- ADD THIS LINE
    "StartDate": start_date,
    "EndDate": None,
    "Active": True,
    "CurrencyCode": "USD",
    "RowMod": "A"
}}
""")

        else:
            logger.warning("NO PRICE LISTS FOUND")
            logger.info("This could mean:")
            logger.info("  1. No price lists exist in your Epicor system")
            logger.info("  2. The filter query is incorrect")
            logger.info("  3. Authentication or permissions issue")
    else:
        logger.error(f"ERROR: {response.status_code}")
        logger.error(f"Response: {response.text[:500]}")

    logger.info("=" * 80)
    logger.info("Discovery complete!")
    logger.info("=" * 80)


if __name__ == "__main__":
    main()
