"""
Discover available price lists in Epicor
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
    logger.info("DISCOVERING AVAILABLE PRICE LISTS")
    logger.info("=" * 80)

    # Query all price lists
    url = f"{BASE_URL}/{COMPANY_ID}/Erp.BO.PriceLstSvc/PriceLsts"
    params = {"$top": "50"}  # Get up to 50 price lists

    logger.info("Querying price lists...")
    logger.info(f"URL: {url}")

    response = requests.get(url, headers=get_headers(), params=params, timeout=10)

    logger.info(f"Status: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        price_lists = data.get("value", [])

        logger.info(f"Found {len(price_lists)} price lists")

        if price_lists:
            logger.info("=" * 80)
            logger.info("AVAILABLE PRICE LISTS")
            logger.info("=" * 80)

            for i, pl in enumerate(price_lists, 1):
                logger.info(f"--- Price List {i} ---")
                logger.info(f"ListCode: {pl.get('ListCode')}")
                logger.info(f"ListDescription: {pl.get('ListDescription')}")
                logger.info(f"Company: {pl.get('Company')}")
                logger.info(f"StartDate: {pl.get('StartDate')}")
                logger.info(f"EndDate: {pl.get('EndDate')}")
                logger.info(f"Active: {pl.get('Active', True)}")

            logger.info("=" * 80)
            logger.info("RECOMMENDATION")
            logger.info("=" * 80)

            # Find the first active price list
            active_lists = [pl for pl in price_lists if pl.get('Active', True)]

            if active_lists:
                recommended = active_lists[0]
                list_code = recommended.get('ListCode')
                logger.info(f"Use this price list code: {list_code}")
                logger.info(f"   Description: {recommended.get('ListDescription')}")
                logger.info("Update your code to use:")
                logger.info(f'   list_code = "{list_code}"')
            else:
                logger.warning("No active price lists found")
                logger.info("   You may need to create a price list in Epicor first")
        else:
            logger.warning("NO PRICE LISTS FOUND")
            logger.info("This means:")
            logger.info("  1. No price lists exist in your Epicor system")
            logger.info("  2. You need to create a price list in Epicor first")
            logger.info("Steps to create a price list:")
            logger.info("  1. Log into Epicor ERP")
            logger.info("  2. Go to: Sales Management -> Price List Maintenance")
            logger.info("  3. Create a new price list (e.g., 'SUPPLIER' or 'VENDOR')")
            logger.info("  4. Then run this script again")
    else:
        logger.error(f"Error: {response.status_code}")
        logger.error(f"Response: {response.text[:500]}")

    logger.info("=" * 80)
    logger.info("Discovery complete!")
    logger.info("=" * 80)


if __name__ == "__main__":
    main()
