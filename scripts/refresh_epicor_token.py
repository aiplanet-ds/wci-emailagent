"""
Quick script to refresh Epicor Bearer Token
Run this when you get 401 token expired errors
"""

import sys
import logging
from pathlib import Path
# Add parent directory to path to allow imports from project root
sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

import os
from dotenv import load_dotenv, set_key
from services.epicor_auth import epicor_auth

def refresh_token():
    """Refresh the Epicor Bearer token"""
    logger.info("=" * 80)
    logger.info("EPICOR TOKEN REFRESH UTILITY")
    logger.info("=" * 80)

    # Load environment
    load_dotenv()

    logger.info("Current Configuration:")
    logger.info(f"   Token URL: {epicor_auth.token_url}")
    logger.info(f"   Username: {epicor_auth.username}")
    logger.info(f"   Company ID: {epicor_auth.company_id}")
    logger.info(f"   Client ID: {epicor_auth.client_id[:20]}...")

    logger.info("Requesting new Bearer token...")
    logger.info("-" * 80)

    # Get new token
    result = epicor_auth.get_token_with_password()

    logger.info("-" * 80)

    if result["status"] == "success":
        logger.info("TOKEN REFRESH SUCCESSFUL!")
        logger.info("=" * 80)
        logger.info("Token Details:")
        logger.info(f"   Expires in: {result['expires_in']} seconds ({result['expires_in']//60} minutes)")
        logger.info(f"   Token type: {result['token_type']}")
        logger.info("   Token saved to: .env")
        logger.info("Next Steps:")
        logger.info("   1. Token has been automatically updated in .env file")
        logger.info("   2. Restart your server: python start.py")
        logger.info("   3. Your automated workflow will now work!")
        logger.info("=" * 80)

        # Display first/last 20 chars of token for verification
        token = result['access_token']
        logger.debug(f"Token Preview: {token[:30]}...{token[-30:]}")

        return True
    else:
        logger.error("TOKEN REFRESH FAILED!")
        logger.info("=" * 80)
        logger.error(f"Error: {result.get('message', 'Unknown error')}")
        logger.error(f"Status Code: {result.get('status_code', 'N/A')}")
        logger.info("Troubleshooting:")
        logger.info("   1. Check your credentials in .env file:")
        logger.info("      - EPICOR_USERNAME")
        logger.info("      - EPICOR_PASSWORD")
        logger.info("      - EPICOR_CLIENT_ID")
        logger.info("      - EPICOR_CLIENT_SECRET (if required)")
        logger.info("   2. Verify Epicor login portal is accessible")
        logger.info("   3. Check if your Epicor account is active")
        logger.info("=" * 80)

        return False


if __name__ == "__main__":
    try:
        success = refresh_token()
        exit(0 if success else 1)
    except Exception as e:
        logger.error(f"UNEXPECTED ERROR: {e}")
        logger.info("=" * 80)
        exit(1)

