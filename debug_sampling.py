#!/usr/bin/env python3
"""
Debug script to test HubSpot sampling and identify why ChurnGuard properties aren't being captured
"""

import asyncio
import os
from services.hubspot_client import HubSpotClient
from services.encyclopedia import EncyclopediaService

async def test_sampling():
    print("🔍 Testing HubSpot sampling...")
    
    hubspot_client = HubSpotClient()
    
    # Test 1: Basic company fetch (no specific properties)
    print("\n1. Testing basic company fetch...")
    try:
        response = await hubspot_client._make_request(
            "GET",
            "/crm/v3/objects/companies",
            params={"limit": 5}
        )
        companies = response.get("results", [])
        print(f"✅ Basic fetch: {len(companies)} companies")
        if companies:
            print(f"   Sample company ID: {companies[0].get('id')}")
    except Exception as e:
        print(f"❌ Basic fetch failed: {e}")
        return
    
    # Test 2: Fetch with standard properties
    print("\n2. Testing with standard properties...")
    try:
        response = await hubspot_client._make_request(
            "GET",
            "/crm/v3/objects/companies",
            params={
                "limit": 5,
                "properties": "name,domain,industry"
            }
        )
        companies = response.get("results", [])
        print(f"✅ Standard properties: {len(companies)} companies")
        if companies:
            props = companies[0].get("properties", {})
            print(f"   Sample properties: {list(props.keys())}")
    except Exception as e:
        print(f"❌ Standard properties failed: {e}")
    
    # Test 3: Check if ChurnGuard properties exist
    print("\n3. Testing ChurnGuard property existence...")
    churnguard_props = [
        "churnguard_current_risk_level",
        "churnguard_trending_risk_level", 
        "churnguard_current_risk_reasons",
        "churnguard_trending_risk_reasons",
        "churnguard_last_updated"
    ]
    
    for prop in churnguard_props:
        try:
            response = await hubspot_client._make_request(
                "GET",
                f"/crm/v3/properties/companies/{prop}"
            )
            print(f"✅ {prop}: exists")
            prop_type = response.get("type", "unknown")
            print(f"   Type: {prop_type}")
            if response.get("options"):
                options = [opt.get("value") for opt in response.get("options", [])]
                print(f"   Options: {options}")
        except Exception as e:
            print(f"❌ {prop}: {e}")
    
    # Test 4: Fetch with ChurnGuard properties
    print("\n4. Testing with ChurnGuard properties...")
    try:
        response = await hubspot_client._make_request(
            "GET",
            "/crm/v3/objects/companies",
            params={
                "limit": 10,
                "properties": "name,churnguard_current_risk_level,churnguard_trending_risk_level"
            }
        )
        companies = response.get("results", [])
        print(f"✅ ChurnGuard properties: {len(companies)} companies")
        
        # Check how many have ChurnGuard data
        companies_with_risk = 0
        for company in companies:
            props = company.get("properties", {})
            if props.get("churnguard_current_risk_level") or props.get("churnguard_trending_risk_level"):
                companies_with_risk += 1
                print(f"   Company {props.get('name', 'Unknown')}: current={props.get('churnguard_current_risk_level')}, trending={props.get('churnguard_trending_risk_level')}")
        
        print(f"   Companies with ChurnGuard data: {companies_with_risk}/{len(companies)}")
        
    except Exception as e:
        print(f"❌ ChurnGuard properties failed: {e}")
    
    # Test 5: Search for companies with ChurnGuard data specifically
    print("\n5. Searching for companies with ChurnGuard data...")
    try:
        search_request = {
            "filterGroups": [{
                "filters": [{
                    "propertyName": "churnguard_current_risk_level",
                    "operator": "HAS_PROPERTY"
                }]
            }],
            "limit": 10,
            "properties": ["name", "churnguard_current_risk_level", "churnguard_trending_risk_level"]
        }
        
        response = await hubspot_client._make_request(
            "POST",
            "/crm/v3/objects/companies/search",
            json=search_request
        )
        
        companies = response.get("results", [])
        print(f"✅ Found {len(companies)} companies with ChurnGuard risk data")
        
        for company in companies[:3]:
            props = company.get("properties", {})
            print(f"   {props.get('name', 'Unknown')}: {props.get('churnguard_current_risk_level')} / {props.get('churnguard_trending_risk_level')}")
            
    except Exception as e:
        print(f"❌ ChurnGuard search failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_sampling())