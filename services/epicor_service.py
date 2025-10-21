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
        self.default_price_list = os.getenv("EPICOR_DEFAULT_PRICE_LIST", "UNA1")

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
        logger.info(f"   Default Price List: {self.default_price_list}")
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

    def get_vendor_by_id(self, vendor_id: str) -> Optional[Dict[str, Any]]:
        """
        Get vendor information by external VendorID

        Args:
            vendor_id: Vendor's external ID (e.g., "FAST1", "USUI-001")

        Returns:
            Vendor data including VendorNum, Name, etc., or None if not found
        """
        try:
            url = f"{self.base_url}/{self.company_id}/Erp.BO.VendorSvc/Vendors"
            headers = self._get_headers()

            # Filter by VendorID (external ID)
            params = {
                "$filter": f"VendorID eq '{vendor_id}'"
            }

            logger.info(f"🔍 Looking up vendor: {vendor_id}")

            response = requests.get(url, headers=headers, params=params, timeout=10)

            if response.status_code == 200:
                data = response.json()
                results = data.get("value", [])

                if results:
                    vendor = results[0]
                    vendor_num = vendor.get("VendorNum")
                    vendor_name = vendor.get("Name")
                    logger.info(f"✅ Vendor found: VendorNum={vendor_num}, Name={vendor_name}")
                    return vendor
                else:
                    logger.warning(f"⚠️ Vendor not found: {vendor_id}")
                    return None
            else:
                logger.error(f"❌ Error looking up vendor: {response.status_code} - {response.text}")
                return None

        except Exception as e:
            logger.error(f"❌ Exception looking up vendor: {e}")
            return None

    def verify_supplier_part(self, supplier_id: str, part_num: str) -> Optional[Dict[str, Any]]:
        """
        Verify supplier-part relationship using SupplierPartSvc (2-step process)

        This uses a 2-step approach because VendorVendorID cannot be filtered directly:
        Step 1: Lookup VendorNum from VendorSvc using VendorID (external ID)
        Step 2: Query SupplierPartSvc using VendorNum (internal ID) and PartNum

        Args:
            supplier_id: Supplier's external ID (VendorID, e.g., "FAST1")
            part_num: Part number to verify

        Returns:
            Supplier part data including VendorNum, VendorName, etc., or None if not found
        """
        try:
            logger.info(f"🔍 Verifying supplier-part link: Supplier={supplier_id}, Part={part_num}")

            # Step 1: Get VendorNum from VendorID
            vendor = self.get_vendor_by_id(supplier_id)
            if not vendor:
                logger.warning(f"⚠️ Supplier {supplier_id} not found in Epicor")
                return None

            vendor_num = vendor.get("VendorNum")
            vendor_name = vendor.get("Name")

            logger.info(f"   Step 1 complete: VendorNum={vendor_num}")

            # Step 2: Query SupplierPartSvc using VendorNum and PartNum
            url = f"{self.base_url}/{self.company_id}/Erp.BO.SupplierPartSvc/SupplierParts"
            headers = self._get_headers()

            # Filter by VendorNum (internal ID) and PartNum
            filter_query = f"VendorNum eq {vendor_num} and PartNum eq '{part_num}'"
            params = {
                "$filter": filter_query
            }

            logger.info(f"   Step 2: Querying SupplierPartSvc")
            logger.info(f"   Filter: {filter_query}")

            response = requests.get(url, headers=headers, params=params, timeout=10)

            if response.status_code == 200:
                data = response.json()
                results = data.get("value", [])

                if results:
                    supplier_part = results[0]  # Take first match
                    # Add vendor name to the result for convenience
                    supplier_part["VendorName"] = vendor_name
                    supplier_part["VendorVendorID"] = supplier_id
                    logger.info(f"✅ Supplier-part verified: VendorNum={vendor_num}, VendorName={vendor_name}")
                    return supplier_part
                else:
                    logger.warning(f"⚠️ Supplier-part link not found: {supplier_id} / {part_num}")
                    logger.warning(f"   Supplier exists but part is not set up for this supplier in Epicor")
                    return None
            else:
                logger.error(f"❌ Error querying supplier-part: {response.status_code} - {response.text}")
                return None

        except Exception as e:
            logger.error(f"❌ Exception verifying supplier-part: {e}")
            return None

    def get_price_list_parts(self, part_num: str) -> Optional[List[Dict[str, Any]]]:
        """
        Get all price list entries for a part

        Args:
            part_num: Part number to query

        Returns:
            List of price list entries, or None if error
        """
        try:
            url = f"{self.base_url}/{self.company_id}/Erp.BO.PriceLstSvc/PriceLstParts"
            headers = self._get_headers()

            params = {
                "$filter": f"PartNum eq '{part_num}'"
            }

            logger.info(f"🔍 Querying price lists for part: {part_num}")

            response = requests.get(url, headers=headers, params=params, timeout=10)

            # Debug: Log the actual URL being called
            logger.info(f"   Request URL: {response.url}")

            if response.status_code == 200:
                data = response.json()
                results = data.get("value", [])

                if results:
                    logger.info(f"✅ Found {len(results)} price list entries for part {part_num}")
                    return results
                else:
                    logger.warning(f"⚠️ No price list entries found for part {part_num}")
                    return []
            else:
                logger.error(f"❌ Error querying price lists: {response.status_code} - {response.text}")
                return None

        except Exception as e:
            logger.error(f"❌ Exception querying price lists: {e}")
            return None

    def get_price_list(self, list_code: str, part_num: str, uom_code: str = "EA") -> Optional[Dict[str, Any]]:
        """
        Get specific price list entry using filter instead of key

        Args:
            list_code: Price list code
            part_num: Part number
            uom_code: Unit of measure code (default: "EA")

        Returns:
            Price list entry data, or None if not found
        """
        try:
            # Use filter instead of key-based access to handle special characters
            url = f"{self.base_url}/{self.company_id}/Erp.BO.PriceLstSvc/PriceLstParts"
            headers = self._get_headers()

            # Build filter with all three key fields
            params = {
                "$filter": f"ListCode eq '{list_code}' and PartNum eq '{part_num}' and UOMCode eq '{uom_code}'"
            }

            logger.info(f"🔍 Getting price list: ListCode={list_code}, Part={part_num}, UOM={uom_code}")

            response = requests.get(url, headers=headers, params=params, timeout=10)

            if response.status_code == 200:
                data = response.json()
                results = data.get("value", [])

                if results:
                    price_list = results[0]  # Take first match
                    logger.info(f"✅ Retrieved price list entry")
                    return price_list
                else:
                    logger.warning(f"⚠️ Price list entry not found")
                    return None
            else:
                logger.error(f"❌ Error retrieving price list: {response.status_code} - {response.text}")
                return None

        except Exception as e:
            logger.error(f"❌ Exception retrieving price list: {e}")
            return None

    def check_price_list_exists(self, list_code: str, part_num: str, uom_code: str = "EA") -> bool:
        """
        Check if a price list entry exists for a specific part (Step B decision point)

        Args:
            list_code: Price list code
            part_num: Part number
            uom_code: Unit of measure code (default: "EA")

        Returns:
            True if price list exists, False otherwise
        """
        try:
            logger.info(f"📋 Step B: Checking if price list exists...")
            logger.info(f"   ListCode={list_code}, Part={part_num}, UOM={uom_code}")

            price_list = self.get_price_list(list_code, part_num, uom_code)

            if price_list:
                logger.info(f"   ✅ Price list EXISTS - will update existing entry")
                return True
            else:
                logger.info(f"   ℹ️  Price list DOES NOT EXIST - will create new entry")
                return False

        except Exception as e:
            logger.error(f"❌ Exception checking price list existence: {e}")
            return False

    def create_price_list_entry(
        self,
        part_num: str,
        base_price: float,
        effective_date: str,
        uom_code: str = "EA",
        list_code: str = None
    ) -> Dict[str, Any]:
        """
        Create a new price list entry (Step B: Price List Creation - NO path)

        This follows the diagram workflow:
        1. GET PriceListSvc: Retrieve Price List Template
        2. Complete Template with Details
        3. POST PriceListSvc: Save New Price List

        Args:
            part_num: Part number
            base_price: Base price for the part
            effective_date: Effective date in ISO format (e.g., "2025-10-20")
            uom_code: Unit of measure code (default: "EA")
            list_code: Price list code (uses default if not specified)

        Returns:
            Dictionary with status and details
        """
        try:
            # Use default price list if not specified
            if list_code is None:
                list_code = self.default_price_list

            logger.info(f"   📝 Step B (NO path): Creating new price list entry")
            logger.info(f"      ListCode: {list_code}")
            logger.info(f"      PartNum: {part_num}")
            logger.info(f"      BasePrice: ${base_price}")
            logger.info(f"      UOMCode: {uom_code}")

            # === Step 1: GET PriceListSvc: Retrieve Price List Template ===
            logger.info(f"      1️⃣  GET PriceListSvc: Retrieving price list template...")
            get_new_url = f"{self.base_url}/{self.company_id}/Erp.BO.PriceLstSvc/GetNewPriceLstParts"
            headers = self._get_headers()

            get_new_payload = {
                "ds": {
                    "PriceLst": [{
                        "Company": self.company_id,
                        "ListCode": list_code
                    }],
                    "PriceLstParts": []
                },
                "listCode": list_code,
                "partNum": part_num,
                "uomCode": uom_code
            }

            response1 = requests.post(get_new_url, headers=headers, json=get_new_payload, timeout=10)

            if response1.status_code != 200:
                error_msg = response1.text
                logger.error(f"      ❌ Failed to retrieve template: {response1.status_code}")
                logger.error(f"         Response: {error_msg[:300]}")
                return {
                    "status": "error",
                    "message": f"GetNewPriceLstParts failed: HTTP {response1.status_code}: {error_msg[:200]}",
                    "list_code": list_code,
                    "part_num": part_num
                }

            # === Step 2: Complete Template with Details ===
            logger.info(f"      2️⃣  Complete Template with Details...")
            template_data = response1.json()

            # Try different possible response structures
            ds = template_data.get("returnObj") or template_data.get("parameters", {}).get("ds") or template_data

            if not ds.get("PriceLstParts"):
                logger.error(f"      ❌ No template returned from API")
                return {
                    "status": "error",
                    "message": "No template returned from GetNewPriceLstParts",
                    "list_code": list_code,
                    "part_num": part_num
                }

            # Get the template record and fill in the details
            new_record = ds["PriceLstParts"][0]

            new_record["PartNum"] = part_num
            new_record["UOMCode"] = uom_code
            new_record["BasePrice"] = base_price
            new_record["RowMod"] = "A"  # A = Add

            # Note: Effective dates are managed at header level only (Step C)
            # Parts inherit the StartDate from the price list header
            logger.info(f"         ℹ️  Effective date will be managed at header level")

            logger.info(f"         ✅ Template completed with part details")

            # === Step 3: POST PriceListSvc: Save New Price List ===
            logger.info(f"      3️⃣  POST PriceListSvc: Saving new price list entry...")
            update_url = f"{self.base_url}/{self.company_id}/Erp.BO.PriceLstSvc/Update"
            update_payload = {"ds": ds}

            response2 = requests.post(update_url, headers=headers, json=update_payload, timeout=10)

            if response2.status_code == 200:
                logger.info(f"         ✅ Price list entry saved successfully")
                return {
                    "status": "success",
                    "message": "Price list entry created",
                    "list_code": list_code,
                    "part_num": part_num,
                    "base_price": base_price,
                    "effective_date": effective_date
                }
            else:
                error_msg = response2.text
                logger.error(f"      ❌ Failed to save entry: {response2.status_code}")
                logger.error(f"         Response: {error_msg[:300]}")

                return {
                    "status": "error",
                    "message": f"Update failed: HTTP {response2.status_code}: {error_msg[:200]}",
                    "list_code": list_code,
                    "part_num": part_num
                }

        except Exception as e:
            logger.error(f"      ❌ Exception creating price list entry: {e}")
            return {
                "status": "error",
                "message": str(e),
                "list_code": list_code,
                "part_num": part_num
            }

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

    def update_price_list_header_dates(
        self,
        list_code: str,
        start_date: str,
        end_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Update price list header with effective dates (Step C: Effective Date Management)

        Important: Effective dates are managed at the HEADER level only in Epicor.
        Individual parts/breaks inherit the dates from the header.

        Args:
            list_code: Price list code
            start_date: Start date in ISO format (e.g., "2025-10-20" or "2025-10-20T00:00:00")
            end_date: Optional end date in ISO format

        Returns:
            Dictionary with status and message
        """
        try:
            logger.info(f"📋 Step C: Updating price list header with effective dates...")
            logger.info(f"   ListCode: {list_code}")
            logger.info(f"   StartDate: {start_date}")
            if end_date:
                logger.info(f"   EndDate: {end_date}")

            # Ensure dates have time component
            if start_date and 'T' not in start_date:
                start_date = f"{start_date}T00:00:00"
            if end_date and 'T' not in end_date:
                end_date = f"{end_date}T00:00:00"

            # Step 1: Get the current price list header
            url = f"{self.base_url}/{self.company_id}/Erp.BO.PriceLstSvc/PriceLsts"
            headers = self._get_headers()

            params = {
                "$filter": f"ListCode eq '{list_code}'"
            }

            logger.info(f"   Fetching price list header...")
            response = requests.get(url, headers=headers, params=params, timeout=10)

            if response.status_code != 200:
                logger.error(f"❌ Failed to fetch price list header: {response.status_code}")
                return {
                    "status": "error",
                    "message": f"Failed to fetch price list header: HTTP {response.status_code}",
                    "list_code": list_code
                }

            data = response.json()
            results = data.get("value", [])

            if not results:
                logger.error(f"❌ Price list header not found: {list_code}")
                return {
                    "status": "error",
                    "message": f"Price list header not found: {list_code}",
                    "list_code": list_code
                }

            # Step 2: Update the header with new dates
            price_list_header = results[0]
            price_list_header["StartDate"] = start_date
            if end_date:
                price_list_header["EndDate"] = end_date
            price_list_header["RowMod"] = "U"  # U = Update

            # Step 3: Call Update method
            update_url = f"{self.base_url}/{self.company_id}/Erp.BO.PriceLstSvc/Update"

            ds = {
                "PriceLst": [price_list_header]
            }

            payload = {"ds": ds}

            logger.info(f"   Updating price list header...")
            response = requests.post(update_url, json=payload, headers=headers, timeout=10)

            if response.status_code == 200:
                logger.info(f"✅ Step C Complete: Price list header dates updated")
                logger.info(f"   StartDate: {start_date}")
                if end_date:
                    logger.info(f"   EndDate: {end_date}")
                return {
                    "status": "success",
                    "message": "Price list header dates updated successfully",
                    "list_code": list_code,
                    "start_date": start_date,
                    "end_date": end_date
                }
            else:
                logger.error(f"❌ Failed to update price list header: {response.status_code}")
                logger.error(f"   Response: {response.text[:500]}")
                return {
                    "status": "error",
                    "message": f"HTTP {response.status_code}: {response.text[:200]}",
                    "list_code": list_code,
                    "status_code": response.status_code
                }

        except Exception as e:
            logger.error(f"❌ Exception updating price list header: {e}")
            return {
                "status": "error",
                "message": str(e),
                "list_code": list_code
            }

    def update_price_list(
        self,
        list_code: str,
        part_num: str,
        new_price: float,
        effective_date: str,
        uom_code: str = "EA"
    ) -> Dict[str, Any]:
        """
        Update part price in price list with effective date using Epicor Update workflow

        Args:
            list_code: Price list code
            part_num: Part number to update
            new_price: New base price
            effective_date: Effective date in ISO format (e.g., "2025-10-20" or "2025-10-20T00:00:00")
            uom_code: Unit of measure code (default: "EA")

        Returns:
            Dictionary with status and message
        """
        try:
            # Step 1: Get the current price list entry (includes all required fields)
            current_entry = self.get_price_list(list_code, part_num, uom_code)

            if not current_entry:
                return {
                    "status": "error",
                    "message": f"Price list entry not found: ListCode={list_code}, Part={part_num}, UOM={uom_code}",
                    "part_num": part_num,
                    "list_code": list_code
                }

            old_price = current_entry.get("BasePrice")

            # Ensure effective_date has time component
            if effective_date and 'T' not in effective_date:
                effective_date = f"{effective_date}T00:00:00"

            logger.info(f"🔄 Updating price list: ListCode={list_code}, Part={part_num}, Price={new_price}, EffectiveDate={effective_date}")

            # Step 2: Update the entry fields
            current_entry["BasePrice"] = new_price
            current_entry["RowMod"] = "U"  # U = Update

            logger.info(f"   ℹ️  Effective date ({effective_date}) managed at header level (Step C)")
            logger.info(f"   ℹ️  This part will inherit the StartDate from price list header")

            # Step 3: Call Update method with the modified dataset
            update_url = f"{self.base_url}/{self.company_id}/Erp.BO.PriceLstSvc/Update"
            headers = self._get_headers()

            # Build the dataset structure
            ds = {
                "PriceLst": [],
                "PriceLstParts": [current_entry]
            }

            payload = {"ds": ds}

            logger.info(f"   Calling Update method...")
            response = requests.post(update_url, json=payload, headers=headers, timeout=10)

            if response.status_code == 200:
                logger.info(f"✅ Successfully updated price list for part {part_num}")
                logger.info(f"   Old Price: ${old_price} → New Price: ${new_price}")
                logger.info(f"   Effective Date: {effective_date}")
                return {
                    "status": "success",
                    "message": f"Price list updated successfully",
                    "part_num": part_num,
                    "list_code": list_code,
                    "old_price": old_price,
                    "new_price": new_price,
                    "effective_date": effective_date
                }
            else:
                logger.error(f"❌ Failed to update price list: {response.status_code} - {response.text[:500]}")
                return {
                    "status": "error",
                    "message": f"HTTP {response.status_code}: {response.text[:200]}",
                    "part_num": part_num,
                    "list_code": list_code,
                    "status_code": response.status_code
                }

        except Exception as e:
            logger.error(f"❌ Exception updating price list: {e}")
            return {
                "status": "error",
                "message": str(e),
                "part_num": part_num,
                "list_code": list_code
            }

    def update_supplier_part_price(
        self,
        supplier_id: str,
        part_num: str,
        new_price: float,
        effective_date: str,
        uom_code: str = "EA"
    ) -> Dict[str, Any]:
        """
        Complete 4-step workflow to update supplier part price with effective date

        This method implements the workflow from the diagram:
        Step A: Supplier Verification - Verify supplier-part relationship
        Step B: Price List Creation - Check if price list exists, create if needed
        Step C: Effective Date Management - Update header-level effective dates
        Step D: Price Update - Update part price (inherits dates from header)

        Args:
            supplier_id: Supplier's external ID (VendorVendorID, e.g., "FAST1")
            part_num: Part number to update
            new_price: New price
            effective_date: Effective date in ISO format (e.g., "2025-10-20")
            uom_code: Unit of measure code (default: "EA")

        Returns:
            Dictionary with status and detailed results
        """
        try:
            logger.info("="*80)
            logger.info(f"🚀 STAGE 3: EPICOR SYSTEM INTEGRATION - 4-STEP WORKFLOW")
            logger.info("="*80)
            logger.info(f"   Supplier: {supplier_id}")
            logger.info(f"   Part: {part_num}")
            logger.info(f"   New Price: ${new_price}")
            logger.info(f"   Effective Date: {effective_date}")
            logger.info("-"*80)

            # ========== STEP A: SUPPLIER VERIFICATION ==========
            logger.info(f"📋 STEP A: SUPPLIER VERIFICATION")
            logger.info(f"   🔄 Retrieving vendor number...")
            supplier_part = self.verify_supplier_part(supplier_id, part_num)

            if not supplier_part:
                logger.error(f"❌ Step A Failed: Supplier-part relationship not found")
                return {
                    "status": "error",
                    "message": f"Supplier-part relationship not found for Supplier={supplier_id}, Part={part_num}",
                    "part_num": part_num,
                    "supplier_id": supplier_id,
                    "step_failed": "Step A: Supplier Verification"
                }

            vendor_num = supplier_part.get("VendorNum")
            vendor_name = supplier_part.get("VendorName")
            logger.info(f"✅ STEP A COMPLETE")
            logger.info(f"   VendorNum: {vendor_num}")
            logger.info(f"   VendorName: {vendor_name}")
            logger.info("-"*80)

            # ========== STEP B: PRICE LIST CREATION ==========
            logger.info(f"📋 STEP B: PRICE LIST CREATION")

            # First, determine which price list to use
            price_lists = self.get_price_list_parts(part_num)

            if price_lists and len(price_lists) > 0:
                list_code = price_lists[0].get("ListCode")
                logger.info(f"   ℹ️  Found existing price list: {list_code}")
            else:
                list_code = self.default_price_list
                logger.info(f"   ℹ️  Using default price list: {list_code}")

            # Check if price list entry exists (Step B decision point)
            price_list_exists = self.check_price_list_exists(list_code, part_num, uom_code)

            if not price_list_exists:
                logger.info(f"   🔄 Creating new price list entry...")
                # Create new price list entry following template workflow
                create_result = self.create_price_list_entry(
                    part_num=part_num,
                    base_price=new_price,
                    effective_date=effective_date,
                    uom_code=uom_code,
                    list_code=list_code
                )

                if create_result.get("status") != "success":
                    logger.error(f"❌ Step B Failed: Could not create price list entry")
                    return {
                        "status": "error",
                        "message": f"Failed to create price list entry: {create_result.get('message')}",
                        "part_num": part_num,
                        "supplier_id": supplier_id,
                        "vendor_num": vendor_num,
                        "step_failed": "Step B: Price List Creation"
                    }

                logger.info(f"✅ STEP B COMPLETE: Price list entry created")
                logger.info(f"   ListCode: {list_code}")
                logger.info("-"*80)

                # For newly created entries, return success
                # (effective date and price already set during creation)
                return {
                    "status": "success",
                    "message": f"Price list entry created with price and effective date",
                    "part_num": part_num,
                    "supplier_id": supplier_id,
                    "vendor_num": vendor_num,
                    "vendor_name": vendor_name,
                    "old_price": None,
                    "new_price": new_price,
                    "workflow": "4-Step Workflow (Created New Entry)",
                    "effective_date": effective_date,
                    "list_code": list_code
                }

            logger.info(f"✅ STEP B COMPLETE: Price list entry exists")
            logger.info(f"   ListCode: {list_code}")
            logger.info("-"*80)

            # ========== STEP C: EFFECTIVE DATE MANAGEMENT ==========
            logger.info(f"📋 STEP C: EFFECTIVE DATE MANAGEMENT")
            logger.info(f"   🔄 Updating header-level effective dates...")

            # Update the price list header with effective dates
            header_result = self.update_price_list_header_dates(
                list_code=list_code,
                start_date=effective_date
            )

            if header_result.get("status") != "success":
                logger.warning(f"⚠️  Step C Warning: Could not update header dates")
                logger.warning(f"   {header_result.get('message')}")
                logger.warning(f"   Continuing with price update...")
            else:
                logger.info(f"✅ STEP C COMPLETE: Header dates updated")
                logger.info(f"   StartDate: {effective_date}")

            logger.info("-"*80)

            # ========== STEP D: PRICE UPDATE ==========
            logger.info(f"📋 STEP D: PRICE UPDATE")
            logger.info(f"   🔄 Updating part price (inherits dates from header)...")

            # Update the part price (which inherits effective dates from header)
            update_result = self.update_price_list(
                list_code=list_code,
                part_num=part_num,
                new_price=new_price,
                effective_date=effective_date,  # For backward compatibility
                uom_code=uom_code
            )

            if update_result["status"] == "success":
                logger.info(f"✅ STEP D COMPLETE: Price updated successfully")
                logger.info("="*80)
                logger.info(f"✅ 4-STEP WORKFLOW COMPLETE")
                logger.info("="*80)

                # Enhance result with supplier info and workflow details
                update_result["supplier_id"] = supplier_id
                update_result["vendor_num"] = vendor_num
                update_result["vendor_name"] = vendor_name
                update_result["workflow"] = "4-Step Workflow (A→B→C→D)"
                return update_result
            else:
                logger.error(f"❌ Step D Failed: {update_result.get('message')}")
                logger.error("="*80)
                update_result["supplier_id"] = supplier_id
                update_result["vendor_num"] = vendor_num
                update_result["step_failed"] = "Step D: Price Update"
                return update_result

        except Exception as e:
            logger.error(f"❌ Exception in 4-step workflow: {e}")
            logger.error("="*80)
            return {
                "status": "error",
                "message": str(e),
                "part_num": part_num,
                "supplier_id": supplier_id
            }

    def batch_update_prices(
        self,
        products: List[Dict[str, Any]],
        supplier_id: Optional[str] = None,
        effective_date: Optional[str] = None,
        use_new_workflow: bool = True
    ) -> Dict[str, Any]:
        """
        Update multiple part prices from extracted email data

        Args:
            products: List of product dictionaries with product_id, new_price, etc.
            supplier_id: Supplier's external ID (VendorVendorID, e.g., "FAST1")
            effective_date: Effective date for price changes (ISO format)
            use_new_workflow: If True, use new PriceLstSvc workflow; if False, use legacy PartSvc

        Returns:
            Dictionary with batch update results
        """
        results = {
            "total": len(products),
            "successful": 0,
            "failed": 0,
            "skipped": 0,
            "details": [],
            "workflow_used": "PriceLstSvc (new)" if use_new_workflow else "PartSvc (legacy)"
        }

        # Log workflow information
        if use_new_workflow:
            logger.info(f"🔄 Using NEW workflow: PriceLstSvc with supplier verification and effective dates")
            logger.info(f"   Supplier ID: {supplier_id or 'Not provided'}")
            logger.info(f"   Effective Date: {effective_date or 'Not provided'}")
        else:
            logger.info(f"🔄 Using LEGACY workflow: PartSvc (direct part price update)")

        for product in products:
            # Try product_id first, fallback to product_code for backward compatibility
            part_num = product.get("product_id") or product.get("product_code")
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

            # Choose workflow based on parameters
            if use_new_workflow and supplier_id and effective_date:
                # NEW WORKFLOW: Use PriceLstSvc with supplier verification
                update_result = self.update_supplier_part_price(
                    supplier_id=supplier_id,
                    part_num=part_num,
                    new_price=new_price,
                    effective_date=effective_date
                )
            else:
                # LEGACY WORKFLOW: Use PartSvc (backward compatibility)
                if use_new_workflow:
                    logger.warning(f"⚠️ Missing supplier_id or effective_date for {part_num}, falling back to legacy workflow")
                update_result = self.update_part_price(part_num, new_price)

            if update_result["status"] == "success":
                results["successful"] += 1
            else:
                results["failed"] += 1

            # Build detail entry
            detail = {
                "part_num": part_num,
                "product": product.get("product_name", "Unknown"),
                "status": update_result["status"],
                "old_price": update_result.get("old_price"),
                "new_price": new_price,
                "message": update_result.get("message")
            }

            # Add new workflow specific fields if available
            if "effective_date" in update_result:
                detail["effective_date"] = update_result["effective_date"]
            if "supplier_id" in update_result:
                detail["supplier_id"] = update_result["supplier_id"]
            if "vendor_name" in update_result:
                detail["vendor_name"] = update_result["vendor_name"]
            if "list_code" in update_result:
                detail["list_code"] = update_result["list_code"]

            results["details"].append(detail)

        logger.info(f"📊 Batch update complete: {results['successful']} successful, {results['failed']} failed, {results['skipped']} skipped")

        return results


# Global instance
epicor_service = EpicorAPIService()

