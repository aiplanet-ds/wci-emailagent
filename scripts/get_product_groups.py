"""
Get available Product Groups from Epicor
"""

import sys
import logging
from pathlib import Path
# Add parent directory to path to allow imports from project root
sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

import requests
from services.epicor_service import epicor_service


def main():
    logger.info("=" * 70)
    logger.info("Get Product Groups from Epicor")
    logger.info("=" * 70)

    # Get Product Groups
    url = f"{epicor_service.base_url}/{epicor_service.company_id}/Erp.BO.ProdGrupSvc/ProdGrups"
    headers = epicor_service._get_headers()

    logger.info("Fetching Product Groups...")
    logger.info(f"URL: {url}")

    try:
        response = requests.get(url, headers=headers, timeout=10)

        if response.status_code == 200:
            data = response.json()
            prod_groups = data.get("value", [])

            if prod_groups:
                logger.info(f"Found {len(prod_groups)} Product Groups:")
                logger.info("-" * 70)

                for i, pg in enumerate(prod_groups, 1):
                    group_id = pg.get("ProdCode", "N/A")
                    description = pg.get("Description", "No description")

                    logger.info(f"{i}. Product Group: {group_id}")
                    logger.info(f"   Description: {description}")

                logger.info("=" * 70)
                logger.info("To create a part with a product group, use:")
                logger.info("=" * 70)

                # Show first group as example
                if prod_groups:
                    example_group = prod_groups[0].get("ProdCode")
                    logger.info("Example:")
                    logger.info("  python create_test_part.py")
                    logger.info(f"  When prompted for Product Group, enter: {example_group}")

            else:
                logger.warning("No Product Groups found")
                logger.info("This might mean:")
                logger.info("   1. No Product Groups are configured in Epicor")
                logger.info("   2. You don't have permission to view them")
                logger.info("   3. The endpoint URL is incorrect")

        else:
            logger.error(f"Failed to get Product Groups: {response.status_code}")
            logger.error(f"Response: {response.text[:500]}")

            logger.info("Alternative: Check Epicor manually")
            logger.info("   1. Open Epicor ERP")
            logger.info("   2. Go to: Product Configuration -> Product Group Maintenance")
            logger.info("   3. Note the Product Group IDs")
            logger.info("   4. Use one when creating a part")

    except Exception as e:
        logger.error(f"Error: {e}")

        logger.info("Manual steps:")
        logger.info("   1. Open Epicor ERP")
        logger.info("   2. Go to: Product Configuration -> Product Group Maintenance")
        logger.info("   3. Find an active Product Group")
        logger.info("   4. Note the Product Group ID")
        logger.info("   5. Use it when creating a part")

    logger.info("=" * 70)
    logger.info("Done")
    logger.info("=" * 70)


if __name__ == "__main__":
    main()
