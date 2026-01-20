"""
Test script to verify forecast-based annual impact calculation.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services.epicor_service import epicor_service

def test_forecast_demand():
    """Test the forecast-based annual impact calculation"""

    print("="*80)
    print("🧪 TESTING FORECAST-BASED ANNUAL IMPACT CALCULATION")
    print("="*80)

    # Test component - use our known component
    component_part = "#FFH06-12SAE F"
    old_price = 10.00
    new_price = 12.50
    price_delta = new_price - old_price

    print(f"\n📦 Component: {component_part}")
    print(f"💰 Price change: ${old_price:.2f} → ${new_price:.2f} (delta: ${price_delta:.2f})")

    # Also test forecast retrieval for parts that HAVE forecast data
    print("\n" + "-"*80)
    print("Step 0: Testing forecast retrieval for a part WITH forecast data...")
    print("-"*80)

    # This part has forecast data in Epicor
    forecast_test_part = "JD5866"
    forecast = epicor_service.get_part_forecast(forecast_test_part)
    print(f"\n   📊 Forecast for {forecast_test_part}:")
    print(f"      Total forecast qty: {forecast.get('total_forecast_qty', 0)}")
    print(f"      Weekly demand: {forecast.get('weekly_demand', 0):.4f}")
    print(f"      Forecast records: {forecast.get('forecast_records', 0)}")
    
    # Step 1: Find affected assemblies
    print("\n" + "-"*80)
    print("Step 1: Finding affected assemblies...")
    print("-"*80)
    
    affected = epicor_service.find_all_affected_assemblies(component_part)
    print(f"   Found {len(affected)} affected assemblies")
    
    for a in affected:
        print(f"   - {a['assembly_part_num']} (Level {a['bom_level']}, Qty: {a['cumulative_qty']})")
    
    if not affected:
        print("   ⚠️ No affected assemblies found - using sample data for demo")
        affected = [
            {"assembly_part_num": "K9790", "revision": "B", "qty_per": 1.0, "cumulative_qty": 1.0, "bom_level": 1}
        ]
    
    # Step 2: Test get_part_forecast for individual parts
    print("\n" + "-"*80)
    print("Step 2: Testing get_part_forecast()...")
    print("-"*80)
    
    for assembly in affected[:3]:  # Test first 3
        part_num = assembly['assembly_part_num']
        forecast = epicor_service.get_part_forecast(part_num)
        print(f"\n   📊 Forecast for {part_num}:")
        print(f"      Total forecast qty: {forecast.get('total_forecast_qty', 0)}")
        print(f"      Weekly demand: {forecast.get('weekly_demand', 0):.4f}")
        print(f"      Forecast records: {forecast.get('forecast_records', 0)}")
    
    # Step 3: Test calculate_annual_impact WITHOUT forecast
    print("\n" + "-"*80)
    print("Step 3: Annual impact WITHOUT forecast (use_forecast=False)...")
    print("-"*80)
    
    result_no_forecast = epicor_service.calculate_annual_impact(
        price_delta=price_delta,
        affected_assemblies=affected,
        use_forecast=False
    )
    
    print(f"   Total annual impact: ${result_no_forecast['total_annual_impact']:,.2f}")
    print(f"   Assemblies with demand: {result_no_forecast['assemblies_with_demand_data']}")
    
    # Step 4: Test calculate_annual_impact WITH forecast
    print("\n" + "-"*80)
    print("Step 4: Annual impact WITH forecast (use_forecast=True)...")
    print("-"*80)
    
    result_with_forecast = epicor_service.calculate_annual_impact(
        price_delta=price_delta,
        affected_assemblies=affected,
        use_forecast=True
    )
    
    print(f"   Total annual impact: ${result_with_forecast['total_annual_impact']:,.2f}")
    print(f"   Assemblies with demand: {result_with_forecast['assemblies_with_demand_data']}")
    print(f"   Demand from forecast: {result_with_forecast.get('demand_from_forecast', 0)}")
    
    print("\n   Impact by assembly:")
    for impact in result_with_forecast['impact_by_assembly']:
        print(f"      {impact['assembly_part_num']}: "
              f"Weekly={impact['weekly_demand']:.2f}, "
              f"Annual Impact=${impact['annual_cost_impact']:,.2f}, "
              f"Source={impact['demand_source']}")
    
    # Step 5: Test with manual override
    print("\n" + "-"*80)
    print("Step 5: Annual impact with MANUAL OVERRIDE (100 units/week)...")
    print("-"*80)
    
    manual_demand = {a['assembly_part_num']: 100.0 for a in affected}
    
    result_override = epicor_service.calculate_annual_impact(
        price_delta=price_delta,
        affected_assemblies=affected,
        weekly_demand_override=manual_demand,
        use_forecast=True  # Even with forecast enabled, override takes priority
    )
    
    print(f"   Total annual impact: ${result_override['total_annual_impact']:,.2f}")
    print(f"   Assemblies with demand: {result_override['assemblies_with_demand_data']}")
    
    for impact in result_override['impact_by_assembly']:
        print(f"      {impact['assembly_part_num']}: "
              f"Weekly={impact['weekly_demand']:.2f}, "
              f"Annual=${impact['annual_cost_impact']:,.2f}, "
              f"Source={impact['demand_source']}")
    
    # Summary
    print("\n" + "="*80)
    print("📋 SUMMARY")
    print("="*80)
    print(f"""
    Component: {component_part}
    Price Change: ${old_price:.2f} → ${new_price:.2f}
    Affected Assemblies: {len(affected)}
    
    Annual Impact Comparison:
    - Without forecast data:  ${result_no_forecast['total_annual_impact']:,.2f}
    - With Epicor forecast:   ${result_with_forecast['total_annual_impact']:,.2f}
    - With manual override:   ${result_override['total_annual_impact']:,.2f}
    """)

if __name__ == "__main__":
    test_forecast_demand()

