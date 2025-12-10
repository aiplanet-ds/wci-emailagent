"""
Check what parts have forecast data in Epicor.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import requests
from dotenv import load_dotenv
from services.epicor_auth import epicor_auth

load_dotenv()

def check_forecast_data():
    """Check available forecast data"""
    
    base_url = os.getenv('EPICOR_BASE_URL')
    company_id = os.getenv('EPICOR_COMPANY_ID')
    api_key = os.getenv('EPICOR_API_KEY')
    
    token = epicor_auth.get_valid_token()
    
    headers = {
        'Authorization': f'Bearer {token}',
        'X-API-Key': api_key,
        'Content-Type': 'application/json'
    }
    
    print("="*80)
    print("🔍 CHECKING FORECAST DATA IN EPICOR")
    print("="*80)
    
    # Get all forecasts (limited)
    url = f'{base_url}/{company_id}/Erp.BO.ForecastSvc/Forecasts'
    params = {
        '$top': 50,
        '$select': 'PartNum,ForeDate,ForeQty,Plant,CustomerName',
        '$orderby': 'ForeDate desc'
    }
    
    response = requests.get(url, headers=headers, params=params, timeout=15)
    
    if response.status_code == 200:
        data = response.json().get('value', [])
        print(f"\n✅ Found {len(data)} forecast records")
        
        # Group by part number
        parts = {}
        for f in data:
            part = f.get('PartNum')
            if part not in parts:
                parts[part] = []
            parts[part].append(f)
        
        print(f"\n📊 Parts with forecasts: {len(parts)}")
        print("-"*80)
        
        for part, forecasts in list(parts.items())[:15]:
            total_qty = sum(float(f.get('ForeQty', 0)) for f in forecasts)
            print(f"\n   {part}")
            print(f"      Records: {len(forecasts)}")
            print(f"      Total Forecast Qty: {total_qty}")
            if forecasts:
                print(f"      Sample: {forecasts[0].get('ForeDate')[:10]} - Qty: {forecasts[0].get('ForeQty')}")
        
        # Try to find one that might be an assembly
        print("\n" + "="*80)
        print("🧪 Testing forecast retrieval for a part WITH data...")
        print("="*80)
        
        if parts:
            test_part = list(parts.keys())[0]
            print(f"\nTesting part: {test_part}")
            
            from services.epicor_service import epicor_service
            forecast = epicor_service.get_part_forecast(test_part)
            
            print(f"   Total forecast qty: {forecast.get('total_forecast_qty')}")
            print(f"   Weekly demand: {forecast.get('weekly_demand'):.4f}")
            print(f"   Forecast records: {forecast.get('forecast_records')}")
    else:
        print(f"❌ Error: {response.status_code}")
        print(response.text[:300])

if __name__ == "__main__":
    check_forecast_data()

