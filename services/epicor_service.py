"""
Epicor ERP API Integration Service
Handles authentication and API calls to Epicor for updating part prices
"""

import os
import requests
import base64
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv
import logging
from services.epicor_auth import epicor_auth

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EpicorAPIService:
    """Service for interacting with Epicor ERP API"""
    
    def __init__(self):
        """Initialize Epicor API service with credentials from environment"""
        self.base_url = os.getenv("EPICOR_BASE_URL")
        self.api_key = os.getenv("EPICOR_API_KEY")
        self.bearer_token = os.getenv("EPICOR_BEARER_TOKEN")
        self.company_id = os.getenv("EPICOR_COMPANY_ID")

        # Validate required configuration
        if not self.base_url:
            raise ValueError("EPICOR_BASE_URL not configured in .env file")
        if not self.company_id:
            raise ValueError("EPICOR_COMPANY_ID not configured in .env file")

        # Check authentication method
        if not self.api_key:
            raise ValueError("EPICOR_API_KEY must be configured")
        if not self.bearer_token:
            logger.warning("⚠️ EPICOR_BEARER_TOKEN not configured - API calls may fail")

        logger.info(f"✅ Epicor API Service initialized")
        logger.info(f"   Base URL: {self.base_url}")
        logger.info(f"   Company ID: {self.company_id}")
        logger.info(f"   Auth Method: Bearer Token + X-api-Key")
    
    def _get_headers(self) -> Dict[str, str]:
        """Get authentication headers for API requests"""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Accept-Encoding": "gzip, deflate, br, zstd",
            "Accept-Language": "en-US,en;q=0.9"
        }

        # Get valid Bearer token (automatically refreshes if expired)
        bearer_token = epicor_auth.get_valid_token()

        if bearer_token:
            headers["Authorization"] = f"Bearer {bearer_token}"
        elif self.bearer_token:
            # Fallback to manual token from .env
            headers["Authorization"] = f"Bearer {self.bearer_token}"

        if self.api_key:
            headers["X-api-Key"] = self.api_key

        return headers
    
    def test_connection(self) -> Dict[str, Any]:
        """Test connection to Epicor API"""
        try:
            # Test with the Part Service endpoint (company-specific)
            url = f"{self.base_url}/{self.company_id}/Erp.BO.PartSvc"
            headers = self._get_headers()

            logger.info(f"Testing connection to: {url}")
            response = requests.get(url, headers=headers, timeout=10)

            if response.status_code == 200:
                logger.info("✅ Epicor API connection successful")
                return {
                    "status": "success",
                    "message": "Connection successful",
                    "part_service_accessible": True
                }
            else:
                logger.error(f"❌ Epicor API connection failed: {response.status_code}")
                return {
                    "status": "error",
                    "message": f"HTTP {response.status_code}: {response.text}",
                    "status_code": response.status_code
                }

        except Exception as e:
            logger.error(f"❌ Epicor API connection error: {e}")
            return {
                "status": "error",
                "message": str(e)
            }
    
    def get_part(self, part_num: str) -> Optional[Dict[str, Any]]:
        """
        Get part information from Epicor

        Args:
            part_num: Part number to retrieve

        Returns:
            Part data dictionary or None if not found
        """
        try:
            url = f"{self.base_url}/{self.company_id}/Erp.BO.PartSvc/Parts(Company='{self.company_id}',PartNum='{part_num}')"
            headers = self._get_headers()

            response = requests.get(url, headers=headers, timeout=10)

            if response.status_code == 200:
                part_data = response.json()
                logger.info(f"✅ Retrieved part: {part_num}")
                return part_data
            elif response.status_code == 404:
                logger.warning(f"⚠️ Part not found: {part_num}")
                return None
            else:
                logger.error(f"❌ Error retrieving part {part_num}: {response.status_code} - {response.text}")
                return None

        except Exception as e:
            logger.error(f"❌ Exception retrieving part {part_num}: {e}")
            return None

    def create_part(
        self,
        part_num: str,
        description: str,
        part_type: str = "P",  # P=Purchased, M=Manufactured
        unit_price: float = 0.0,
        ium: str = "EA",  # Inventory Unit of Measure
        pum: str = "EA",  # Purchasing Unit of Measure
        price_per_code: str = "E",  # E=Each
        part_class: str = "",  # Part Class (required by some Epicor configs)
        product_group: str = "",  # Product Group (required by some Epicor configs)
        additional_fields: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create a new part in Epicor

        Args:
            part_num: Part number (unique identifier)
            description: Part description
            part_type: Part type (P=Purchased, M=Manufactured, etc.)
            unit_price: Initial unit price
            ium: Inventory Unit of Measure (EA, LB, etc.)
            pum: Purchasing Unit of Measure
            price_per_code: Price per code (E=Each, C=Per 100, etc.)
            additional_fields: Optional additional fields

        Returns:
            Dictionary with status and message
        """
        try:
            # Check if part already exists
            existing_part = self.get_part(part_num)
            if existing_part:
                return {
                    "status": "error",
                    "message": f"Part {part_num} already exists",
                    "part_num": part_num
                }

            # Prepare POST request
            url = f"{self.base_url}/{self.company_id}/Erp.BO.PartSvc/Parts"
            headers = self._get_headers()

            # Build part payload
            payload = {
                "Company": self.company_id,
                "PartNum": part_num,
                "PartDescription": description,
                "TypeCode": part_type,
                "IUM": ium,
                "PUM": pum,
                "UnitPrice": unit_price,
                "PricePerCode": price_per_code,
                "TrackDimension": False,
                "TrackLots": False,
                "TrackSerialNum": False
            }

            # Add Part Class if provided (required by some Epicor configurations)
            if part_class:
                payload["ClassID"] = part_class

            # Add Product Group if provided (required by some Epicor configurations)
            if product_group:
                payload["ProdCode"] = product_group

            # Add any additional fields
            if additional_fields:
                payload.update(additional_fields)

            logger.info(f"🔄 Creating part {part_num}...")

            # Make POST request
            response = requests.post(url, json=payload, headers=headers, timeout=30)

            if response.status_code in [200, 201]:
                logger.info(f"✅ Successfully created part {part_num}")
                return {
                    "status": "success",
                    "message": f"Part created successfully",
                    "part_num": part_num,
                    "data": response.json()
                }
            else:
                logger.error(f"❌ Failed to create part {part_num}: {response.status_code} - {response.text}")
                return {
                    "status": "error",
                    "message": f"HTTP {response.status_code}: {response.text}",
                    "part_num": part_num,
                    "status_code": response.status_code
                }

        except Exception as e:
            logger.error(f"❌ Exception creating part {part_num}: {e}")
            return {
                "status": "error",
                "message": str(e),
                "part_num": part_num
            }
    
    def update_part_price(
        self, 
        part_num: str, 
        new_price: float,
        price_per_code: str = "E",
        additional_fields: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Update part price in Epicor ERP
        
        Args:
            part_num: Part number to update
            new_price: New unit price
            price_per_code: Price per code (default: "E" for Each)
            additional_fields: Optional additional fields to update
            
        Returns:
            Dictionary with status and message
        """
        try:
            # First, get the current part data (required for PATCH)
            current_part = self.get_part(part_num)
            
            if not current_part:
                return {
                    "status": "error",
                    "message": f"Part {part_num} not found in Epicor",
                    "part_num": part_num
                }
            
            # Prepare PATCH request
            url = f"{self.base_url}/{self.company_id}/Erp.BO.PartSvc/Parts(Company='{self.company_id}',PartNum='{part_num}')"
            headers = self._get_headers()
            
            # Build update payload
            payload = {
                "Company": self.company_id,
                "PartNum": part_num,
                "UnitPrice": new_price,
                "PricePerCode": price_per_code
            }
            
            # Add any additional fields
            if additional_fields:
                payload.update(additional_fields)
            
            logger.info(f"🔄 Updating part {part_num} price to {new_price}")
            
            # Make PATCH request
            response = requests.patch(url, json=payload, headers=headers, timeout=10)
            
            if response.status_code in [200, 204]:
                logger.info(f"✅ Successfully updated part {part_num} price to {new_price}")
                return {
                    "status": "success",
                    "message": f"Price updated successfully",
                    "part_num": part_num,
                    "old_price": current_part.get("UnitPrice"),
                    "new_price": new_price
                }
            else:
                logger.error(f"❌ Failed to update part {part_num}: {response.status_code} - {response.text}")
                return {
                    "status": "error",
                    "message": f"HTTP {response.status_code}: {response.text}",
                    "part_num": part_num,
                    "status_code": response.status_code
                }
                
        except Exception as e:
            logger.error(f"❌ Exception updating part {part_num}: {e}")
            return {
                "status": "error",
                "message": str(e),
                "part_num": part_num
            }
    
    def batch_update_prices(
        self, 
        products: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Update multiple part prices from extracted email data
        
        Args:
            products: List of product dictionaries with product_id, new_price, etc.
            
        Returns:
            Dictionary with batch update results
        """
        results = {
            "total": len(products),
            "successful": 0,
            "failed": 0,
            "skipped": 0,
            "details": []
        }
        
        for product in products:
            part_num = product.get("product_id")
            new_price_str = product.get("new_price")
            
            # Validate data
            if not part_num:
                results["skipped"] += 1
                results["details"].append({
                    "product": product.get("product_name", "Unknown"),
                    "status": "skipped",
                    "reason": "Missing product_id"
                })
                continue
            
            if not new_price_str:
                results["skipped"] += 1
                results["details"].append({
                    "part_num": part_num,
                    "product": product.get("product_name", "Unknown"),
                    "status": "skipped",
                    "reason": "Missing new_price"
                })
                continue
            
            # Parse price (remove currency symbols, commas, etc.)
            try:
                # Clean price string
                clean_price = str(new_price_str).replace("$", "").replace("€", "").replace("£", "")
                clean_price = clean_price.replace(",", "").strip()
                new_price = float(clean_price)
            except (ValueError, TypeError) as e:
                results["failed"] += 1
                results["details"].append({
                    "part_num": part_num,
                    "product": product.get("product_name", "Unknown"),
                    "status": "failed",
                    "reason": f"Invalid price format: {new_price_str}"
                })
                continue
            
            # Update the price
            update_result = self.update_part_price(part_num, new_price)
            
            if update_result["status"] == "success":
                results["successful"] += 1
            else:
                results["failed"] += 1
            
            results["details"].append({
                "part_num": part_num,
                "product": product.get("product_name", "Unknown"),
                "status": update_result["status"],
                "old_price": update_result.get("old_price"),
                "new_price": new_price,
                "message": update_result.get("message")
            })
        
        logger.info(f"📊 Batch update complete: {results['successful']} successful, {results['failed']} failed, {results['skipped']} skipped")
        
        return results


# Global instance
epicor_service = EpicorAPIService()

