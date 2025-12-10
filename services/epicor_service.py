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

        # Load margin thresholds from environment with defaults
        # These define the margin percentage levels for risk classification
        self.margin_thresholds = {
            "critical": float(os.getenv("MARGIN_THRESHOLD_CRITICAL", "10.0")),  # < 10% = critical
            "high": float(os.getenv("MARGIN_THRESHOLD_HIGH", "15.0")),          # 10-15% = high
            "medium": float(os.getenv("MARGIN_THRESHOLD_MEDIUM", "20.0"))       # 15-20% = medium, > 20% = low
        }

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
        logger.info(f"   Margin Thresholds: Critical<{self.margin_thresholds['critical']}%, High<{self.margin_thresholds['high']}%, Medium<{self.margin_thresholds['medium']}%")
    
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
            # Use filter query instead of key lookup to handle special characters like #
            url = f"{self.base_url}/{self.company_id}/Erp.BO.PartSvc/Parts"
            headers = self._get_headers()

            params = {
                "$filter": f"Company eq '{self.company_id}' and PartNum eq '{part_num}'",
                "$top": 1
            }

            response = requests.get(url, headers=headers, params=params, timeout=10)

            if response.status_code == 200:
                data = response.json()
                parts = data.get("value", [])
                if parts:
                    logger.info(f"✅ Retrieved part: {part_num}")
                    return parts[0]
                else:
                    logger.warning(f"⚠️ Part not found: {part_num}")
                    return None
            elif response.status_code == 404:
                logger.warning(f"⚠️ Part not found: {part_num}")
                return None
            else:
                logger.error(f"❌ Error retrieving part {part_num}: {response.status_code} - {response.text}")
                return None

        except Exception as e:
            logger.error(f"❌ Exception retrieving part {part_num}: {e}")
            return None

    def get_part_where_used(self, part_num: str) -> List[Dict[str, Any]]:
        """
        Find direct parent assemblies that use a given component part.

        Calls the Epicor GetPartWhereUsed endpoint to perform BOM implosion
        (find which assemblies contain this part as a component).

        Args:
            part_num: Component part number to look up

        Returns:
            List of parent assemblies with fields:
            - PartNum: Parent assembly part number
            - RevisionNum: Revision of the parent assembly
            - QtyPer: Quantity of the component used per parent assembly
            - CanTrackUp: Boolean indicating if this parent has further parents (for multi-level traversal)
            - Description: Parent assembly description
            - MtlSeq: Material sequence number in the BOM
        """
        try:
            logger.info(f"🔍 Finding assemblies that use part: {part_num}")

            # Build the endpoint URL for GetPartWhereUsed action
            url = f"{self.base_url}/{self.company_id}/Erp.BO.PartSvc/GetPartWhereUsed"
            headers = self._get_headers()

            # Build the request body
            payload = {
                "whereUsedPartNum": part_num,
                "pageSize": 0,       # 0 = return all results
                "absolutePage": 0
            }

            logger.info(f"   Calling GetPartWhereUsed endpoint...")
            response = requests.post(url, json=payload, headers=headers, timeout=30)

            if response.status_code == 200:
                data = response.json()

                # Extract the PartWhereUsed array from returnObj
                return_obj = data.get("returnObj", {})
                where_used_list = return_obj.get("PartWhereUsed", [])

                if not where_used_list:
                    logger.info(f"   ℹ️  No parent assemblies found for part {part_num}")
                    return []

                # Parse and normalize the results
                results = []
                for item in where_used_list:
                    parent_info = {
                        "PartNum": item.get("PartNum", ""),
                        "RevisionNum": item.get("RevisionNum", ""),
                        "QtyPer": float(item.get("QtyPer", 1.0)),
                        "CanTrackUp": item.get("CanTrackUp", False),
                        "Description": item.get("Description", "") or item.get("PartDescription", ""),
                        "MtlSeq": item.get("MtlSeq", 0),
                        "MtlPartNum": item.get("MtlPartNum", part_num)
                    }
                    results.append(parent_info)

                logger.info(f"✅ Found {len(results)} parent assemblies for part {part_num}")
                for r in results[:5]:  # Log first 5 for brevity
                    logger.info(f"   - {r['PartNum']} (Rev: {r['RevisionNum']}, QtyPer: {r['QtyPer']}, CanTrackUp: {r['CanTrackUp']})")
                if len(results) > 5:
                    logger.info(f"   ... and {len(results) - 5} more")

                return results

            elif response.status_code == 404:
                logger.warning(f"⚠️ GetPartWhereUsed endpoint not found - verify API version")
                return []
            else:
                logger.error(f"❌ Error calling GetPartWhereUsed: {response.status_code}")
                logger.error(f"   Response: {response.text[:500]}")
                return []

        except requests.exceptions.Timeout:
            logger.error(f"❌ Timeout calling GetPartWhereUsed for part {part_num}")
            return []
        except Exception as e:
            logger.error(f"❌ Exception in get_part_where_used for {part_num}: {e}")
            return []

    def find_all_affected_assemblies(
        self,
        part_num: str,
        max_levels: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Recursively find ALL assemblies (direct and indirect) affected by a component.

        Performs multi-level BOM traversal using GetPartWhereUsed to find:
        - Direct parent assemblies that use the component
        - Indirect parent assemblies (assemblies that use the direct parents)
        - Continues up the BOM hierarchy until no more parents or max_levels reached

        Calculates cumulative quantity at each level (multiplies QtyPer as we traverse up).

        Args:
            part_num: Component part number to start from
            max_levels: Maximum BOM levels to traverse (default 10, prevents infinite loops)

        Returns:
            List of dictionaries containing:
            - assembly_part_num: Parent assembly part number
            - revision: Assembly revision
            - qty_per: Quantity per (at this direct level)
            - cumulative_qty: Cumulative quantity from original component to this assembly
            - bom_level: BOM level (1 = direct parent, 2 = grandparent, etc.)
            - direct_parent_of: The part this assembly directly contains
            - can_track_up: Whether this assembly has further parents
            - description: Assembly description
        """
        logger.info(f"🔍 Finding ALL affected assemblies for part: {part_num}")
        logger.info(f"   Max traversal levels: {max_levels}")

        all_affected = []
        visited = set()  # Track visited parts to prevent circular references

        def traverse(current_part: str, level: int, cumulative_qty: float, parent_chain: List[str]):
            """Recursive helper function to traverse BOM hierarchy"""

            # Prevent infinite loops and excessive depth
            if current_part in visited:
                logger.debug(f"   Skipping already visited part: {current_part}")
                return
            if level > max_levels:
                logger.warning(f"⚠️ Max level ({max_levels}) reached at part {current_part}")
                return

            visited.add(current_part)

            # Get direct parents of current part
            parents = self.get_part_where_used(current_part)

            if not parents:
                logger.debug(f"   No parents found for {current_part} at level {level}")
                return

            for parent in parents:
                parent_part = parent.get("PartNum", "")
                if not parent_part:
                    continue

                # Skip if this parent is in our traversal chain (circular reference)
                if parent_part in parent_chain:
                    logger.warning(f"⚠️ Circular reference detected: {parent_part} already in chain")
                    continue

                qty_per = parent.get("QtyPer", 1.0)
                total_qty = cumulative_qty * qty_per
                can_track_up = parent.get("CanTrackUp", False)

                # Build the affected assembly entry
                affected_entry = {
                    "assembly_part_num": parent_part,
                    "revision": parent.get("RevisionNum", ""),
                    "qty_per": qty_per,
                    "cumulative_qty": total_qty,
                    "bom_level": level,
                    "direct_parent_of": current_part,
                    "can_track_up": can_track_up,
                    "description": parent.get("Description", ""),
                    "mtl_seq": parent.get("MtlSeq", 0)
                }

                all_affected.append(affected_entry)

                logger.debug(f"   Level {level}: {parent_part} (QtyPer: {qty_per}, Cumulative: {total_qty}, CanTrackUp: {can_track_up})")

                # Recursively check if this parent has parents
                if can_track_up:
                    new_chain = parent_chain + [parent_part]
                    traverse(parent_part, level + 1, total_qty, new_chain)

        # Start traversal from the component part
        try:
            traverse(part_num, 1, 1.0, [part_num])

            # Log summary
            if all_affected:
                # Count assemblies by level
                level_counts = {}
                for item in all_affected:
                    lvl = item["bom_level"]
                    level_counts[lvl] = level_counts.get(lvl, 0) + 1

                logger.info(f"✅ Found {len(all_affected)} total affected assemblies for {part_num}")
                for lvl in sorted(level_counts.keys()):
                    logger.info(f"   Level {lvl}: {level_counts[lvl]} assemblies")
            else:
                logger.info(f"ℹ️  No affected assemblies found for part {part_num}")

            return all_affected

        except Exception as e:
            logger.error(f"❌ Exception in find_all_affected_assemblies: {e}")
            return all_affected  # Return what we found so far

    def calculate_assembly_cost_impact(
        self,
        component_price_delta: float,
        qty_per_assembly: float,
        assembly_part_num: str
    ) -> Dict[str, Any]:
        """
        Calculate how a component price change affects an assembly's cost.

        Args:
            component_price_delta: Price difference (new_price - old_price)
            qty_per_assembly: Quantity of component used per assembly (from BOM)
            assembly_part_num: Assembly part number to analyze

        Returns:
            Dictionary containing:
            - assembly_part_num: The assembly analyzed
            - current_cost: Current assembly cost from Epicor
            - cost_increase_per_unit: Cost increase per assembly unit
            - new_assembly_cost: Projected new assembly cost
            - cost_increase_pct: Percentage cost increase
            - cost_field_used: Which cost field was used (StdCost or AvgMaterialCost)
        """
        try:
            logger.info(f"💰 Calculating cost impact for assembly: {assembly_part_num}")
            logger.info(f"   Price delta: ${component_price_delta:.4f}, QtyPer: {qty_per_assembly}")

            # Get assembly's current cost from Epicor
            assembly_data = self.get_part(assembly_part_num)

            if not assembly_data:
                logger.warning(f"⚠️ Assembly {assembly_part_num} not found in Epicor")
                return {
                    "assembly_part_num": assembly_part_num,
                    "error": f"Assembly {assembly_part_num} not found",
                    "current_cost": 0,
                    "cost_increase_per_unit": component_price_delta * qty_per_assembly,
                    "new_assembly_cost": 0,
                    "cost_increase_pct": 0,
                    "cost_field_used": None
                }

            # Try StdCost first, fall back to AvgMaterialCost
            current_cost = assembly_data.get("StdCost")
            cost_field_used = "StdCost"

            if current_cost is None or current_cost == 0:
                current_cost = assembly_data.get("AvgMaterialCost", 0)
                cost_field_used = "AvgMaterialCost"

            if current_cost is None:
                current_cost = 0
                cost_field_used = "None (defaulted to 0)"

            # Calculate cost impact
            cost_increase_per_unit = component_price_delta * qty_per_assembly
            new_assembly_cost = current_cost + cost_increase_per_unit

            # Calculate percentage increase (handle zero cost)
            if current_cost > 0:
                cost_increase_pct = (cost_increase_per_unit / current_cost) * 100
            else:
                cost_increase_pct = 0 if cost_increase_per_unit == 0 else 100  # 100% if going from 0 to something

            logger.info(f"   Current cost (${cost_field_used}): ${current_cost:.4f}")
            logger.info(f"   Cost increase: ${cost_increase_per_unit:.4f} ({cost_increase_pct:.2f}%)")
            logger.info(f"   New projected cost: ${new_assembly_cost:.4f}")

            return {
                "assembly_part_num": assembly_part_num,
                "assembly_description": assembly_data.get("PartDescription", ""),
                "current_cost": round(current_cost, 4),
                "cost_increase_per_unit": round(cost_increase_per_unit, 4),
                "new_assembly_cost": round(new_assembly_cost, 4),
                "cost_increase_pct": round(cost_increase_pct, 2),
                "cost_field_used": cost_field_used
            }

        except Exception as e:
            logger.error(f"❌ Exception calculating cost impact for {assembly_part_num}: {e}")
            return {
                "assembly_part_num": assembly_part_num,
                "error": str(e),
                "current_cost": 0,
                "cost_increase_per_unit": component_price_delta * qty_per_assembly,
                "new_assembly_cost": 0,
                "cost_increase_pct": 0,
                "cost_field_used": None
            }

    def calculate_annual_impact(
        self,
        price_delta: float,
        affected_assemblies: List[Dict[str, Any]],
        weekly_demand_override: Optional[Dict[str, float]] = None,
        use_forecast: bool = False
    ) -> Dict[str, Any]:
        """
        Estimate the annual financial impact of a component price change.

        Formula: Annual Cost Delta = Price Difference × Cumulative Qty × Weekly Demand × 52

        Args:
            price_delta: Component price difference (new_price - old_price)
            affected_assemblies: List from find_all_affected_assemblies()
            weekly_demand_override: Optional dict mapping assembly_part_num to weekly demand
                                   (overrides forecast data if provided for a specific part)
            use_forecast: If True, automatically fetch forecast data from Epicor
                         for assemblies without override values (default: False)

        Returns:
            Dictionary containing:
            - total_annual_impact: Sum of annual impact across all assemblies
            - total_assemblies_impacted: Count of affected assemblies
            - impact_by_assembly: Detailed breakdown for each assembly
        """
        try:
            logger.info(f"📊 Calculating annual impact for {len(affected_assemblies)} assemblies")
            logger.info(f"   Price delta: ${price_delta:.4f}")

            if weekly_demand_override:
                logger.info(f"   Using demand overrides for {len(weekly_demand_override)} assemblies")

            # If use_forecast is enabled, fetch forecast data for assemblies
            forecast_demand = {}
            if use_forecast:
                logger.info(f"   📈 Fetching forecast data from Epicor...")
                assembly_parts = [a.get("assembly_part_num", "") for a in affected_assemblies]
                # Remove duplicates
                unique_parts = list(set(p for p in assembly_parts if p))
                forecast_demand = self.get_assembly_demand(unique_parts)

            total_annual_impact = 0.0
            impact_by_assembly = []

            for assembly in affected_assemblies:
                assembly_part = assembly.get("assembly_part_num", "")
                cumulative_qty = assembly.get("cumulative_qty", assembly.get("qty_per", 1.0))

                # Determine weekly demand with priority:
                # 1. Override (if provided for this part)
                # 2. Forecast data (if use_forecast=True and data exists)
                # 3. Default to 0
                demand_source = "default"
                weekly_demand = 0.0

                if weekly_demand_override and assembly_part in weekly_demand_override:
                    weekly_demand = weekly_demand_override[assembly_part]
                    demand_source = "override"
                elif use_forecast and assembly_part in forecast_demand:
                    weekly_demand = forecast_demand[assembly_part]
                    demand_source = "forecast" if weekly_demand > 0 else "forecast_zero"

                # Calculate annual impact
                # Impact = Price Delta × Cumulative Qty × Weekly Demand × 52 weeks
                annual_demand = weekly_demand * 52
                annual_impact = price_delta * cumulative_qty * annual_demand

                total_annual_impact += annual_impact

                impact_entry = {
                    "assembly_part_num": assembly_part,
                    "revision": assembly.get("revision", ""),
                    "bom_level": assembly.get("bom_level", 0),
                    "qty_per": assembly.get("qty_per", 1.0),
                    "cumulative_qty": cumulative_qty,
                    "weekly_demand": weekly_demand,
                    "annual_demand": annual_demand,
                    "cost_increase_per_unit": round(price_delta * cumulative_qty, 4),
                    "annual_cost_impact": round(annual_impact, 2),
                    "demand_source": demand_source
                }

                impact_by_assembly.append(impact_entry)

                if weekly_demand > 0:
                    logger.debug(f"   {assembly_part}: Weekly={weekly_demand}, Annual Impact=${annual_impact:.2f}")

            # Sort by annual impact (highest first)
            impact_by_assembly.sort(key=lambda x: x["annual_cost_impact"], reverse=True)

            # Log summary
            assemblies_with_demand = sum(1 for a in impact_by_assembly if a["weekly_demand"] > 0)
            forecast_sources = sum(1 for a in impact_by_assembly if a["demand_source"] == "forecast")
            logger.info(f"✅ Annual impact calculation complete")
            logger.info(f"   Total assemblies: {len(affected_assemblies)}")
            logger.info(f"   Assemblies with demand data: {assemblies_with_demand}")
            if use_forecast:
                logger.info(f"   Demand from forecast: {forecast_sources}")
            logger.info(f"   Total annual impact: ${total_annual_impact:,.2f}")

            return {
                "total_annual_impact": round(total_annual_impact, 2),
                "total_assemblies_impacted": len(affected_assemblies),
                "assemblies_with_demand_data": assemblies_with_demand,
                "demand_from_forecast": forecast_sources if use_forecast else 0,
                "impact_by_assembly": impact_by_assembly,
                "price_delta": price_delta,
                "calculation_note": "Annual Impact = Price Delta × Cumulative Qty × Weekly Demand × 52"
            }

        except Exception as e:
            logger.error(f"❌ Exception calculating annual impact: {e}")
            return {
                "total_annual_impact": 0,
                "total_assemblies_impacted": len(affected_assemblies) if affected_assemblies else 0,
                "assemblies_with_demand_data": 0,
                "impact_by_assembly": [],
                "error": str(e)
            }

    def get_part_forecast(
        self,
        part_num: str,
        weeks_ahead: int = 52,
        plant: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get forecast/planned demand for a part from Epicor ForecastSvc.

        Retrieves forecast quantities for the specified part and calculates
        weekly demand based on future forecasts.

        Args:
            part_num: Part number to get forecast for
            weeks_ahead: Number of weeks to look ahead (default: 52 for annual)
            plant: Optional plant code to filter by

        Returns:
            Dictionary containing:
            - total_forecast_qty: Sum of all forecast quantities
            - weekly_demand: Calculated average weekly demand
            - forecast_records: Number of forecast records found
            - forecasts: List of individual forecast entries
            - data_source: "epicor_forecast"
        """
        try:
            logger.info(f"📊 Getting forecast for part: {part_num}")

            url = f"{self.base_url}/{self.company_id}/Erp.BO.ForecastSvc/Forecasts"
            headers = self._get_headers()

            # Build filter - get forecasts for this part with future dates
            from datetime import datetime, timedelta, timezone
            today = datetime.now(timezone.utc)
            end_date = today + timedelta(weeks=weeks_ahead)

            # Format dates for OData filter with timezone (Epicor requires timezone offset)
            today_str = today.strftime("%Y-%m-%dT00:00:00Z")
            end_date_str = end_date.strftime("%Y-%m-%dT00:00:00Z")

            filter_parts = [
                f"PartNum eq '{part_num}'",
                f"ForeDate ge {today_str}",
                f"ForeDate le {end_date_str}"
            ]

            if plant:
                filter_parts.append(f"Plant eq '{plant}'")

            params = {
                "$filter": " and ".join(filter_parts),
                "$select": "PartNum,ForeDate,ForeQty,ForeQtyUOM,Plant,CustNum,CustomerName",
                "$orderby": "ForeDate asc"
            }

            logger.info(f"   Querying forecasts from {today.date()} to {end_date.date()}")

            response = requests.get(url, headers=headers, params=params, timeout=15)

            if response.status_code == 200:
                data = response.json()
                forecasts = data.get("value", [])

                # Calculate totals
                total_qty = sum(float(f.get("ForeQty", 0)) for f in forecasts)
                weekly_demand = total_qty / weeks_ahead if weeks_ahead > 0 else 0

                logger.info(f"✅ Found {len(forecasts)} forecast records for {part_num}")
                logger.info(f"   Total forecast qty: {total_qty}")
                logger.info(f"   Avg weekly demand: {weekly_demand:.2f}")

                return {
                    "part_num": part_num,
                    "total_forecast_qty": round(total_qty, 2),
                    "weekly_demand": round(weekly_demand, 4),
                    "annual_demand": round(total_qty, 2),
                    "weeks_covered": weeks_ahead,
                    "forecast_records": len(forecasts),
                    "forecasts": forecasts,
                    "data_source": "epicor_forecast"
                }

            elif response.status_code == 404:
                logger.info(f"   ℹ️ No forecasts found for part {part_num}")
                return {
                    "part_num": part_num,
                    "total_forecast_qty": 0,
                    "weekly_demand": 0,
                    "annual_demand": 0,
                    "weeks_covered": weeks_ahead,
                    "forecast_records": 0,
                    "forecasts": [],
                    "data_source": "epicor_forecast",
                    "message": "No forecast data available"
                }
            else:
                logger.error(f"❌ Error getting forecast: {response.status_code} - {response.text[:200]}")
                return {
                    "part_num": part_num,
                    "total_forecast_qty": 0,
                    "weekly_demand": 0,
                    "annual_demand": 0,
                    "forecast_records": 0,
                    "forecasts": [],
                    "error": f"API error: {response.status_code}"
                }

        except Exception as e:
            logger.error(f"❌ Exception getting forecast for {part_num}: {e}")
            return {
                "part_num": part_num,
                "total_forecast_qty": 0,
                "weekly_demand": 0,
                "annual_demand": 0,
                "forecast_records": 0,
                "forecasts": [],
                "error": str(e)
            }

    def get_assembly_demand(
        self,
        assembly_part_nums: List[str],
        weeks_ahead: int = 52
    ) -> Dict[str, float]:
        """
        Get weekly demand for multiple assemblies from Epicor forecasts.

        Convenience method that retrieves forecast data for a list of assemblies
        and returns a dictionary mapping part numbers to weekly demand.
        This can be passed directly to calculate_annual_impact().

        Args:
            assembly_part_nums: List of assembly part numbers
            weeks_ahead: Number of weeks to look ahead (default: 52)

        Returns:
            Dictionary mapping assembly_part_num to weekly_demand
            Example: {"ASSY-001": 25.5, "ASSY-002": 12.0}
        """
        logger.info(f"📊 Getting demand data for {len(assembly_part_nums)} assemblies")

        demand_data = {}

        for part_num in assembly_part_nums:
            forecast = self.get_part_forecast(part_num, weeks_ahead)
            weekly_demand = forecast.get("weekly_demand", 0)
            demand_data[part_num] = weekly_demand

            if weekly_demand > 0:
                logger.debug(f"   {part_num}: {weekly_demand:.2f}/week")

        assemblies_with_demand = sum(1 for d in demand_data.values() if d > 0)
        logger.info(f"✅ Retrieved demand for {assemblies_with_demand}/{len(assembly_part_nums)} assemblies")

        return demand_data

    def check_margin_erosion(
        self,
        assembly_part_num: str,
        cost_increase: float,
        margin_thresholds: Optional[Dict[str, float]] = None
    ) -> Dict[str, Any]:
        """
        Check if a cost increase will cause margin erosion below acceptable thresholds.

        Margin thresholds are loaded from environment variables by default:
        - MARGIN_THRESHOLD_CRITICAL (default 10%): < this = critical risk
        - MARGIN_THRESHOLD_HIGH (default 15%): < this = high risk
        - MARGIN_THRESHOLD_MEDIUM (default 20%): < this = medium risk, >= this = low risk

        Args:
            assembly_part_num: Assembly part number to check
            cost_increase: Cost increase per unit from component price change
            margin_thresholds: Optional custom thresholds dict (overrides env vars)
                               Keys: critical, high, medium

        Returns:
            Dictionary containing:
            - assembly_part_num: The assembly analyzed
            - current_cost, new_cost, selling_price: Financial data
            - current_margin_pct, new_margin_pct, margin_change_pct: Margin analysis
            - risk_level: "critical", "high", "medium", or "low"
            - requires_review: Boolean indicating if human review is needed
            - recommendation: Human-readable recommendation text
        """
        try:
            logger.info(f"📉 Checking margin erosion for assembly: {assembly_part_num}")
            logger.info(f"   Cost increase: ${cost_increase:.4f}")

            # Use provided thresholds, or fall back to instance thresholds (from env vars)
            if margin_thresholds is None:
                margin_thresholds = self.margin_thresholds

            # Get assembly's current cost and selling price from Epicor
            assembly_data = self.get_part(assembly_part_num)

            if not assembly_data:
                logger.warning(f"⚠️ Assembly {assembly_part_num} not found")
                return {
                    "assembly_part_num": assembly_part_num,
                    "error": f"Assembly {assembly_part_num} not found",
                    "risk_level": "unknown",
                    "requires_review": True,
                    "recommendation": "Cannot analyze - assembly not found in Epicor"
                }

            # Get cost (try StdCost first, then AvgMaterialCost)
            current_cost = assembly_data.get("StdCost")
            if current_cost is None or current_cost == 0:
                current_cost = assembly_data.get("AvgMaterialCost", 0) or 0

            # Get selling price
            selling_price = assembly_data.get("UnitPrice", 0) or 0

            # Handle missing selling price
            if selling_price <= 0:
                logger.warning(f"⚠️ No selling price defined for {assembly_part_num}")
                return {
                    "assembly_part_num": assembly_part_num,
                    "assembly_description": assembly_data.get("PartDescription", ""),
                    "current_cost": round(current_cost, 4),
                    "new_cost": round(current_cost + cost_increase, 4),
                    "cost_increase": round(cost_increase, 4),
                    "selling_price": 0,
                    "current_margin_pct": 0,
                    "new_margin_pct": 0,
                    "margin_change_pct": 0,
                    "risk_level": "unknown",
                    "requires_review": True,
                    "recommendation": "Cannot calculate margin - no selling price defined",
                    "thresholds_used": margin_thresholds
                }

            # Calculate margins
            new_cost = current_cost + cost_increase
            current_margin = ((selling_price - current_cost) / selling_price) * 100
            new_margin = ((selling_price - new_cost) / selling_price) * 100
            margin_change = new_margin - current_margin

            # Determine risk level based on NEW margin
            if new_margin < margin_thresholds["critical"]:
                risk_level = "critical"
                recommendation = f"🚨 CRITICAL: Margin ({new_margin:.1f}%) below {margin_thresholds['critical']}%. Require executive approval or consider selling price increase."
            elif new_margin < margin_thresholds["high"]:
                risk_level = "high"
                recommendation = f"⚠️ HIGH RISK: Margin ({new_margin:.1f}%) between {margin_thresholds['critical']}-{margin_thresholds['high']}%. Manager approval required."
            elif new_margin < margin_thresholds["medium"]:
                risk_level = "medium"
                recommendation = f"ℹ️ REVIEW: Margin ({new_margin:.1f}%) between {margin_thresholds['high']}-{margin_thresholds['medium']}%. Monitor closely."
            else:
                risk_level = "low"
                recommendation = f"✅ OK: Margin ({new_margin:.1f}%) above {margin_thresholds['medium']}%. Within acceptable range."

            logger.info(f"   Selling price: ${selling_price:.4f}")
            logger.info(f"   Current cost: ${current_cost:.4f} → New cost: ${new_cost:.4f}")
            logger.info(f"   Margin: {current_margin:.1f}% → {new_margin:.1f}% (change: {margin_change:.1f}%)")
            logger.info(f"   Risk level: {risk_level.upper()}")

            return {
                "assembly_part_num": assembly_part_num,
                "assembly_description": assembly_data.get("PartDescription", ""),
                "current_cost": round(current_cost, 4),
                "new_cost": round(new_cost, 4),
                "cost_increase": round(cost_increase, 4),
                "selling_price": round(selling_price, 4),
                "current_margin_pct": round(current_margin, 2),
                "new_margin_pct": round(new_margin, 2),
                "margin_change_pct": round(margin_change, 2),
                "risk_level": risk_level,
                "requires_review": risk_level in ["critical", "high"],
                "recommendation": recommendation,
                "thresholds_used": margin_thresholds
            }

        except Exception as e:
            logger.error(f"❌ Exception checking margin erosion for {assembly_part_num}: {e}")
            return {
                "assembly_part_num": assembly_part_num,
                "error": str(e),
                "risk_level": "unknown",
                "requires_review": True,
                "recommendation": f"Error analyzing margin: {str(e)}"
            }

    def analyze_price_change_impact(
        self,
        part_num: str,
        old_price: float,
        new_price: float,
        weekly_demand_override: Optional[Dict[str, float]] = None,
        margin_thresholds: Optional[Dict[str, float]] = None,
        use_forecast: bool = True
    ) -> Dict[str, Any]:
        """
        Comprehensive BOM impact analysis for a component price change.

        This method ties together all BOM impact analysis:
        1. Find all affected assemblies (BOM implosion)
        2. Calculate cost impact for each assembly
        3. Check margin erosion risks for ALL affected assemblies
        4. Estimate annual financial impact using Epicor forecast data
        5. Generate summary and recommendations

        Args:
            part_num: Component part number with price change
            old_price: Previous component price
            new_price: New component price
            weekly_demand_override: Optional dict mapping assembly_part_num to weekly demand
                                   (overrides forecast data for specific assemblies)
            margin_thresholds: Optional custom margin thresholds (uses env vars if not provided)
            use_forecast: If True, automatically fetch forecast data from Epicor (default: True)

        Returns:
            Comprehensive impact analysis report (JSON-friendly for frontend):
            - component_part_num: Component that changed
            - old_price, new_price, price_delta, price_change_pct: Price change details
            - summary: High-level statistics and risk counts
            - impact_details: Detailed analysis for each affected assembly
            - annual_impact: Annual financial impact estimates
            - high_risk_assemblies: List of assemblies requiring review (critical/high)
            - recommendation: Overall recommendation text
            - thresholds_used: The margin thresholds applied
        """
        try:
            logger.info("="*80)
            logger.info("📊 BOM IMPACT ANALYSIS - COMPREHENSIVE REPORT")
            logger.info("="*80)
            logger.info(f"   Component: {part_num}")
            logger.info(f"   Old Price: ${old_price:.4f}")
            logger.info(f"   New Price: ${new_price:.4f}")

            price_delta = new_price - old_price
            price_change_pct = ((new_price - old_price) / old_price * 100) if old_price > 0 else 0

            logger.info(f"   Price Delta: ${price_delta:.4f} ({price_change_pct:+.2f}%)")
            logger.info("-"*80)

            # Step 1: Find all affected assemblies
            logger.info("📋 Step 1: Finding affected assemblies...")
            affected_assemblies = self.find_all_affected_assemblies(part_num)

            if not affected_assemblies:
                logger.info("ℹ️ No affected assemblies found - component may be a top-level part")
                return {
                    "component_part_num": part_num,
                    "old_price": old_price,
                    "new_price": new_price,
                    "price_delta": round(price_delta, 4),
                    "price_change_pct": round(price_change_pct, 2),
                    "summary": {
                        "total_assemblies_affected": 0,
                        "total_annual_cost_impact": 0,
                        "risk_summary": {"critical": 0, "high": 0, "medium": 0, "low": 0, "unknown": 0},
                        "requires_approval": False
                    },
                    "impact_details": [],
                    "annual_impact": {"total_annual_impact": 0},
                    "recommendation": "ℹ️ No assemblies affected - this part is not used as a component in any BOMs."
                }

            logger.info("-"*80)

            # Step 2 & 3: Calculate cost impact and check margins for each assembly
            logger.info("📋 Step 2-3: Calculating cost impact and margin erosion...")
            impact_details = []
            risk_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0, "unknown": 0}

            for assembly in affected_assemblies:
                assembly_part = assembly["assembly_part_num"]
                cumulative_qty = assembly.get("cumulative_qty", assembly.get("qty_per", 1.0))

                # Calculate cost impact using cumulative qty
                cost_increase = price_delta * cumulative_qty

                # Check margin erosion
                margin_check = self.check_margin_erosion(
                    assembly_part_num=assembly_part,
                    cost_increase=cost_increase,
                    margin_thresholds=margin_thresholds
                )

                # Track risk counts
                risk_level = margin_check.get("risk_level", "unknown")
                risk_counts[risk_level] = risk_counts.get(risk_level, 0) + 1

                # Build combined impact entry
                impact_entry = {
                    # From affected assembly
                    "assembly_part_num": assembly_part,
                    "revision": assembly.get("revision", ""),
                    "bom_level": assembly.get("bom_level", 0),
                    "qty_per": assembly.get("qty_per", 1.0),
                    "cumulative_qty": cumulative_qty,
                    "direct_parent_of": assembly.get("direct_parent_of", ""),
                    "description": assembly.get("description", "") or margin_check.get("assembly_description", ""),
                    # Cost impact
                    "cost_increase_per_unit": round(cost_increase, 4),
                    # From margin check
                    "current_cost": margin_check.get("current_cost", 0),
                    "new_cost": margin_check.get("new_cost", 0),
                    "selling_price": margin_check.get("selling_price", 0),
                    "current_margin_pct": margin_check.get("current_margin_pct", 0),
                    "new_margin_pct": margin_check.get("new_margin_pct", 0),
                    "margin_change_pct": margin_check.get("margin_change_pct", 0),
                    "risk_level": risk_level,
                    "requires_review": margin_check.get("requires_review", False),
                    "recommendation": margin_check.get("recommendation", "")
                }

                impact_details.append(impact_entry)

            logger.info("-"*80)

            # Step 4: Calculate annual impact with forecast data
            logger.info("📋 Step 4: Calculating annual financial impact...")
            if use_forecast:
                logger.info("   📈 Using Epicor forecast data for demand...")
            annual_impact_result = self.calculate_annual_impact(
                price_delta=price_delta,
                affected_assemblies=affected_assemblies,
                weekly_demand_override=weekly_demand_override,
                use_forecast=use_forecast
            )

            # Merge annual impact data into impact_details
            annual_by_assembly = {a["assembly_part_num"]: a for a in annual_impact_result.get("impact_by_assembly", [])}
            for detail in impact_details:
                assembly_part = detail["assembly_part_num"]
                if assembly_part in annual_by_assembly:
                    annual_data = annual_by_assembly[assembly_part]
                    detail["weekly_demand"] = annual_data.get("weekly_demand", 0)
                    detail["annual_demand"] = annual_data.get("annual_demand", 0)
                    detail["annual_cost_impact"] = annual_data.get("annual_cost_impact", 0)
                    detail["demand_source"] = annual_data.get("demand_source", "default")

            # Sort by risk level (critical first) then by annual impact
            risk_priority = {"critical": 0, "high": 1, "medium": 2, "low": 3, "unknown": 4}
            impact_details.sort(key=lambda x: (
                risk_priority.get(x.get("risk_level", "unknown"), 4),
                -x.get("annual_cost_impact", 0)
            ))

            logger.info("-"*80)

            # Build summary
            total_annual_impact = annual_impact_result.get("total_annual_impact", 0)
            requires_approval = risk_counts["critical"] > 0 or risk_counts["high"] > 0

            # Get thresholds used (for transparency)
            thresholds_used = margin_thresholds if margin_thresholds else self.margin_thresholds

            # Calculate data quality metrics
            assemblies_with_demand = annual_impact_result.get("assemblies_with_demand_data", 0)
            assemblies_without_demand = len(affected_assemblies) - assemblies_with_demand
            unknown_count = risk_counts.get("unknown", 0)

            # Data quality warning flag - true if any assemblies have missing data
            has_data_quality_issues = (unknown_count > 0 or assemblies_without_demand > 0)

            summary = {
                "total_assemblies_affected": len(affected_assemblies),
                "total_annual_cost_impact": total_annual_impact,
                "risk_summary": risk_counts,
                "requires_approval": requires_approval,
                "assemblies_with_demand_data": assemblies_with_demand,
                "assemblies_without_demand_data": assemblies_without_demand,
                "demand_from_forecast": annual_impact_result.get("demand_from_forecast", 0),
                "assemblies_with_unknown_risk": unknown_count,
                "has_data_quality_issues": has_data_quality_issues
            }

            # Extract high-risk assemblies (critical and high) for easy frontend access
            high_risk_assemblies = [
                {
                    "assembly_part_num": d["assembly_part_num"],
                    "description": d.get("description", ""),
                    "risk_level": d["risk_level"],
                    "current_margin_pct": d.get("current_margin_pct", 0),
                    "new_margin_pct": d.get("new_margin_pct", 0),
                    "margin_change_pct": d.get("margin_change_pct", 0),
                    "annual_cost_impact": d.get("annual_cost_impact", 0),
                    "recommendation": d.get("recommendation", "")
                }
                for d in impact_details
                if d.get("risk_level") in ["critical", "high"]
            ]

            # Generate overall recommendation
            recommendation = self._generate_impact_recommendation(risk_counts, total_annual_impact)

            logger.info("="*80)
            logger.info("📊 BOM IMPACT ANALYSIS COMPLETE")
            logger.info("="*80)
            logger.info(f"   Total assemblies affected: {len(affected_assemblies)}")
            logger.info(f"   Risk breakdown: Critical={risk_counts['critical']}, High={risk_counts['high']}, Medium={risk_counts['medium']}, Low={risk_counts['low']}")
            logger.info(f"   Total annual impact: ${total_annual_impact:,.2f}")
            logger.info(f"   Requires approval: {requires_approval}")
            logger.info(f"   High-risk assemblies: {len(high_risk_assemblies)}")
            logger.info("="*80)

            return {
                "component_part_num": part_num,
                "old_price": old_price,
                "new_price": new_price,
                "price_delta": round(price_delta, 4),
                "price_change_pct": round(price_change_pct, 2),
                "summary": summary,
                "impact_details": impact_details,
                "high_risk_assemblies": high_risk_assemblies,
                "annual_impact": annual_impact_result,
                "recommendation": recommendation,
                "thresholds_used": thresholds_used
            }

        except Exception as e:
            logger.error(f"❌ Exception in analyze_price_change_impact: {e}")
            return {
                "component_part_num": part_num,
                "old_price": old_price,
                "new_price": new_price,
                "price_delta": round(new_price - old_price, 4) if old_price and new_price else 0,
                "error": str(e),
                "summary": {
                    "total_assemblies_affected": 0,
                    "risk_summary": {},
                    "requires_approval": True
                },
                "impact_details": [],
                "recommendation": f"❌ Error during analysis: {str(e)}"
            }

    def _generate_impact_recommendation(
        self,
        risk_counts: Dict[str, int],
        total_annual_impact: float
    ) -> str:
        """
        Generate a human-readable recommendation based on impact analysis.

        Args:
            risk_counts: Dict with counts by risk level
            total_annual_impact: Total annual financial impact

        Returns:
            Recommendation string
        """
        if risk_counts.get("critical", 0) > 0:
            return (
                f"🚨 CRITICAL: {risk_counts['critical']} assemblies have margin below 10%. "
                f"Price update requires executive approval. Consider selling price adjustments. "
                f"Total annual impact: ${total_annual_impact:,.2f}"
            )
        elif risk_counts.get("high", 0) > 0:
            return (
                f"⚠️ HIGH RISK: {risk_counts['high']} assemblies have margin between 10-15%. "
                f"Manager approval required before proceeding. "
                f"Total annual impact: ${total_annual_impact:,.2f}"
            )
        elif risk_counts.get("medium", 0) > 0:
            return (
                f"ℹ️ REVIEW: {risk_counts['medium']} assemblies approaching margin threshold (15-20%). "
                f"Monitor closely after update. "
                f"Total annual impact: ${total_annual_impact:,.2f}"
            )
        else:
            low_count = risk_counts.get("low", 0)
            unknown_count = risk_counts.get("unknown", 0)
            if low_count > 0:
                return (
                    f"✅ LOW RISK: All {low_count} assemblies maintain healthy margins (>20%). "
                    f"Safe to proceed with price update. "
                    f"Total annual impact: ${total_annual_impact:,.2f}"
                )
            elif unknown_count > 0:
                return (
                    f"⚠️ UNKNOWN: {unknown_count} assemblies could not be analyzed (missing price/cost data). "
                    f"Review manually before proceeding."
                )
            else:
                return "ℹ️ No assemblies affected by this price change."

    def process_supplier_price_change(
        self,
        part_num: str,
        supplier_id: str,
        old_price: float,
        new_price: float,
        effective_date: Optional[str] = None,
        email_metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process a supplier price change email end-to-end.

        This is the main orchestration method for the automated workflow:
        1. Validates the component and supplier in Epicor
        2. Finds all affected assemblies (BOM implosion)
        3. Calculates annual cost impact using Epicor forecast data
        4. Checks margin erosion for ALL affected assemblies
        5. Generates a comprehensive JSON report for frontend display

        Args:
            part_num: Component part number from email
            supplier_id: Supplier ID from email (e.g., "FAST1")
            old_price: Previous price from email
            new_price: New price from email
            effective_date: Optional effective date from email (ISO format)
            email_metadata: Optional dict with email info (subject, from, date, etc.)

        Returns:
            Comprehensive JSON-friendly report containing:
            - status: "success", "warning", or "error"
            - component: Validated component info from Epicor
            - supplier: Validated supplier info from Epicor
            - price_change: Price change details
            - bom_impact: Results from analyze_price_change_impact
            - actions_required: List of required actions based on risk levels
            - processing_errors: List of any errors encountered (continues on errors)
            - timestamp: ISO timestamp of when analysis was performed
        """
        from datetime import datetime

        logger.info("="*80)
        logger.info("🔄 PROCESSING SUPPLIER PRICE CHANGE")
        logger.info("="*80)
        logger.info(f"   Part: {part_num}")
        logger.info(f"   Supplier: {supplier_id}")
        logger.info(f"   Price Change: ${old_price:.4f} → ${new_price:.4f}")
        if effective_date:
            logger.info(f"   Effective Date: {effective_date}")

        processing_errors = []
        timestamp = datetime.utcnow().isoformat() + "Z"

        # Initialize result structure
        result = {
            "status": "success",
            "timestamp": timestamp,
            "processing_errors": processing_errors,
            "component": None,
            "supplier": None,
            "price_change": {
                "part_num": part_num,
                "supplier_id": supplier_id,
                "old_price": old_price,
                "new_price": new_price,
                "price_delta": round(new_price - old_price, 4),
                "price_change_pct": round(((new_price - old_price) / old_price * 100), 2) if old_price > 0 else 0,
                "effective_date": effective_date
            },
            "email_metadata": email_metadata,
            "bom_impact": None,
            "actions_required": [],
            "can_auto_approve": False
        }

        # Step 1: Validate component exists in Epicor
        logger.info("-"*80)
        logger.info("📋 Step 1: Validating component in Epicor...")
        try:
            component_data = self.get_part(part_num)
            if component_data:
                result["component"] = {
                    "part_num": part_num,
                    "description": component_data.get("PartDescription", ""),
                    "type_code": component_data.get("TypeCode", ""),
                    "uom": component_data.get("IUM", ""),
                    "current_cost": component_data.get("StdCost") or component_data.get("AvgMaterialCost", 0),
                    "validated": True
                }
                logger.info(f"   ✅ Component validated: {component_data.get('PartDescription', part_num)}")
            else:
                result["component"] = {"part_num": part_num, "validated": False, "error": "Part not found in Epicor"}
                processing_errors.append(f"Component {part_num} not found in Epicor")
                logger.warning(f"   ⚠️ Component {part_num} not found in Epicor")
        except Exception as e:
            result["component"] = {"part_num": part_num, "validated": False, "error": str(e)}
            processing_errors.append(f"Error validating component: {str(e)}")
            logger.error(f"   ❌ Error validating component: {e}")

        # Step 2: Validate supplier exists in Epicor
        logger.info("-"*80)
        logger.info("📋 Step 2: Validating supplier in Epicor...")
        try:
            vendor_data = self.get_vendor_by_id(supplier_id)
            if vendor_data:
                result["supplier"] = {
                    "supplier_id": supplier_id,
                    "vendor_num": vendor_data.get("VendorNum"),
                    "name": vendor_data.get("Name", ""),
                    "validated": True
                }
                logger.info(f"   ✅ Supplier validated: {vendor_data.get('Name', supplier_id)}")
            else:
                result["supplier"] = {"supplier_id": supplier_id, "validated": False, "error": "Supplier not found"}
                processing_errors.append(f"Supplier {supplier_id} not found in Epicor")
                logger.warning(f"   ⚠️ Supplier {supplier_id} not found in Epicor")
        except Exception as e:
            result["supplier"] = {"supplier_id": supplier_id, "validated": False, "error": str(e)}
            processing_errors.append(f"Error validating supplier: {str(e)}")
            logger.error(f"   ❌ Error validating supplier: {e}")

        # Step 3: Perform comprehensive BOM impact analysis
        logger.info("-"*80)
        logger.info("📋 Step 3: Performing BOM impact analysis...")
        try:
            bom_impact = self.analyze_price_change_impact(
                part_num=part_num,
                old_price=old_price,
                new_price=new_price,
                use_forecast=True  # Automatically use Epicor forecast data
            )
            result["bom_impact"] = bom_impact

            if "error" in bom_impact:
                processing_errors.append(f"BOM analysis error: {bom_impact['error']}")
                logger.error(f"   ❌ BOM analysis error: {bom_impact['error']}")
        except Exception as e:
            result["bom_impact"] = {"error": str(e)}
            processing_errors.append(f"Error in BOM analysis: {str(e)}")
            logger.error(f"   ❌ Exception in BOM analysis: {e}")

        # Step 4: Determine required actions based on analysis
        logger.info("-"*80)
        logger.info("📋 Step 4: Determining required actions...")
        actions = []

        if result["bom_impact"] and "summary" in result["bom_impact"]:
            summary = result["bom_impact"]["summary"]
            risk_summary = summary.get("risk_summary", {})

            # Check for critical/high risk items
            critical_count = risk_summary.get("critical", 0)
            high_count = risk_summary.get("high", 0)
            medium_count = risk_summary.get("medium", 0)

            if critical_count > 0:
                actions.append({
                    "action": "EXECUTIVE_APPROVAL_REQUIRED",
                    "priority": "critical",
                    "description": f"{critical_count} assemblies have margins below {self.margin_thresholds['critical']}%",
                    "assemblies_affected": critical_count
                })

            if high_count > 0:
                actions.append({
                    "action": "MANAGER_APPROVAL_REQUIRED",
                    "priority": "high",
                    "description": f"{high_count} assemblies have margins between {self.margin_thresholds['critical']}%-{self.margin_thresholds['high']}%",
                    "assemblies_affected": high_count
                })

            if medium_count > 0:
                actions.append({
                    "action": "REVIEW_RECOMMENDED",
                    "priority": "medium",
                    "description": f"{medium_count} assemblies approaching margin threshold",
                    "assemblies_affected": medium_count
                })

            # Check for assemblies with unknown risk (missing selling price data)
            unknown_count = risk_summary.get("unknown", 0)
            if unknown_count > 0:
                actions.append({
                    "action": "MANUAL_REVIEW_REQUIRED",
                    "priority": "warning",
                    "description": f"{unknown_count} assemblies have missing price data - cannot calculate margins",
                    "assemblies_affected": unknown_count,
                    "reason": "Missing selling price in Epicor"
                })

            # Check if price update can be auto-approved
            # Prevent auto-approval when there are critical, high risk, OR unknown risk assemblies
            can_auto_approve = (critical_count == 0 and high_count == 0 and unknown_count == 0)
            result["can_auto_approve"] = can_auto_approve

            if can_auto_approve:
                actions.append({
                    "action": "AUTO_APPROVE_ELIGIBLE",
                    "priority": "low",
                    "description": "All affected assemblies maintain healthy margins - eligible for automatic price update"
                })

            # Add price update action
            actions.append({
                "action": "UPDATE_EPICOR_PRICE",
                "priority": "required",
                "description": f"Update part {part_num} price from ${old_price:.4f} to ${new_price:.4f}",
                "requires_approval": not can_auto_approve
            })

        result["actions_required"] = actions

        # Step 5: Set overall status
        if processing_errors:
            if result["bom_impact"] and "summary" in result["bom_impact"]:
                result["status"] = "warning"  # Partial success
            else:
                result["status"] = "error"  # Failed
        else:
            result["status"] = "success"

        # Final logging
        logger.info("="*80)
        logger.info("🔄 SUPPLIER PRICE CHANGE PROCESSING COMPLETE")
        logger.info("="*80)
        logger.info(f"   Status: {result['status'].upper()}")
        logger.info(f"   Processing errors: {len(processing_errors)}")
        logger.info(f"   Actions required: {len(actions)}")
        logger.info(f"   Can auto-approve: {result['can_auto_approve']}")
        if result["bom_impact"] and "summary" in result["bom_impact"]:
            logger.info(f"   Total assemblies affected: {result['bom_impact']['summary']['total_assemblies_affected']}")
            logger.info(f"   Total annual impact: ${result['bom_impact']['summary']['total_annual_cost_impact']:,.2f}")
        logger.info("="*80)

        return result

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

    def get_all_vendor_emails(self) -> List[Dict[str, Any]]:
        """
        Fetch all vendor emails from Epicor VendorSvc
        Used for vendor verification to prevent AI token waste on random emails

        Returns:
            List of dicts: [
                {"vendor_id": "ACME1", "name": "Acme Corp", "email": "contact@acme.com"},
                ...
            ]
        """
        try:
            url = f"{self.base_url}/{self.company_id}/Erp.BO.VendorSvc/Vendors"
            headers = self._get_headers()

            params = {
                "$select": "VendorID,Name,EMailAddress",
                "$filter": "EMailAddress ne null and EMailAddress ne ''"
            }

            logger.info("🔍 Fetching vendor emails from Epicor VendorSvc...")
            response = requests.get(url, headers=headers, params=params, timeout=30)

            if response.status_code == 200:
                data = response.json()
                vendors = data.get("value", [])

                result = []
                for v in vendors:
                    email = v.get("EMailAddress")
                    vendor_id = v.get("VendorID")
                    name = v.get("Name")

                    if email and vendor_id:
                        result.append({
                            "vendor_id": vendor_id,
                            "name": name,
                            "email": email.lower().strip() if email else None
                        })

                logger.info(f"✅ Fetched {len(result)} vendors with email addresses")
                return result
            else:
                logger.error(f"❌ Failed to fetch vendors: {response.status_code} - {response.text[:200]}")
                return []

        except Exception as e:
            logger.error(f"❌ Exception fetching vendor emails: {e}")
            return []

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

    def get_all_price_lists(self) -> Optional[List[Dict[str, Any]]]:
        """
        Get all price lists for the company

        Returns:
            List of price list headers, or None if error
        """
        try:
            url = f"{self.base_url}/{self.company_id}/Erp.BO.PriceLstSvc/PriceLsts"
            headers = self._get_headers()

            params = {
                "$filter": f"Company eq '{self.company_id}'"
            }

            logger.info(f"🔍 Fetching all price lists for company {self.company_id}")

            response = requests.get(url, headers=headers, params=params, timeout=10)

            if response.status_code == 200:
                data = response.json()
                results = data.get("value", [])
                logger.info(f"✅ Found {len(results)} price lists")
                return results
            else:
                logger.error(f"❌ Error fetching price lists: {response.status_code} - {response.text}")
                return None

        except Exception as e:
            logger.error(f"❌ Exception fetching price lists: {e}")
            return None

    def find_supplier_price_list(self, supplier_id: str, supplier_name: str = None) -> Optional[Dict[str, Any]]:
        """
        Find existing price list for a supplier by searching all price lists

        Searches by:
        1. ListCode containing supplier_id (e.g., "FAST1" in code)
        2. ListDescription containing supplier_name or supplier_id

        Args:
            supplier_id: External supplier identifier (e.g., "FAST1")
            supplier_name: Supplier name (optional, for better matching)

        Returns:
            Price list header dict if found, None otherwise
        """
        try:
            logger.info(f"🔍 Searching for existing price list for supplier: {supplier_id}")

            # Get all price lists
            all_lists = self.get_all_price_lists()

            if not all_lists:
                logger.info(f"   No price lists found in system")
                return None

            # Search for matching price list
            for price_list in all_lists:
                list_code = price_list.get("ListCode", "")
                description = price_list.get("ListDescription", "")

                # Match by code containing supplier_id
                if supplier_id.upper() in list_code.upper():
                    logger.info(f"✅ Found matching price list by code: {list_code}")
                    return price_list

                # Match by description containing supplier_id or supplier_name
                if supplier_id.upper() in description.upper():
                    logger.info(f"✅ Found matching price list by description: {list_code}")
                    return price_list

                if supplier_name and supplier_name.upper() in description.upper():
                    logger.info(f"✅ Found matching price list by supplier name: {list_code}")
                    return price_list

            logger.info(f"   No existing price list found for supplier {supplier_id}")
            return None

        except Exception as e:
            logger.error(f"❌ Exception searching for supplier price list: {e}")
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

    def get_or_create_supplier_price_list(
        self,
        supplier_id: str,
        supplier_name: str = None,
        effective_date: str = None
    ) -> Dict[str, Any]:
        """
        Get or create a supplier-specific price list

        Uses naming convention with 10-char limit:
        - If supplier_id <= 10 chars: use supplier_id directly (e.g., "FAST1", "USUI-001")
        - If supplier_id > 10 chars: truncate to 10 chars

        Args:
            supplier_id: External supplier identifier (e.g., "FAST1")
            supplier_name: Supplier name for description (optional)
            effective_date: Effective start date if creating new list (optional)

        Returns:
            Dictionary with status, list_code, and created flag
        """
        try:
            # Step 1: Search for existing price list for this supplier
            logger.info(f"🔍 Step 1: Searching for existing price list for supplier: {supplier_id}")
            existing_list = self.find_supplier_price_list(supplier_id, supplier_name)

            if existing_list:
                list_code = existing_list.get("ListCode")
                logger.info(f"✅ Using existing supplier price list: {list_code}")
                return {
                    "status": "success",
                    "message": "Supplier price list exists",
                    "list_code": list_code,
                    "created": False,
                    "price_list": existing_list
                }

            # Step 2: No existing list found - create new one
            # Generate list code with 10-char limit
            # Strategy: Use supplier_id directly if <= 10 chars, otherwise truncate
            if len(supplier_id) <= 10:
                list_code = supplier_id
            else:
                list_code = supplier_id[:10]
                logger.warning(f"⚠️  Supplier ID '{supplier_id}' exceeds 10 chars, truncating to '{list_code}'")

            logger.info(f"📝 Step 2: Creating new supplier price list: {list_code}")

            # Prepare description with 30-char limit
            if supplier_name:
                # Format: "PL: {name}" to keep it short
                description = f"PL: {supplier_name}"
            else:
                description = f"Supplier {supplier_id}"

            # Truncate to 30 chars if needed
            if len(description) > 30:
                description = description[:30]
                logger.info(f"   Description truncated to 30 chars: {description}")

            # Prepare start date
            start_date = effective_date
            if start_date and 'T' not in start_date:
                start_date = f"{start_date}T00:00:00"

            # Construct new price list header
            new_price_list = {
                "Company": self.company_id,
                "ListCode": list_code,
                "ListDescription": description,
                "ListType": "B",  # B = Base/Buy price list (discovered from existing lists)
                "StartDate": start_date,
                "EndDate": None,
                "Active": True,
                "CurrencyCode": "USD",  # Default currency
                "RowMod": "A"  # A = Add (create)
            }

            # POST to Update endpoint
            update_url = f"{self.base_url}/{self.company_id}/Erp.BO.PriceLstSvc/Update"
            headers = self._get_headers()

            ds = {
                "PriceLst": [new_price_list]
            }

            payload = {"ds": ds}

            logger.info(f"   Creating price list: {list_code}")
            logger.info(f"   Description: {description}")
            if start_date:
                logger.info(f"   StartDate: {start_date}")

            response = requests.post(update_url, json=payload, headers=headers, timeout=10)

            if response.status_code == 200:
                logger.info(f"✅ Supplier price list created successfully: {list_code}")
                return {
                    "status": "success",
                    "message": "Supplier price list created",
                    "list_code": list_code,
                    "created": True,
                    "start_date": start_date
                }
            else:
                logger.error(f"❌ Failed to create price list: {response.status_code}")
                logger.error(f"   Response: {response.text[:500]}")
                return {
                    "status": "error",
                    "message": f"Failed to create price list: HTTP {response.status_code}: {response.text[:200]}",
                    "list_code": list_code,
                    "status_code": response.status_code
                }

        except Exception as e:
            logger.error(f"❌ Exception in get_or_create_supplier_price_list: {e}")
            # Generate safe list code for error response
            safe_list_code = supplier_id[:10] if len(supplier_id) <= 10 else supplier_id[:10]
            return {
                "status": "error",
                "message": str(e),
                "list_code": safe_list_code
            }

    def create_price_list_entry(
        self,
        part_num: str,
        base_price: float,
        effective_date: str,
        uom_code: str = "EA",
        list_code: str = None
    ) -> Dict[str, Any]:
        """
        Create a new price list entry using direct POST (Step B: Price List Creation - NO path)

        Uses Epicor's direct insert workflow with RowMod="A" instead of template-based creation.
        The GetNewPriceLstParts endpoint does not exist in Epicor REST API.

        Args:
            part_num: Part number
            base_price: Base price for the part
            effective_date: Effective date (managed at header level, not used here)
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

            # Construct new price list part entry directly
            # No template needed - Epicor REST API supports direct POST with RowMod="A"
            logger.info(f"      Constructing new price list entry...")

            new_entry = {
                "Company": self.company_id,
                "ListCode": list_code,
                "PartNum": part_num,
                "UOMCode": uom_code,
                "BasePrice": base_price,
                "RowMod": "A"  # A = Add (create new entry)
            }

            # Note: Effective dates are managed at header level only (Step C)
            # Parts inherit the StartDate from the price list header
            logger.info(f"      ℹ️  Effective date will be managed at header level")

            # POST to Update endpoint
            update_url = f"{self.base_url}/{self.company_id}/Erp.BO.PriceLstSvc/Update"
            headers = self._get_headers()

            ds = {
                "PriceLstParts": [new_entry]
            }

            payload = {"ds": ds}

            logger.info(f"      Saving new price list entry...")
            response = requests.post(update_url, headers=headers, json=payload, timeout=10)

            if response.status_code == 200:
                logger.info(f"      ✅ Price list entry created successfully")
                return {
                    "status": "success",
                    "message": "Price list entry created",
                    "list_code": list_code,
                    "part_num": part_num,
                    "base_price": base_price,
                    "effective_date": effective_date
                }
            else:
                error_msg = response.text
                logger.error(f"      ❌ Failed to create entry: {response.status_code}")
                logger.error(f"         Response: {error_msg[:300]}")

                return {
                    "status": "error",
                    "message": f"Create failed: HTTP {response.status_code}: {error_msg[:200]}",
                    "list_code": list_code,
                    "part_num": part_num
                }

        except Exception as e:
            logger.error(f"      ❌ Exception creating price list entry: {e}")
            return {
                "status": "error",
                "message": str(e),
                "list_code": list_code if list_code else "unknown",
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

            # Get or create supplier-specific price list (SUPPLIER_{supplier_id})
            logger.info(f"   🔄 Getting or creating supplier-specific price list...")
            price_list_result = self.get_or_create_supplier_price_list(
                supplier_id=supplier_id,
                supplier_name=vendor_name,
                effective_date=effective_date
            )

            if price_list_result.get("status") != "success":
                logger.error(f"❌ Step B Failed: Could not get/create supplier price list")
                return {
                    "status": "error",
                    "message": f"Failed to get/create supplier price list: {price_list_result.get('message')}",
                    "part_num": part_num,
                    "supplier_id": supplier_id,
                    "vendor_num": vendor_num,
                    "step_failed": "Step B: Price List Creation (Header)"
                }

            list_code = price_list_result.get("list_code")
            price_list_created = price_list_result.get("created", False)

            if price_list_created:
                logger.info(f"   ✅ Created new supplier price list: {list_code}")
            else:
                logger.info(f"   ✅ Using existing supplier price list: {list_code}")

            # Check if price list entry exists for this part (Step B decision point)
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

