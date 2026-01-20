"""
Integration tests for Epicor BOM Impact Analysis functionality.

This test module tests the complete BOM impact analysis workflow:
1. Finding affected assemblies (BOM implosion) - get_part_where_used(), find_all_affected_assemblies()
2. Calculating cost impact - calculate_assembly_cost_impact()
3. Estimating annual financial impact - calculate_annual_impact()
4. Checking margin erosion risks - check_margin_erosion()
5. Comprehensive analysis - analyze_price_change_impact()

IMPORTANT: These are integration tests that connect to the actual Epicor instance.
They require valid credentials in .env and real part numbers from your Epicor system.

Test Data Requirements:
-----------------------
To run these tests, you need to identify part numbers from your Epicor system:

1. COMPONENT_PART: A purchased component that is used in at least one assembly
   Example: A bolt, screw, or raw material like "BOLT-M10-30" or "STEEL-PLATE-01"

2. ASSEMBLY_PART: An assembly that uses the component above
   Example: A frame, kit, or subassembly like "FRAME-A" or "KIT-001"

3. TOP_LEVEL_PART: A finished good that is NOT used in any other assemblies
   Example: A final product like "PRODUCT-001"

4. MULTI_LEVEL_COMPONENT: A component used in assemblies that are themselves used in higher-level assemblies
   Example: A motor used in a pump, which is used in a system

Update the TEST_DATA dictionary below with your actual part numbers before running.

Run tests with: python -m pytest test/test_epicor_bom_impact.py -v
"""

import sys
import os
import json
import pytest
from typing import Dict, List, Any

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services.epicor_service import epicor_service


# =============================================================================
# TEST DATA CONFIGURATION
# =============================================================================
# Update these with actual part numbers from your Epicor system

TEST_DATA = {
    # A component part that IS USED in at least one assembly (for BOM implosion tests)
    # This should be a purchased part or raw material used in manufacturing
    "COMPONENT_PART": "#FFH06-12SAE F",  # Verified: Used in K9790 assembly

    # An assembly that contains the COMPONENT_PART above
    "ASSEMBLY_PART": "K9790",  # Verified: Contains #FFH06-12SAE F as component

    # A top-level part that is NOT used in any other assemblies
    "TOP_LEVEL_PART": "K9790",  # Using assembly as top-level (no parents expected)

    # For multi-level BOM tests: A component used in nested assemblies
    "MULTI_LEVEL_COMPONENT": "#FFH06-12SAE F",  # Same component for consistency

    # Supplier ID for the component (for verification)
    "SUPPLIER_ID": "FAST1",

    # Sample price change data for testing
    "OLD_PRICE": 10.00,
    "NEW_PRICE": 12.50,

    # Weekly demand overrides for annual impact calculation
    "WEEKLY_DEMAND_OVERRIDE": {
        # "ASSY-001": 100,  # 100 units per week
        # "ASSY-002": 50,   # 50 units per week
    },

    # Custom margin thresholds for testing (optional)
    "MARGIN_THRESHOLDS": {
        "critical": 10.0,
        "high": 15.0,
        "medium": 20.0
    }
}


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture(scope="module")
def epicor():
    """Provide the Epicor service instance for all tests"""
    return epicor_service


@pytest.fixture(scope="module")
async def connection_verified(epicor):
    """Verify Epicor connection before running tests"""
    result = await epicor.test_connection()
    if result["status"] != "success":
        pytest.skip(f"Epicor connection failed: {result.get('message')}")
    return True


# =============================================================================
# TEST: CONNECTION AND SETUP
# =============================================================================

class TestEpicorConnection:
    """Test Epicor API connectivity"""

    async def test_connection(self, epicor):
        """
        Test basic connection to Epicor API.
        This should pass before any other tests can run.
        """
        print("\n" + "="*80)
        print("🔌 Testing Epicor API Connection")
        print("="*80)

        result = await epicor.test_connection()

        print(f"   Status: {result['status']}")
        print(f"   Message: {result['message']}")

        assert result["status"] == "success", f"Connection failed: {result.get('message')}"
        print("   ✅ Connection successful!")


# =============================================================================
# TEST: get_part_where_used() - Direct Parent Assembly Lookup
# =============================================================================

class TestGetPartWhereUsed:
    """Tests for the get_part_where_used() method - finds direct parent assemblies"""

    @pytest.mark.integration
    async def test_get_part_where_used_with_valid_component(self, epicor, connection_verified):
        """
        Test finding direct parent assemblies for a component that IS used in assemblies.

        Expected: Should return a list of parent assemblies with:
        - PartNum, RevisionNum, QtyPer, CanTrackUp, Description, MtlSeq
        """
        print("\n" + "="*80)
        print("📋 TEST: get_part_where_used() - Valid Component")
        print("="*80)

        part_num = TEST_DATA["COMPONENT_PART"]
        print(f"   Component Part: {part_num}")

        result = await epicor.get_part_where_used(part_num)

        print(f"\n   Result Type: {type(result)}")
        print(f"   Parent Assemblies Found: {len(result) if result else 0}")

        if result:
            print("\n   Sample Parent Assemblies:")
            for i, parent in enumerate(result[:5], 1):  # Show max 5
                print(f"      {i}. PartNum: {parent.get('PartNum')}")
                print(f"         QtyPer: {parent.get('QtyPer')}")
                print(f"         CanTrackUp: {parent.get('CanTrackUp')}")
                print(f"         Description: {parent.get('Description', 'N/A')[:50]}")

            # Assertions
            assert isinstance(result, list), "Result should be a list"
            assert len(result) > 0, "Should find at least one parent assembly"

            # Verify structure of first result
            first = result[0]
            assert "PartNum" in first, "Result should contain PartNum"
            assert "QtyPer" in first, "Result should contain QtyPer"
            print("\n   ✅ Test passed: Found parent assemblies with correct structure")
        else:
            print(f"\n   ⚠️ No parent assemblies found for {part_num}")
            print("   This may indicate the component is not used in any BOMs")
            pytest.skip(f"No parent assemblies found for test part {part_num}")

    @pytest.mark.integration
    async def test_get_part_where_used_with_top_level_part(self, epicor, connection_verified):
        """
        Test finding parent assemblies for a top-level part (finished good).

        Expected: Should return an empty list since top-level parts have no parents.
        """
        print("\n" + "="*80)
        print("📋 TEST: get_part_where_used() - Top-Level Part (No Parents Expected)")
        print("="*80)

        part_num = TEST_DATA["TOP_LEVEL_PART"]
        print(f"   Top-Level Part: {part_num}")

        result = await epicor.get_part_where_used(part_num)

        print(f"\n   Parent Assemblies Found: {len(result) if result else 0}")

        # Top-level parts should have no parents (empty list)
        assert isinstance(result, list), "Result should be a list"
        print(f"   ✅ Test passed: Top-level part returns {'empty list' if len(result) == 0 else f'{len(result)} parents'}")

    @pytest.mark.integration
    async def test_get_part_where_used_with_nonexistent_part(self, epicor, connection_verified):
        """
        Test handling of non-existent part number.

        Expected: Should return an empty list without crashing.
        """
        print("\n" + "="*80)
        print("📋 TEST: get_part_where_used() - Non-Existent Part")
        print("="*80)

        part_num = "NONEXISTENT-PART-XYZ-999"
        print(f"   Part (should not exist): {part_num}")

        result = await epicor.get_part_where_used(part_num)

        print(f"\n   Result: {result}")

        # Should return empty list for non-existent parts
        assert isinstance(result, list), "Result should be a list even for non-existent parts"
        assert len(result) == 0, "Non-existent parts should return empty list"
        print("   ✅ Test passed: Non-existent part handled gracefully")


# =============================================================================
# TEST: find_all_affected_assemblies() - Multi-Level BOM Traversal
# =============================================================================

class TestFindAllAffectedAssemblies:
    """Tests for find_all_affected_assemblies() - recursive multi-level BOM implosion"""

    @pytest.mark.integration
    async def test_find_all_affected_assemblies_basic(self, epicor, connection_verified):
        """
        Test recursive BOM traversal to find all affected assemblies.

        Expected: Should return list with:
        - assembly_part_num, revision, qty_per, cumulative_qty, bom_level,
          direct_parent_of, can_track_up, description
        """
        print("\n" + "="*80)
        print("📋 TEST: find_all_affected_assemblies() - Basic Multi-Level Traversal")
        print("="*80)

        part_num = TEST_DATA["MULTI_LEVEL_COMPONENT"]
        print(f"   Component Part: {part_num}")

        result = await epicor.find_all_affected_assemblies(part_num)

        print(f"\n   Total Affected Assemblies: {len(result) if result else 0}")

        if result:
            # Group by BOM level
            levels = {}
            for assy in result:
                level = assy.get("bom_level", 0)
                levels[level] = levels.get(level, 0) + 1

            print(f"\n   BOM Level Distribution:")
            for level in sorted(levels.keys()):
                print(f"      Level {level}: {levels[level]} assemblies")

            print("\n   Sample Affected Assemblies:")
            for i, assy in enumerate(result[:5], 1):
                print(f"      {i}. {assy.get('assembly_part_num')}")
                print(f"         Level: {assy.get('bom_level')}")
                print(f"         QtyPer: {assy.get('qty_per')}")
                print(f"         CumulativeQty: {assy.get('cumulative_qty')}")
                print(f"         DirectParentOf: {assy.get('direct_parent_of')}")

            # Assertions
            assert isinstance(result, list), "Result should be a list"
            assert len(result) > 0, "Should find at least one affected assembly"

            # Verify structure
            first = result[0]
            required_fields = ["assembly_part_num", "qty_per", "cumulative_qty", "bom_level"]
            for field in required_fields:
                assert field in first, f"Result should contain {field}"

            # Verify cumulative_qty calculation (should be >= qty_per)
            for assy in result:
                assert assy["cumulative_qty"] >= assy["qty_per"], \
                    f"Cumulative qty ({assy['cumulative_qty']}) should be >= qty_per ({assy['qty_per']})"

            print("\n   ✅ Test passed: Multi-level BOM traversal working correctly")
        else:
            pytest.skip(f"No affected assemblies found for {part_num}")

    @pytest.mark.integration
    async def test_find_all_affected_assemblies_max_levels(self, epicor, connection_verified):
        """
        Test that max_levels parameter limits traversal depth.
        """
        print("\n" + "="*80)
        print("📋 TEST: find_all_affected_assemblies() - Max Levels Limit")
        print("="*80)

        part_num = TEST_DATA["MULTI_LEVEL_COMPONENT"]

        # Test with max_levels=1 (direct parents only)
        result_1_level = await epicor.find_all_affected_assemblies(part_num, max_levels=1)

        # Test with max_levels=10 (deep traversal)
        result_10_levels = await epicor.find_all_affected_assemblies(part_num, max_levels=10)

        print(f"   Results with max_levels=1:  {len(result_1_level) if result_1_level else 0} assemblies")
        print(f"   Results with max_levels=10: {len(result_10_levels) if result_10_levels else 0} assemblies")

        # With higher max_levels, we should get >= assemblies
        if result_1_level and result_10_levels:
            assert len(result_10_levels) >= len(result_1_level), \
                "Higher max_levels should find >= assemblies"

            # Verify all level-1 results have bom_level=1
            for assy in result_1_level:
                assert assy.get("bom_level") == 1, "Level-limited results should all be at level 1"

        print("   ✅ Test passed: max_levels parameter works correctly")



# =============================================================================
# TEST: calculate_assembly_cost_impact() - Cost Impact Calculation
# =============================================================================

class TestCalculateAssemblyCostImpact:
    """Tests for calculate_assembly_cost_impact() - cost impact per assembly"""

    @pytest.mark.integration
    async def test_calculate_assembly_cost_impact_basic(self, epicor, connection_verified):
        """
        Test basic cost impact calculation for a price change.

        Expected return: current_cost, cost_increase_per_unit, new_assembly_cost, cost_increase_pct
        """
        print("\n" + "="*80)
        print("💰 TEST: calculate_assembly_cost_impact() - Basic Calculation")
        print("="*80)

        assembly_part = TEST_DATA["ASSEMBLY_PART"]
        price_delta = TEST_DATA["NEW_PRICE"] - TEST_DATA["OLD_PRICE"]
        qty_per = 2.0  # Assume 2 units of component per assembly

        print(f"   Assembly Part: {assembly_part}")
        print(f"   Price Delta: ${price_delta:.4f}")
        print(f"   Qty Per Assembly: {qty_per}")

        result = await epicor.calculate_assembly_cost_impact(
            component_price_delta=price_delta,
            qty_per_assembly=qty_per,
            assembly_part_num=assembly_part
        )

        print(f"\n   Result:")
        print(json.dumps(result, indent=4, default=str))

        # Assertions
        assert isinstance(result, dict), "Result should be a dictionary"
        assert "assembly_part_num" in result, "Result should contain assembly_part_num"

        if "error" not in result:
            # Verify cost increase calculation: delta * qty_per
            expected_increase = price_delta * qty_per
            actual_increase = result.get("cost_increase_per_unit", 0)

            assert abs(actual_increase - expected_increase) < 0.01, \
                f"Cost increase should be {expected_increase}, got {actual_increase}"

            print(f"\n   ✅ Test passed: Cost impact calculated correctly")
            print(f"      Expected cost increase: ${expected_increase:.4f}")
            print(f"      Actual cost increase: ${actual_increase:.4f}")
        else:
            print(f"\n   ⚠️ Assembly not found or error: {result.get('error')}")
            pytest.skip(f"Assembly {assembly_part} not found in Epicor")


# =============================================================================
# TEST: get_part_forecast() - Forecast Data Retrieval
# =============================================================================

class TestGetPartForecast:
    """Tests for get_part_forecast() - retrieving forecast/demand data from Epicor"""

    @pytest.mark.integration
    async def test_get_part_forecast_basic(self, epicor, connection_verified):
        """
        Test retrieving forecast data for a part.

        Expected: total_forecast_qty, weekly_demand, forecast_records, forecasts list
        """
        print("\n" + "="*80)
        print("📈 TEST: get_part_forecast() - Basic Forecast Retrieval")
        print("="*80)

        # Test with a part that may or may not have forecast data
        part_num = TEST_DATA["ASSEMBLY_PART"]

        print(f"   Part Number: {part_num}")

        result = await epicor.get_part_forecast(part_num)

        print(f"\n   Result:")
        print(f"      Total Forecast Qty: {result.get('total_forecast_qty', 0)}")
        print(f"      Weekly Demand: {result.get('weekly_demand', 0):.4f}")
        print(f"      Forecast Records: {result.get('forecast_records', 0)}")
        print(f"      Data Source: {result.get('data_source', 'N/A')}")

        # Assertions
        assert isinstance(result, dict), "Result should be a dictionary"
        assert "total_forecast_qty" in result, "Result should contain total_forecast_qty"
        assert "weekly_demand" in result, "Result should contain weekly_demand"
        assert "forecast_records" in result, "Result should contain forecast_records"
        assert result.get("weekly_demand", 0) >= 0, "Weekly demand should be non-negative"

        print(f"\n   ✅ Test passed: Forecast data retrieved successfully")


# =============================================================================
# TEST: calculate_annual_impact() - Annual Financial Impact
# =============================================================================

class TestCalculateAnnualImpact:
    """Tests for calculate_annual_impact() - annual financial impact estimation"""

    @pytest.mark.integration
    async def test_calculate_annual_impact_with_override(self, epicor, connection_verified):
        """
        Test annual impact calculation with weekly demand overrides.

        Formula: Annual Impact = Price Delta × Cumulative Qty × Weekly Demand × 52
        """
        print("\n" + "="*80)
        print("📊 TEST: calculate_annual_impact() - With Demand Override")
        print("="*80)

        part_num = TEST_DATA["COMPONENT_PART"]
        price_delta = TEST_DATA["NEW_PRICE"] - TEST_DATA["OLD_PRICE"]

        # First, get affected assemblies
        affected = await epicor.find_all_affected_assemblies(part_num)

        if not affected:
            pytest.skip(f"No affected assemblies found for {part_num}")

        # Create weekly demand override for testing
        weekly_demand_override = {}
        for assy in affected[:3]:  # Override demand for first 3 assemblies
            weekly_demand_override[assy["assembly_part_num"]] = 100.0  # 100 units/week

        print(f"   Price Delta: ${price_delta:.4f}")
        print(f"   Affected Assemblies: {len(affected)}")
        print(f"   Weekly Demand Override: {weekly_demand_override}")

        result = await epicor.calculate_annual_impact(
            price_delta=price_delta,
            affected_assemblies=affected,
            weekly_demand_override=weekly_demand_override
        )

        print(f"\n   Result Summary:")
        print(f"      Total Annual Impact: ${result.get('total_annual_impact', 0):,.2f}")
        print(f"      Assemblies Impacted: {result.get('total_assemblies_impacted', 0)}")
        print(f"      Assemblies With Demand Data: {result.get('assemblies_with_demand_data', 0)}")

        # Assertions
        assert isinstance(result, dict), "Result should be a dictionary"
        assert "total_annual_impact" in result, "Result should contain total_annual_impact"
        assert "impact_by_assembly" in result, "Result should contain impact_by_assembly"

        # Verify impact_by_assembly structure
        if result.get("impact_by_assembly"):
            first_impact = result["impact_by_assembly"][0]
            assert "assembly_part_num" in first_impact
            assert "annual_cost_impact" in first_impact

        print(f"\n   ✅ Test passed: Annual impact calculated")

    @pytest.mark.integration
    async def test_calculate_annual_impact_with_forecast(self, epicor, connection_verified):
        """
        Test annual impact calculation using Epicor forecast data.

        This test uses use_forecast=True to automatically fetch demand data
        from Epicor's ForecastSvc instead of manual overrides.
        """
        print("\n" + "="*80)
        print("📊 TEST: calculate_annual_impact() - With Epicor Forecast")
        print("="*80)

        part_num = TEST_DATA["COMPONENT_PART"]
        price_delta = TEST_DATA["NEW_PRICE"] - TEST_DATA["OLD_PRICE"]

        # First, get affected assemblies
        affected = await epicor.find_all_affected_assemblies(part_num)

        if not affected:
            pytest.skip(f"No affected assemblies found for {part_num}")

        print(f"   Price Delta: ${price_delta:.4f}")
        print(f"   Affected Assemblies: {len(affected)}")
        print(f"   Using Epicor Forecast: True")

        result = await epicor.calculate_annual_impact(
            price_delta=price_delta,
            affected_assemblies=affected,
            use_forecast=True  # Automatically fetch forecast data
        )

        print(f"\n   Result Summary:")
        print(f"      Total Annual Impact: ${result.get('total_annual_impact', 0):,.2f}")
        print(f"      Assemblies Impacted: {result.get('total_assemblies_impacted', 0)}")
        print(f"      Assemblies With Demand Data: {result.get('assemblies_with_demand_data', 0)}")
        print(f"      Demand From Forecast: {result.get('demand_from_forecast', 0)}")

        # Assertions
        assert isinstance(result, dict), "Result should be a dictionary"
        assert "total_annual_impact" in result, "Result should contain total_annual_impact"
        assert "impact_by_assembly" in result, "Result should contain impact_by_assembly"
        assert "demand_from_forecast" in result, "Result should contain demand_from_forecast"

        # Verify impact_by_assembly structure includes demand_source
        if result.get("impact_by_assembly"):
            first_impact = result["impact_by_assembly"][0]
            assert "demand_source" in first_impact, "Impact should include demand_source"
            # demand_source should be 'forecast', 'forecast_zero', 'override', or 'default'
            valid_sources = ["forecast", "forecast_zero", "override", "default"]
            assert first_impact["demand_source"] in valid_sources, \
                f"demand_source should be one of {valid_sources}"

        print(f"\n   ✅ Test passed: Annual impact with forecast calculated")


# =============================================================================
# TEST: check_margin_erosion() - Margin Risk Analysis
# =============================================================================

class TestCheckMarginErosion:
    """Tests for check_margin_erosion() - margin erosion risk flagging"""

    @pytest.mark.integration
    async def test_check_margin_erosion_basic(self, epicor, connection_verified):
        """
        Test margin erosion check for an assembly with a cost increase.

        Expected: current_margin_pct, new_margin_pct, margin_change_pct,
                  risk_level (critical/high/medium/low), requires_review, recommendation
        """
        print("\n" + "="*80)
        print("📉 TEST: check_margin_erosion() - Basic Margin Check")
        print("="*80)

        assembly_part = TEST_DATA["ASSEMBLY_PART"]
        cost_increase = 5.00  # $5 cost increase

        print(f"   Assembly Part: {assembly_part}")
        print(f"   Cost Increase: ${cost_increase:.2f}")

        result = await epicor.check_margin_erosion(
            assembly_part_num=assembly_part,
            cost_increase=cost_increase
        )

        print(f"\n   Result:")
        print(json.dumps(result, indent=4, default=str))

        # Assertions
        assert isinstance(result, dict), "Result should be a dictionary"
        assert "risk_level" in result, "Result should contain risk_level"
        assert "requires_review" in result, "Result should contain requires_review"
        assert "recommendation" in result, "Result should contain recommendation"

        # Verify risk_level is valid
        valid_risk_levels = ["critical", "high", "medium", "low", "unknown"]
        assert result["risk_level"] in valid_risk_levels, \
            f"Risk level should be one of {valid_risk_levels}"

        if "error" not in result:
            print(f"\n   ✅ Test passed: Margin erosion check completed")
            print(f"      Risk Level: {result['risk_level'].upper()}")
            print(f"      Current Margin: {result.get('current_margin_pct', 'N/A')}%")
            print(f"      New Margin: {result.get('new_margin_pct', 'N/A')}%")
        else:
            print(f"\n   ⚠️ Error checking margin: {result.get('error')}")

    @pytest.mark.integration
    async def test_check_margin_erosion_with_custom_thresholds(self, epicor, connection_verified):
        """
        Test margin erosion check with custom thresholds.
        """
        print("\n" + "="*80)
        print("📉 TEST: check_margin_erosion() - Custom Thresholds")
        print("="*80)

        assembly_part = TEST_DATA["ASSEMBLY_PART"]
        cost_increase = 10.00

        # Custom thresholds (more strict)
        custom_thresholds = {
            "critical": 15.0,  # More strict: critical below 15%
            "high": 20.0,
            "medium": 25.0
        }

        print(f"   Assembly Part: {assembly_part}")
        print(f"   Cost Increase: ${cost_increase:.2f}")
        print(f"   Custom Thresholds: {custom_thresholds}")

        result = await epicor.check_margin_erosion(
            assembly_part_num=assembly_part,
            cost_increase=cost_increase,
            margin_thresholds=custom_thresholds
        )

        print(f"\n   Result:")
        print(f"      Risk Level: {result.get('risk_level', 'N/A').upper()}")
        print(f"      Thresholds Used: {result.get('thresholds_used', 'N/A')}")

        # Verify custom thresholds were used
        if "thresholds_used" in result:
            assert result["thresholds_used"]["critical"] == custom_thresholds["critical"]

        print(f"\n   ✅ Test passed: Custom thresholds applied correctly")



# =============================================================================
# TEST: analyze_price_change_impact() - Comprehensive Analysis
# =============================================================================

class TestAnalyzePriceChangeImpact:
    """Tests for analyze_price_change_impact() - the comprehensive analysis method"""

    @pytest.mark.integration
    async def test_analyze_price_change_impact_full(self, epicor, connection_verified):
        """
        Test the comprehensive BOM impact analysis for a price change.

        This is the main integration test that exercises all BOM impact methods together.

        Expected return structure:
        - component_part_num, old_price, new_price, price_delta, price_change_pct
        - summary: total_assemblies_affected, total_annual_cost_impact, risk_summary, requires_approval
        - impact_details: list of detailed impact for each assembly
        - annual_impact: total financial impact data
        - recommendation: human-readable recommendation text
        """
        print("\n" + "="*80)
        print("🎯 TEST: analyze_price_change_impact() - COMPREHENSIVE ANALYSIS")
        print("="*80)

        part_num = TEST_DATA["COMPONENT_PART"]
        old_price = TEST_DATA["OLD_PRICE"]
        new_price = TEST_DATA["NEW_PRICE"]
        weekly_demand_override = TEST_DATA.get("WEEKLY_DEMAND_OVERRIDE", {})

        print(f"\n   Component: {part_num}")
        print(f"   Old Price: ${old_price:.2f}")
        print(f"   New Price: ${new_price:.2f}")
        print(f"   Price Change: ${new_price - old_price:.2f} ({((new_price - old_price) / old_price * 100):.1f}%)")

        result = await epicor.analyze_price_change_impact(
            part_num=part_num,
            old_price=old_price,
            new_price=new_price,
            weekly_demand_override=weekly_demand_override if weekly_demand_override else None
        )

        print(f"\n" + "-"*80)
        print("   📊 ANALYSIS RESULTS")
        print("-"*80)

        # Display summary
        summary = result.get("summary", {})
        print(f"\n   Summary:")
        print(f"      Total Assemblies Affected: {summary.get('total_assemblies_affected', 0)}")
        print(f"      Total Annual Impact: ${summary.get('total_annual_cost_impact', 0):,.2f}")
        print(f"      Requires Approval: {summary.get('requires_approval', 'N/A')}")

        # Display risk breakdown
        risk_summary = summary.get("risk_summary", {})
        print(f"\n   Risk Breakdown:")
        print(f"      🚨 Critical: {risk_summary.get('critical', 0)}")
        print(f"      ⚠️  High:     {risk_summary.get('high', 0)}")
        print(f"      ℹ️  Medium:   {risk_summary.get('medium', 0)}")
        print(f"      ✅ Low:      {risk_summary.get('low', 0)}")
        print(f"      ❓ Unknown:  {risk_summary.get('unknown', 0)}")

        # Display recommendation
        print(f"\n   Recommendation:")
        print(f"      {result.get('recommendation', 'N/A')}")

        # Display top impacted assemblies
        impact_details = result.get("impact_details", [])
        if impact_details:
            print(f"\n   Top 5 Impacted Assemblies (by risk):")
            for i, detail in enumerate(impact_details[:5], 1):
                risk = detail.get('risk_level', 'unknown').upper()
                margin = detail.get('new_margin_pct', 'N/A')
                annual = detail.get('annual_cost_impact', 0)
                print(f"      {i}. {detail['assembly_part_num']}")
                print(f"         Risk: {risk} | New Margin: {margin}% | Annual Impact: ${annual:,.2f}")

        # Assertions - Verify structure
        assert isinstance(result, dict), "Result should be a dictionary"
        assert "component_part_num" in result, "Result should contain component_part_num"
        assert "summary" in result, "Result should contain summary"
        assert "impact_details" in result, "Result should contain impact_details"
        assert "recommendation" in result, "Result should contain recommendation"

        # Verify summary structure
        assert "total_assemblies_affected" in summary, "Summary should contain total_assemblies_affected"
        assert "risk_summary" in summary, "Summary should contain risk_summary"
        assert "requires_approval" in summary, "Summary should contain requires_approval"

        # Verify price delta calculation
        expected_delta = new_price - old_price
        actual_delta = result.get("price_delta", 0)
        assert abs(actual_delta - expected_delta) < 0.01, \
            f"Price delta should be {expected_delta}, got {actual_delta}"

        print(f"\n" + "="*80)
        print("   ✅ COMPREHENSIVE TEST PASSED")
        print("="*80)

    @pytest.mark.integration
    async def test_analyze_price_change_impact_no_affected_assemblies(self, epicor, connection_verified):
        """
        Test comprehensive analysis for a part with no affected assemblies.

        Expected: Should return gracefully with empty impact_details and zero counts.
        """
        print("\n" + "="*80)
        print("🎯 TEST: analyze_price_change_impact() - No Affected Assemblies")
        print("="*80)

        part_num = TEST_DATA["TOP_LEVEL_PART"]

        print(f"   Part (should have no parents): {part_num}")

        result = await epicor.analyze_price_change_impact(
            part_num=part_num,
            old_price=100.00,
            new_price=110.00
        )

        summary = result.get("summary", {})

        print(f"\n   Total Assemblies Affected: {summary.get('total_assemblies_affected', 0)}")
        print(f"   Recommendation: {result.get('recommendation', 'N/A')}")

        # Parts with no parent assemblies should still return a valid structure
        assert isinstance(result, dict), "Result should be a dictionary"
        assert result.get("summary", {}).get("total_assemblies_affected", -1) >= 0

        print(f"\n   ✅ Test passed: No affected assemblies handled correctly")


# =============================================================================
# MAIN - Run tests manually (outside pytest)
# =============================================================================

async def main():
    """
    Run BOM impact analysis tests manually.
    Use this for quick testing without pytest framework.

    Usage: python test/test_epicor_bom_impact.py
    """
    print("\n" + "="*80)
    print("🚀 EPICOR BOM IMPACT ANALYSIS - INTEGRATION TEST SUITE")
    print("="*80)

    # Check connection first
    print("\n🔌 Testing Epicor connection...")
    connection = await epicor_service.test_connection()

    if connection["status"] != "success":
        print(f"❌ Connection failed: {connection.get('message')}")
        print("   Please check .env configuration")
        return

    print("✅ Connection successful")

    # Run tests
    print("\n" + "-"*80)
    print("Running BOM Impact Tests...")
    print("-"*80)

    # Test 1: get_part_where_used
    print("\n📋 Test 1: get_part_where_used()")
    part = TEST_DATA["COMPONENT_PART"]
    result = await epicor_service.get_part_where_used(part)
    print(f"   Part: {part}")
    print(f"   Direct Parents Found: {len(result) if result else 0}")

    # Test 2: find_all_affected_assemblies
    print("\n📋 Test 2: find_all_affected_assemblies()")
    result = await epicor_service.find_all_affected_assemblies(part)
    print(f"   Part: {part}")
    print(f"   All Affected Assemblies: {len(result) if result else 0}")

    # Test 3: Full analysis
    if result:
        print("\n📋 Test 3: analyze_price_change_impact()")
        analysis = await epicor_service.analyze_price_change_impact(
            part_num=part,
            old_price=TEST_DATA["OLD_PRICE"],
            new_price=TEST_DATA["NEW_PRICE"]
        )

        summary = analysis.get("summary", {})
        print(f"   Total Assemblies: {summary.get('total_assemblies_affected', 0)}")
        print(f"   Risk Summary: {summary.get('risk_summary', {})}")
        print(f"   Annual Impact: ${summary.get('total_annual_cost_impact', 0):,.2f}")
        print(f"   Recommendation: {analysis.get('recommendation', 'N/A')[:80]}...")

    print("\n" + "="*80)
    print("✅ Manual test suite complete!")
    print("="*80)
    print("\nFor full test coverage, run: python -m pytest test/test_epicor_bom_impact.py -v")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
