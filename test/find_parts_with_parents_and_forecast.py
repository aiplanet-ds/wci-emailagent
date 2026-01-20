"""
Script to find parts that have BOTH:
1. Parent assemblies (used as components in BOMs)
2. Forecast data available

This script connects to Epicor using the existing credentials from the configuration
and displays detailed information about 5 qualifying parts.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import requests
from dotenv import load_dotenv
from services.epicor_service import epicor_service
from services.epicor_auth import epicor_auth

load_dotenv()


def get_api_headers():
    """Get authentication headers for Epicor API requests"""
    base_url = os.getenv('EPICOR_BASE_URL')
    api_key = os.getenv('EPICOR_API_KEY')
    token = epicor_auth.get_valid_token()

    headers = {
        'Authorization': f'Bearer {token}',
        'X-API-Key': api_key,
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }
    return headers, base_url, os.getenv('EPICOR_COMPANY_ID')


def get_parts_with_forecasts(headers, base_url, company_id, limit=200):
    """
    Get parts that have forecast data by querying the Forecast table directly.
    Returns a set of part numbers that have forecasts.
    """
    print("\n📋 Step 1: Fetching parts with forecast data...")
    print("-" * 80)

    parts_with_forecast = set()

    url = f'{base_url}/{company_id}/Erp.BO.ForecastSvc/Forecasts'
    params = {
        '$top': limit,
        '$select': 'PartNum,ForeDate,ForeQty',
        '$filter': 'ForeQty gt 0',
        '$orderby': 'ForeDate desc'
    }

    try:
        response = requests.get(url, headers=headers, params=params, timeout=30)
        if response.status_code == 200:
            data = response.json()
            forecasts = data.get('value', [])
            print(f"   Found {len(forecasts)} forecast records")

            for forecast in forecasts:
                part_num = forecast.get('PartNum')
                if part_num:
                    parts_with_forecast.add(part_num)

            print(f"   Found {len(parts_with_forecast)} unique parts with forecasts:")
            for p in list(parts_with_forecast)[:10]:
                print(f"      - {p}")
            if len(parts_with_forecast) > 10:
                print(f"      ... and {len(parts_with_forecast) - 10} more")
        else:
            print(f"   ⚠️ Error fetching forecasts: {response.status_code}")
            print(f"   {response.text[:300]}")
    except Exception as e:
        print(f"   ⚠️ Exception: {e}")

    return parts_with_forecast


def get_candidate_parts(headers, base_url, company_id, limit=200):
    """
    Get candidate parts to check for BOTH parent assemblies AND forecast data.

    Strategy:
    1. Query Forecast table to get parts with forecasts
    2. For each part with forecast, use get_part_where_used() to check for parent assemblies
    3. This ensures we're checking PARTS (not assemblies) that have forecasts
    """
    print("\n" + "=" * 80)
    print("📋 Finding PARTS with BOTH parent assemblies AND forecast data")
    print("=" * 80)

    # Step 1: Get parts that have forecast data
    forecast_parts = get_parts_with_forecasts(headers, base_url, company_id, limit)

    # Build candidate list from parts with forecasts
    # These are parts (not assemblies) - we'll verify they have parent assemblies using get_part_where_used
    candidates = []

    # PRIORITY 1: Parts with forecasts (need to check if they have parent assemblies)
    print(f"\n📋 Step 2: Building candidate list from parts with forecasts...")
    for part_num in forecast_parts:
        candidates.append({
            'PartNum': part_num,
            'PartDescription': 'Part with forecast',
            'Source': 'Forecast',
            'HasForecast': True
        })

    # PRIORITY 2: Add known test parts that are components
    known_component_parts = ['#FFH06-12SAE F', 'JD5866']
    print(f"\n   Adding {len(known_component_parts)} known component parts...")
    seen = {c['PartNum'] for c in candidates}
    for part_num in known_component_parts:
        if part_num not in seen:
            candidates.append({
                'PartNum': part_num,
                'PartDescription': 'Known component part',
                'Source': 'KnownComponent',
                'HasForecast': False  # Will be verified
            })
            seen.add(part_num)

    print(f"\n   Total candidates to check: {len(candidates)}")
    return candidates


def check_part_qualifies(part_num):
    """
    Check if a part has both parent assemblies and forecast data.
    Returns tuple: (has_parents, parent_info, has_forecast, forecast_info)
    """
    # Check for parent assemblies
    parents = epicor_service.get_part_where_used(part_num)
    has_parents = len(parents) > 0 if parents else False
    
    # Check for forecast data
    forecast = epicor_service.get_part_forecast(part_num, weeks_ahead=52)
    has_forecast = forecast.get('forecast_records', 0) > 0
    
    return has_parents, parents, has_forecast, forecast


def display_part_details(part_num, description, parents, forecast, index):
    """Display detailed information about a qualifying part"""
    print(f"\n{'='*80}")
    print(f"📦 PART {index}: {part_num}")
    print(f"{'='*80}")
    print(f"   Description: {description}")
    
    # Display parent assembly information
    print(f"\n   🔗 PARENT ASSEMBLIES ({len(parents)} found):")
    print(f"   {'-'*70}")
    for parent in parents[:10]:  # Show up to 10 parents
        parent_num = parent.get('PartNum', 'N/A')
        revision = parent.get('RevisionNum', 'N/A')
        qty_per = parent.get('QtyPer', 0)
        parent_desc = parent.get('Description', 'N/A')[:40]
        print(f"      • {parent_num} (Rev: {revision}, QtyPer: {qty_per})")
        if parent_desc and parent_desc != 'N/A':
            print(f"        Description: {parent_desc}")
    if len(parents) > 10:
        print(f"      ... and {len(parents) - 10} more parent assemblies")
    
    # Display forecast information
    print(f"\n   📈 FORECAST DATA:")
    print(f"   {'-'*70}")
    print(f"      Total Forecast Qty: {forecast.get('total_forecast_qty', 0)}")
    print(f"      Weekly Demand: {forecast.get('weekly_demand', 0):.4f}")
    print(f"      Annual Demand: {forecast.get('annual_demand', 0)}")
    print(f"      Forecast Records: {forecast.get('forecast_records', 0)}")
    
    # Show individual forecast entries
    forecasts = forecast.get('forecasts', [])
    if forecasts:
        print(f"\n      Forecast Details (up to 5 records):")
        for f in forecasts[:5]:
            fore_date = f.get('ForeDate', 'N/A')
            fore_qty = f.get('ForeQty', 0)
            plant = f.get('Plant', 'N/A')
            customer = f.get('CustomerName', 'N/A')
            print(f"        - Date: {fore_date}, Qty: {fore_qty}, Plant: {plant}")
            if customer and customer != 'N/A':
                print(f"          Customer: {customer}")
        if len(forecasts) > 5:
            print(f"        ... and {len(forecasts) - 5} more forecast records")


def main():
    """Main function to find and display qualifying parts"""
    print("=" * 80)
    print("🔍 FINDING PARTS WITH PARENT ASSEMBLIES AND FORECAST DATA")
    print("=" * 80)
    print("\nConnecting to Epicor using existing credentials...")
    
    # Get API credentials
    headers, base_url, company_id = get_api_headers()
    print(f"   Base URL: {base_url}")
    print(f"   Company ID: {company_id}")
    
    # Test connection
    connection = epicor_service.test_connection()
    if connection.get('status') != 'success':
        print(f"\n❌ Connection failed: {connection.get('message')}")
        return
    print("   ✅ Connected successfully!")
    
    # Get candidate parts
    candidates = get_candidate_parts(headers, base_url, company_id, limit=200)
    print(f"\n   Found {len(candidates)} unique component parts to check")
    
    # Find parts that qualify (have both parents AND forecast)
    qualifying_parts = []
    parts_checked = 0
    target_count = 5
    
    print(f"\n🔎 Checking parts for parent assemblies AND forecast data...")
    print(f"   Target: Find {target_count} qualifying parts")
    print("-" * 80)
    
    for candidate in candidates:
        part_num = candidate['PartNum']
        parts_checked += 1
        
        print(f"   Checking [{parts_checked}/{len(candidates)}]: {part_num}...", end=" ")
        
        has_parents, parents, has_forecast, forecast = check_part_qualifies(part_num)
        
        if has_parents and has_forecast:
            print(f"✅ QUALIFIES (Parents: {len(parents)}, Forecasts: {forecast.get('forecast_records', 0)})")
            qualifying_parts.append({
                'part_num': part_num,
                'description': candidate['PartDescription'],
                'parents': parents,
                'forecast': forecast
            })
            
            if len(qualifying_parts) >= target_count:
                break
        else:
            status = []
            if not has_parents:
                status.append("No parents")
            if not has_forecast:
                status.append("No forecast")
            print(f"❌ ({', '.join(status)})")
    
    # Display results
    print("\n" + "=" * 80)
    print(f"📋 RESULTS: Found {len(qualifying_parts)} parts with BOTH parents AND forecast")
    print("=" * 80)
    
    if not qualifying_parts:
        print("\n⚠️ No parts found that have both parent assemblies and forecast data.")
        print("   This could mean:")
        print("   - Forecasts are not set up for component parts in this Epicor instance")
        print("   - The search needs to be expanded (increase limit parameter)")
        return
    
    # Display detailed information for each qualifying part
    for i, part in enumerate(qualifying_parts, 1):
        display_part_details(
            part['part_num'],
            part['description'],
            part['parents'],
            part['forecast'],
            i
        )
    
    # Summary
    print("\n" + "=" * 80)
    print("📊 SUMMARY")
    print("=" * 80)
    print(f"   Parts checked: {parts_checked}")
    print(f"   Qualifying parts found: {len(qualifying_parts)}")
    print(f"\n   Qualifying Part Numbers:")
    for i, part in enumerate(qualifying_parts, 1):
        parent_count = len(part['parents'])
        forecast_qty = part['forecast'].get('total_forecast_qty', 0)
        print(f"      {i}. {part['part_num']} - {parent_count} parents, {forecast_qty} forecast qty")


if __name__ == "__main__":
    main()

