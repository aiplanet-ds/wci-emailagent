"""
Test script to demonstrate the process_supplier_price_change() method.

This script simulates processing a supplier price change email end-to-end
using real Epicor data.
"""

import json
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.epicor_service import EpicorAPIService


def print_section(title: str):
    """Print a formatted section header."""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


def print_json(data: dict, indent: int = 2):
    """Pretty print JSON data."""
    print(json.dumps(data, indent=indent, default=str))


def main():
    print_section("SUPPLIER PRICE CHANGE PROCESSING DEMO")
    
    # Initialize service
    epicor = EpicorAPIService()
    
    # Simulate email-extracted data
    # Using real test data from your Epicor instance
    email_data = {
        "part_num": "#FFH06-12SAE F",  # Component used in assemblies
        "supplier_id": "FAST1",         # Known supplier
        "old_price": 1.25,
        "new_price": 1.50,              # 20% price increase
        "effective_date": "2025-01-15",
        "email_metadata": {
            "subject": "Price Update Notice - Part #FFH06-12SAE F",
            "from": "pricing@fastenersupplier.com",
            "received_date": "2024-12-10T09:30:00Z",
            "email_id": "MSG-12345"
        }
    }
    
    print("\n📧 Simulated Email Data Extracted:")
    print("-" * 40)
    print(f"   Part Number: {email_data['part_num']}")
    print(f"   Supplier ID: {email_data['supplier_id']}")
    print(f"   Old Price:   ${email_data['old_price']:.4f}")
    print(f"   New Price:   ${email_data['new_price']:.4f}")
    print(f"   Change:      ${email_data['new_price'] - email_data['old_price']:.4f} ({((email_data['new_price'] - email_data['old_price']) / email_data['old_price'] * 100):.1f}%)")
    print(f"   Effective:   {email_data['effective_date']}")
    
    print_section("PROCESSING PRICE CHANGE...")
    
    # Call the new orchestration method
    result = epicor.process_supplier_price_change(
        part_num=email_data["part_num"],
        supplier_id=email_data["supplier_id"],
        old_price=email_data["old_price"],
        new_price=email_data["new_price"],
        effective_date=email_data["effective_date"],
        email_metadata=email_data["email_metadata"]
    )
    
    # Display results
    print_section("PROCESSING RESULTS")
    
    print(f"\n📊 Status: {result['status'].upper()}")
    print(f"⏱️  Timestamp: {result['timestamp']}")
    
    # Component validation
    print("\n🔧 Component Validation:")
    if result.get("component"):
        comp = result["component"]
        if comp.get("validated"):
            print(f"   ✅ {comp['part_num']} - {comp.get('description', 'N/A')}")
            print(f"      UOM: {comp.get('uom', 'N/A')}, Current Cost: ${comp.get('current_cost', 0):.4f}")
        else:
            print(f"   ❌ {comp['part_num']} - {comp.get('error', 'Not found')}")
    
    # Supplier validation
    print("\n🏭 Supplier Validation:")
    if result.get("supplier"):
        supp = result["supplier"]
        if supp.get("validated"):
            print(f"   ✅ {supp['supplier_id']} - {supp.get('name', 'N/A')}")
            print(f"      Vendor Num: {supp.get('vendor_num', 'N/A')}")
        else:
            print(f"   ❌ {supp['supplier_id']} - {supp.get('error', 'Not found')}")
    
    # BOM Impact Summary
    if result.get("bom_impact") and "summary" in result["bom_impact"]:
        bom = result["bom_impact"]
        summary = bom["summary"]
        
        print("\n📈 BOM Impact Summary:")
        print(f"   Total Assemblies Affected: {summary['total_assemblies_affected']}")
        print(f"   Total Annual Cost Impact:  ${summary['total_annual_cost_impact']:,.2f}")
        print(f"   Assemblies with Forecast:  {summary.get('demand_from_forecast', 0)}")
        
        risk = summary.get("risk_summary", {})
        print(f"\n   Risk Breakdown:")
        print(f"      🔴 Critical: {risk.get('critical', 0)}")
        print(f"      🟠 High:     {risk.get('high', 0)}")
        print(f"      🟡 Medium:   {risk.get('medium', 0)}")
        print(f"      🟢 Low:      {risk.get('low', 0)}")
        print(f"      ⚪ Unknown:  {risk.get('unknown', 0)}")
        
        # High-risk assemblies
        high_risk = bom.get("high_risk_assemblies", [])
        if high_risk:
            print(f"\n   ⚠️ High-Risk Assemblies ({len(high_risk)}):")
            for hr in high_risk[:5]:  # Show top 5
                print(f"      • {hr['assembly_part_num']}: {hr['risk_level'].upper()}")
                print(f"        Margin: {hr.get('current_margin_pct', 0):.1f}% → {hr.get('new_margin_pct', 0):.1f}%")
        
        print(f"\n   💬 Recommendation: {bom.get('recommendation', 'N/A')}")
    
    # Actions Required
    print("\n📋 Actions Required:")
    for action in result.get("actions_required", []):
        priority_icon = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢", "required": "📌"}.get(action.get("priority", ""), "•")
        print(f"   {priority_icon} [{action.get('priority', 'N/A').upper()}] {action['action']}")
        print(f"      {action.get('description', '')}")
    
    # Auto-approval status
    print(f"\n🤖 Can Auto-Approve: {'✅ Yes' if result.get('can_auto_approve') else '❌ No - Manual approval required'}")
    
    # Processing errors
    if result.get("processing_errors"):
        print(f"\n⚠️ Processing Errors ({len(result['processing_errors'])}):")
        for err in result["processing_errors"]:
            print(f"   • {err}")
    
    # Full JSON output
    print_section("FULL JSON RESPONSE (for frontend)")
    print_json(result)
    
    return result


if __name__ == "__main__":
    main()

