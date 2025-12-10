"""
Script to explore Epicor endpoints for demand/forecast data.
This will help identify where to get weekly/annual demand data for parts.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import requests
from dotenv import load_dotenv
from services.epicor_auth import epicor_auth

load_dotenv()

def explore_demand_endpoints():
    """Explore available Epicor endpoints for demand data"""
    
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
    print("🔍 EXPLORING EPICOR DEMAND/FORECAST ENDPOINTS")
    print("="*80)
    
    # List of potential demand-related endpoints to check
    endpoints = [
        # Forecast/Demand
        ("Erp.BO.ForecastSvc/Forecasts", "Forecast - Sales forecasts"),
        ("Erp.BO.PartForecastSvc/PartForecasts", "Part Forecast"),
        ("Erp.BO.DemandHeadSvc/DemandHeads", "Demand Header"),
        ("Erp.BO.DemandDetailSvc/DemandDetails", "Demand Detail"),
        
        # Sales/Orders
        ("Erp.BO.SalesOrderSvc/SalesOrders", "Sales Orders - Order history"),
        ("Erp.BO.OrderDtlSvc/OrderDtls", "Order Details - Line items"),
        ("Erp.BO.OrderHistSvc/OrderHists", "Order History"),
        
        # MRP/Planning
        ("Erp.BO.PartPlantSvc/PartPlants", "Part Plant - Planning params"),
        ("Erp.BO.MRPProcQueueSvc/MRPProcQueues", "MRP Process Queue"),
        ("Erp.BO.SuggPoSvc/SuggPos", "Suggested POs from MRP"),
        
        # Production/Jobs
        ("Erp.BO.JobEntrySvc/JobHeads", "Job Entry - Production jobs"),
        ("Erp.BO.JobProdSvc/JobProds", "Job Production"),
        ("Erp.BO.JobMtlSvc/JobMtls", "Job Materials"),
        
        # Part info that may contain demand fields
        ("Erp.BO.PartSvc/PartPlants", "Part Plants - Min/Max/Safety Stock"),
        ("Erp.BO.PartSvc/PartWhses", "Part Warehouse - Inventory"),
    ]
    
    results = []
    
    for endpoint, description in endpoints:
        url = f'{base_url}/{company_id}/{endpoint}'
        params = {'$top': 3}
        
        try:
            response = requests.get(url, headers=headers, params=params, timeout=15)
            status = response.status_code
            
            if status == 200:
                data = response.json()
                count = len(data.get('value', []))
                sample = data.get('value', [{}])[0] if data.get('value') else {}
                fields = list(sample.keys())[:8] if sample else []
                
                print(f"\n✅ {description}")
                print(f"   Endpoint: {endpoint}")
                print(f"   Status: {status} | Records: {count}+")
                print(f"   Sample fields: {fields}")
                
                results.append({
                    'endpoint': endpoint,
                    'description': description,
                    'status': 'available',
                    'sample_fields': fields
                })
            else:
                print(f"\n❌ {description}")
                print(f"   Endpoint: {endpoint}")
                print(f"   Status: {status}")
                
        except Exception as e:
            print(f"\n⚠️ {description}")
            print(f"   Endpoint: {endpoint}")
            print(f"   Error: {str(e)[:50]}")
    
    print("\n" + "="*80)
    print("📋 SUMMARY - AVAILABLE DEMAND DATA SOURCES")
    print("="*80)
    
    available = [r for r in results if r['status'] == 'available']
    if available:
        print(f"\n✅ Found {len(available)} available endpoints:\n")
        for r in available:
            print(f"   • {r['description']}: {r['endpoint']}")
    else:
        print("\n⚠️ No demand endpoints found available")

if __name__ == "__main__":
    explore_demand_endpoints()

