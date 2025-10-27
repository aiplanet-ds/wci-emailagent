"""
Discover ListType values used in existing Epicor price lists
This helps identify what ListType value to use when creating new price lists
"""

import os
import requests
from dotenv import load_dotenv
from collections import Counter

load_dotenv()

BASE_URL = os.getenv("EPICOR_BASE_URL")
API_KEY = os.getenv("EPICOR_API_KEY")
BEARER_TOKEN = os.getenv("EPICOR_BEARER_TOKEN")
COMPANY_ID = os.getenv("EPICOR_COMPANY_ID")

def get_headers():
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    if BEARER_TOKEN and BEARER_TOKEN != "your-epicor-bearer-token-here":
        headers["Authorization"] = f"Bearer {BEARER_TOKEN}"
    if API_KEY:
        headers["X-api-Key"] = API_KEY
    return headers

print("=" * 80)
print("DISCOVERING LISTTYPE VALUES IN EPICOR PRICE LISTS")
print("=" * 80)

# Query all price lists
url = f"{BASE_URL}/{COMPANY_ID}/Erp.BO.PriceLstSvc/PriceLsts"
params = {
    "$filter": f"Company eq '{COMPANY_ID}'",
    "$top": "100"  # Get up to 100 price lists
}

print(f"\nQuerying price lists...")
print(f"URL: {url}")

response = requests.get(url, headers=get_headers(), params=params, timeout=10)

print(f"\nStatus: {response.status_code}")

if response.status_code == 200:
    data = response.json()
    price_lists = data.get("value", [])

    print(f"\nFound {len(price_lists)} price lists")

    if price_lists:
        # Extract all ListType values
        list_types = []
        list_type_examples = {}

        for pl in price_lists:
            list_type = pl.get("ListType", "NOT SET")
            list_code = pl.get("ListCode", "")
            description = pl.get("ListDescription", "")

            list_types.append(list_type)

            # Store an example for each ListType
            if list_type not in list_type_examples:
                list_type_examples[list_type] = {
                    "ListCode": list_code,
                    "ListDescription": description,
                    "full_record": pl
                }

        # Count occurrences of each ListType
        type_counts = Counter(list_types)

        print("\n" + "=" * 80)
        print("LISTTYPE ANALYSIS")
        print("=" * 80)

        print(f"\nUnique ListType values found: {len(type_counts)}")
        print("\nListType Distribution:")
        for list_type, count in type_counts.most_common():
            percentage = (count / len(price_lists)) * 100
            print(f"  '{list_type}': {count} price lists ({percentage:.1f}%)")

        # Show examples of each ListType
        print("\n" + "=" * 80)
        print("EXAMPLES OF EACH LISTTYPE")
        print("=" * 80)

        for list_type, example in list_type_examples.items():
            print(f"\nListType: '{list_type}'")
            print(f"  Example Code: {example['ListCode']}")
            print(f"  Example Description: {example['ListDescription']}")

        # Determine most common ListType
        most_common_type = type_counts.most_common(1)[0][0]

        print("\n" + "=" * 80)
        print("RECOMMENDATION")
        print("=" * 80)

        print(f"\nMost commonly used ListType: '{most_common_type}'")
        print(f"Used in {type_counts[most_common_type]} out of {len(price_lists)} price lists")

        print(f"\nFor creating new supplier price lists, use:")
        print(f"  ListType: '{most_common_type}'")

        # Show full structure of one price list
        print("\n" + "=" * 80)
        print("FULL STRUCTURE OF A SAMPLE PRICE LIST")
        print("=" * 80)

        sample = list_type_examples[most_common_type]['full_record']
        print(f"\nSample Price List: {sample.get('ListCode')}")
        print("\nAll fields:")
        for key, value in sorted(sample.items()):
            if key not in ['SysRowID', 'SysRevID', 'RowMod'] and value is not None:
                print(f"  {key}: {value}")

        # Generate code snippet
        print("\n" + "=" * 80)
        print("CODE SNIPPET TO USE")
        print("=" * 80)

        print(f"""
Add this field to your price list creation payload:

new_price_list = {{
    "Company": self.company_id,
    "ListCode": list_code,
    "ListDescription": description,
    "ListType": "{most_common_type}",  # <-- ADD THIS LINE
    "StartDate": start_date,
    "EndDate": None,
    "Active": True,
    "CurrencyCode": "USD",
    "RowMod": "A"
}}
""")

    else:
        print("\nNO PRICE LISTS FOUND")
        print("\nThis could mean:")
        print("  1. No price lists exist in your Epicor system")
        print("  2. The filter query is incorrect")
        print("  3. Authentication or permissions issue")
else:
    print(f"\nERROR: {response.status_code}")
    print(f"Response: {response.text[:500]}")

print("\n" + "=" * 80)
print("Discovery complete!")
print("=" * 80)
