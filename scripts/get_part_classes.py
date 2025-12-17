"""
Get available Part Classes from Epicor
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
    logger.info("Get Part Classes from Epicor")
    logger.info("=" * 70)

    # Get Part Classes
    url = f"{epicor_service.base_url}/{epicor_service.company_id}/Erp.BO.PartClassSvc/PartClasses"
    headers = epicor_service._get_headers()

    logger.info("Fetching Part Classes...")
    logger.info(f"URL: {url}")

    try:
        response = requests.get(url, headers=headers, timeout=10)

        if response.status_code == 200:
            data = response.json()
            part_classes = data.get("value", [])

            if part_classes:
                logger.info(f"Found {len(part_classes)} Part Classes:")
                logger.info("-" * 70)

                for i, pc in enumerate(part_classes, 1):
                    class_id = pc.get("ClassID", "N/A")
                    description = pc.get("Description", "No description")
                    active = pc.get("InActive", False)
                    status = "Inactive" if active else "Active"

                    logger.info(f"{i}. Class ID: {class_id}")
                    logger.info(f"   Description: {description}")
                    logger.info(f"   Status: {status}")

                logger.info("=" * 70)
                logger.info("To create a part with a class, use:")
                logger.info("=" * 70)

                # Show first active class as example
                active_classes = [pc for pc in part_classes if not pc.get("InActive", False)]
                if active_classes:
                    example_class = active_classes[0].get("ClassID")
                    logger.info("Example:")
                    logger.info("  python create_test_part.py")
                    logger.info(f"  When prompted for Part Class, enter: {example_class}")

            else:
                logger.warning("No Part Classes found")
                logger.info("This might mean:")
                logger.info("   1. No Part Classes are configured in Epicor")
                logger.info("   2. You don't have permission to view them")
                logger.info("   3. The endpoint URL is incorrect")

        else:
            logger.error(f"Failed to get Part Classes: {response.status_code}")
            logger.error(f"Response: {response.text[:500]}")

            logger.info("Alternative: Check Epicor manually")
            logger.info("   1. Open Epicor ERP")
            logger.info("   2. Go to: Product Configuration -> Part Class Maintenance")
            logger.info("   3. Note the Class IDs")
            logger.info("   4. Use one when creating a part")

    except Exception as e:
        logger.error(f"Error: {e}")

        logger.info("Manual steps:")
        logger.info("   1. Open Epicor ERP")
        logger.info("   2. Go to: Product Configuration -> Part Class Maintenance")
        logger.info("   3. Find an active Part Class")
        logger.info("   4. Note the Class ID")
        logger.info("   5. Use it when creating a part")

    logger.info("=" * 70)
    logger.info("Done")
    logger.info("=" * 70)


if __name__ == "__main__":
    main()
