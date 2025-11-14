"""
API Endpoints Test Script
==========================

Tests the new generation profile API endpoints

Prerequisites:
- API server must be running: python vervestacks-dashboard/python-service/api_server.py
- Or use: uvicorn api_server:app --reload (from python-service directory)

Usage:
    python 2_ts_design/test_api_endpoints.py
"""

import requests
import json

BASE_URL = "http://localhost:8000"  # Adjust if your server runs on different port

def test_endpoint(endpoint, params=None):
    """Test a single endpoint"""
    url = f"{BASE_URL}{endpoint}"
    
    print(f"\n{'='*60}")
    print(f"Testing: {endpoint}")
    if params:
        print(f"Params: {params}")
    print('='*60)
    
    try:
        response = requests.get(url, params=params, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            
            if isinstance(data, list):
                # Hourly profile response
                print(f"✅ Success! Received {len(data)} data points")
                if len(data) == 8760:
                    print(f"   Min: {min(data):.2f}")
                    print(f"   Max: {max(data):.2f}")
                    print(f"   Avg: {sum(data)/len(data):.2f}")
                    print(f"   Sample (hour 0): {data[0]:.2f}")
                    print(f"   Sample (hour 4380): {data[4380]:.2f}")
                else:
                    print(f"   ⚠️  Expected 8760 hours, got {len(data)}")
                    
            elif isinstance(data, dict):
                # Cell selection or stats response
                if 'error' in data:
                    print(f"⚠️  Error in response: {data['error']}")
                else:
                    print(f"✅ Success! Received dictionary with {len(data)} keys")
                    
                    # Show sample of data
                    for i, (key, value) in enumerate(list(data.items())[:3]):
                        if isinstance(value, dict):
                            print(f"   {key}: {value}")
                        else:
                            print(f"   {key}: {value}")
            else:
                print(f"✅ Success! Response type: {type(data)}")
                
        else:
            print(f"❌ Error: HTTP {response.status_code}")
            print(f"   {response.text}")
            
    except requests.exceptions.ConnectionError:
        print(f"❌ Connection Error: Is the API server running?")
        print(f"   Start with: cd vervestacks-dashboard/python-service && uvicorn api_server:app --reload")
    except requests.exceptions.Timeout:
        print(f"⏱️  Timeout: Request took too long (>30s)")
    except Exception as e:
        print(f"❌ Error: {e}")


def main():
    print("🧪 Testing VerveStacks Generation Profile API Endpoints")
    print("="*60)
    
    iso_code = "DEU"  # Germany
    capacity_gw = 10.0
    
    # Test 1: Solar cell selection
    test_endpoint(f"/generation-profile/solar-cells/{iso_code}", 
                 params={"year": 2022, "capacity_gw": capacity_gw})
    
    # Test 2: Solar hourly profile
    test_endpoint(f"/generation-profile/solar-hourly/{iso_code}",
                 params={"year": 2022, "capacity_gw": capacity_gw})
    
    # Test 3: Wind cell selection
    test_endpoint(f"/generation-profile/wind-cells/{iso_code}",
                 params={"year": 2022, "capacity_gw": 15.0})
    
    # Test 4: Wind hourly profile
    test_endpoint(f"/generation-profile/wind-hourly/{iso_code}",
                 params={"year": 2022, "capacity_gw": 15.0})
    
    # Test 5: Cache stats
    test_endpoint("/cache/shape-cache-stats")
    
    print("\n" + "="*60)
    print("✅ All API tests complete!")
    print("="*60)


if __name__ == "__main__":
    main()

