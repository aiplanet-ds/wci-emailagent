"""
Explore demand data details from available Epicor endpoints.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import requests
import json
from dotenv import load_dotenv
from services.epicor_auth import epicor_auth

load_dotenv()

def explore_endpoint_details():
    """Explore demand endpoint details"""
    
    base_url = os.getenv('EPICOR_BASE_URL')
    company_id = os.getenv('EPICOR_COMPANY_ID')
    api_key = os.getenv('EPICOR_API_KEY')
    
    token = epicor_auth.get_valid_token()
    
    headers = {
        'Authorization': f'Bearer {token}',
        'X-API-Key': api_key,
        'Content-Type': 'application/json'
    }
    
    test_part = "K9790"  # Our known assembly part
    
    print("="*80)
    print("🔍 EXPLORING DEMAND DATA DETAILS FOR ASSEMBLY: " + test_part)
    print("="*80)
    
    # 1. Check Forecast data
    print("\n📊 1. FORECAST DATA (Erp.BO.ForecastSvc/Forecasts)")
    print("-"*80)
    url = f'{base_url}/{company_id}/Erp.BO.ForecastSvc/Forecasts'
    params = {'$top': 10}
    
    response = requests.get(url, headers=headers, params=params, timeout=15)
    if response.status_code == 200:
        data = response.json().get('value', [])
        print(f"   Total forecasts found: {len(data)}")
        if data:
            print(f"   Sample record:")
            for key, value in data[0].items():
                if value and str(value).strip():
                    print(f"      {key}: {value}")
    
    # Check for specific part forecast
    params = {'$filter': f"PartNum eq '{test_part}'", '$top': 5}
    response = requests.get(url, headers=headers, params=params, timeout=15)
    if response.status_code == 200:
        data = response.json().get('value', [])
        print(f"\n   Forecasts for {test_part}: {len(data)}")
    
    # 2. Check PartPlant (Planning parameters)
    print("\n📊 2. PART PLANT DATA - Planning Parameters")
    print("-"*80)
    url = f'{base_url}/{company_id}/Erp.BO.PartSvc/PartPlants'
    params = {'$filter': f"PartNum eq '{test_part}'"}
    
    response = requests.get(url, headers=headers, params=params, timeout=15)
    if response.status_code == 200:
        data = response.json().get('value', [])
        print(f"   PartPlant records for {test_part}: {len(data)}")
        if data:
            for key, value in data[0].items():
                if value and str(value).strip() and value != 0:
                    print(f"      {key}: {value}")
    
    # 3. Check PartWhse (Warehouse with DemandQty)
    print("\n📊 3. PART WAREHOUSE DATA - Inventory & Demand")
    print("-"*80)
    url = f'{base_url}/{company_id}/Erp.BO.PartSvc/PartWhses'
    params = {'$filter': f"PartNum eq '{test_part}'"}
    
    response = requests.get(url, headers=headers, params=params, timeout=15)
    if response.status_code == 200:
        data = response.json().get('value', [])
        print(f"   PartWhse records for {test_part}: {len(data)}")
        if data:
            for key, value in data[0].items():
                if value and str(value).strip() and value != 0:
                    print(f"      {key}: {value}")
    
    # 4. Check Sales Order details for historical demand
    print("\n📊 4. SALES ORDER LINES (Historical Demand)")
    print("-"*80)
    url = f'{base_url}/{company_id}/Erp.BO.SalesOrderSvc/OrderDtls'
    params = {'$filter': f"PartNum eq '{test_part}'", '$top': 10}
    
    response = requests.get(url, headers=headers, params=params, timeout=15)
    if response.status_code == 200:
        data = response.json().get('value', [])
        print(f"   Order lines for {test_part}: {len(data)}")
        if data:
            total_qty = sum(d.get('OrderQty', 0) for d in data)
            print(f"   Total ordered quantity (sample): {total_qty}")
            for d in data[:3]:
                print(f"      Order {d.get('OrderNum')}: Qty={d.get('OrderQty')}, Date={d.get('NeedByDate')}")
    else:
        print(f"   Status: {response.status_code}")
        # Try alternate endpoint
        url = f'{base_url}/{company_id}/Erp.BO.SalesOrderSvc/SalesOrders'
        params = {'$top': 3, '$expand': 'OrderDtls'}
        response = requests.get(url, headers=headers, params=params, timeout=15)
        if response.status_code == 200:
            data = response.json().get('value', [])
            print(f"   Sample Orders with details: {len(data)}")
            for order in data[:2]:
                dtls = order.get('OrderDtls', [])
                print(f"      Order {order.get('OrderNum')}: {len(dtls)} lines")

    print("\n" + "="*80)
    print("📋 DEMAND DATA OPTIONS FOR ANNUAL IMPACT CALCULATION")
    print("="*80)
    print("""
    Option 1: ForecastSvc (Best for planned demand)
       - ForeQty field contains forecast quantity
       - ForeDate for time period
       - Filter by PartNum to get assembly forecasts
       
    Option 2: PartPlant (MRP planning parameters)  
       - MinimumQty, MaximumQty, SafetyQty
       - Can infer demand from min/max settings
       
    Option 3: PartWhse (Current demand)
       - DemandQty field shows current demand
       - Good for real-time snapshot
       
    Option 4: SalesOrder/OrderDtls (Historical demand)
       - Sum OrderQty over time period
       - Calculate average weekly demand from history
    """)

if __name__ == "__main__":
    explore_endpoint_details()

