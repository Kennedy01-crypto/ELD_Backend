#!/usr/bin/env python3
"""
Comprehensive API Test Script for ELD Backend
Tests all endpoints and functionality
"""
import requests
import json
import time
from datetime import datetime, timedelta

API_BASE = "http://127.0.0.1:8000/api"

def test_endpoint(method, url, data=None, expected_status=200):
    """Test an API endpoint"""
    try:
        if method == "GET":
            response = requests.get(url)
        elif method == "POST":
            response = requests.post(url, json=data)
        elif method == "PUT":
            response = requests.put(url, json=data)
        elif method == "DELETE":
            response = requests.delete(url)
        
        print(f"✅ {method} {url} - Status: {response.status_code}")
        if response.status_code != expected_status:
            print(f"   ⚠️  Expected {expected_status}, got {response.status_code}")
        
        try:
            return response.json()
        except:
            return response.text
    except Exception as e:
        print(f"❌ {method} {url} - Error: {e}")
        return None

def main():
    print("🚛 ELD Backend API Test Suite")
    print("=" * 50)
    
    # Test 1: API Root
    print("\n1. Testing API Root...")
    test_endpoint("GET", f"{API_BASE}/")
    
    # Test 2: Get CSRF Token
    print("\n2. Testing CSRF Token...")
    csrf_data = test_endpoint("GET", f"{API_BASE}/csrf-token/")
    
    # Test 3: Get Drivers
    print("\n3. Testing Drivers Endpoint...")
    drivers = test_endpoint("GET", f"{API_BASE}/drivers/")
    
    # Test 4: Create Driver
    print("\n4. Testing Create Driver...")
    driver_data = {
        "name": "Test Driver",
        "license_number": "TEST123456",
        "license_state": "VA"
    }
    new_driver = test_endpoint("POST", f"{API_BASE}/drivers/", driver_data, 201)
    
    if new_driver and 'id' in new_driver:
        driver_id = new_driver['id']
        print(f"   Created driver with ID: {driver_id}")
        
        # Test 5: Get HOS Status
        print("\n5. Testing HOS Status...")
        hos_status = test_endpoint("GET", f"{API_BASE}/drivers/{driver_id}/hos_status/")
        
        # Test 6: Update Duty Status
        print("\n6. Testing Duty Status Update...")
        duty_data = {
            "status": "driving",
            "location": "Richmond, VA",
            "remarks": "Starting shift"
        }
        test_endpoint("POST", f"{API_BASE}/drivers/{driver_id}/update_duty_status/", duty_data)
        
        # Test 7: Create Trip
        print("\n7. Testing Create Trip...")
        trip_data = {
            "driver_id": driver_id,
            "origin_address": "Richmond, VA",
            "destination_address": "Newark, NJ",
            "planned_start_time": (datetime.now() + timedelta(hours=1)).isoformat()
        }
        new_trip = test_endpoint("POST", f"{API_BASE}/trips/create_trip/", trip_data, 201)
        
        if new_trip and 'id' in new_trip:
            trip_id = new_trip['id']
            print(f"   Created trip with ID: {trip_id}")
    
    # Test 8: Geocoding
    print("\n8. Testing Geocoding...")
    geocode_data = {"address": "1600 Amphitheatre Parkway, Mountain View, CA"}
    geocode_result = test_endpoint("POST", f"{API_BASE}/geocode/", geocode_data)
    
    # Test 9: Reverse Geocoding
    print("\n9. Testing Reverse Geocoding...")
    reverse_data = {"latitude": 37.4221, "longitude": -122.0841}
    reverse_result = test_endpoint("POST", f"{API_BASE}/geocode/reverse/", reverse_data)
    
    # Test 10: Route Calculation
    print("\n10. Testing Route Calculation...")
    route_data = {
        "origin": "Richmond, VA",
        "destination": "Newark, NJ"
    }
    route_result = test_endpoint("POST", f"{API_BASE}/route-calculation/", route_data)
    
    # Test 11: Map Tile
    print("\n11. Testing Map Tile...")
    test_endpoint("GET", f"{API_BASE}/map-tile/?lat=37.7749&lng=-122.4194&zoom=10")
    
    # Test 12: Daily Logs
    print("\n12. Testing Daily Logs...")
    logs = test_endpoint("GET", f"{API_BASE}/daily-logs/")
    
    # Test 13: Generate PDF
    print("\n13. Testing PDF Generation...")
    if new_driver and 'id' in new_driver:
        pdf_data = {
            "driver_id": new_driver['id'],
            "date": datetime.now().strftime("%Y-%m-%d")
        }
        test_endpoint("POST", f"{API_BASE}/daily-logs/generate_pdf/", pdf_data)
    
    # Test 14: Get Trips
    print("\n14. Testing Get Trips...")
    trips = test_endpoint("GET", f"{API_BASE}/trips/")
    
    # Test 15: Get Violations
    print("\n15. Testing Get Violations...")
    violations = test_endpoint("GET", f"{API_BASE}/violations/")
    
    print("\n" + "=" * 50)
    print("🎉 API Test Suite Completed!")
    print("\n📋 Available UIs:")
    print("   • Admin Test UI: http://127.0.0.1:8000/api/test-ui/")
    print("   • Driver UI: http://127.0.0.1:8000/api/driver-ui/")
    print("   • Admin Login: http://127.0.0.1:8000/api/admin-login/")
    print("   • Django Admin: http://127.0.0.1:8000/admin/")
    print("\n🔑 Test Credentials:")
    print("   • Username: admin")
    print("   • Password: admin123")

if __name__ == "__main__":
    main()
