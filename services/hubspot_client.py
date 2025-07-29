"""
HubSpot API client for interacting with HubSpot CRM
"""

import httpx
import json
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from config.settings import settings

class HubSpotClient:
    def __init__(self):
        self.access_token = settings.HUBSPOT_ACCESS_TOKEN
        self.base_url = settings.HUBSPOT_BASE_URL
        self.headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
    
    async def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make an HTTP request to HubSpot API"""
        url = f"{self.base_url}{endpoint}"
        
        async with httpx.AsyncClient() as client:
            response = await client.request(
                method=method,
                url=url,
                headers=self.headers,
                timeout=30.0,
                **kwargs
            )
            
            if response.status_code == 401:
                raise Exception("Invalid HubSpot access token")
            elif response.status_code == 429:
                raise Exception("Rate limit exceeded")
            elif response.status_code >= 400:
                raise Exception(f"HubSpot API error: {response.status_code} - {response.text}")
            
            return response.json()
    
    async def search_companies(
        self, 
        filters: List[Dict[str, Any]] = None,
        properties: List[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Search for companies using HubSpot search API"""
        if properties is None:
            properties = settings.DEFAULT_COMPANY_PROPERTIES
        
        search_request = {
            "filterGroups": [{"filters": filters or []}],
            "properties": properties,
            "limit": min(limit, settings.MAX_COMPANY_LIMIT)
        }
        
        response = await self._make_request(
            "POST", 
            settings.SEARCH_ENDPOINT,
            json=search_request
        )
        
        return response.get("results", [])
    
    async def get_company(self, company_id: str, properties: List[str] = None) -> Optional[Dict[str, Any]]:
        """Get a specific company by ID"""
        if properties is None:
            properties = settings.DEFAULT_COMPANY_PROPERTIES
        
        params = {"properties": ",".join(properties)}
        
        try:
            response = await self._make_request(
                "GET",
                f"{settings.COMPANIES_ENDPOINT}/{company_id}",
                params=params
            )
            return response
        except Exception as e:
            if "404" in str(e):
                return None
            raise e
    
    async def list_companies(
        self,
        limit: int = 100,
        properties: List[str] = None,
        after: str = None
    ) -> List[Dict[str, Any]]:
        """List companies with pagination"""
        if properties is None:
            properties = settings.DEFAULT_COMPANY_PROPERTIES
        
        params = {
            "properties": ",".join(properties),
            "limit": min(limit, settings.MAX_COMPANY_LIMIT)
        }
        
        if after:
            params["after"] = after
        
        response = await self._make_request(
            "GET",
            settings.COMPANIES_ENDPOINT,
            params=params
        )
        
        return response.get("results", [])
    
    async def get_contracts_closed_metrics(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get contracts closed metrics within a date range"""
        
        # Default to last 30 days if no dates provided
        if not end_date:
            end_date = datetime.now().strftime("%Y-%m-%d")
        if not start_date:
            start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        
        # Convert dates to milliseconds for HubSpot API
        start_timestamp = int(datetime.strptime(start_date, "%Y-%m-%d").timestamp() * 1000)
        end_timestamp = int(datetime.strptime(end_date, "%Y-%m-%d").timestamp() * 1000)
        
        # Search for closed deals in the date range
        search_request = {
            "filterGroups": [
                {
                    "filters": [
                        {
                            "propertyName": "closedate",
                            "operator": "GTE",
                            "value": start_timestamp
                        },
                        {
                            "propertyName": "closedate",
                            "operator": "LTE", 
                            "value": end_timestamp
                        },
                        {
                            "propertyName": "dealstage",
                            "operator": "IN",
                            "values": ["closedwon", "closed-won", "closed_won"]
                        }
                    ]
                }
            ],
            "properties": settings.CONTRACTS_PROPERTIES,
            "limit": 200
        }
        
        response = await self._make_request(
            "POST",
            "/crm/v3/objects/deals/search",
            json=search_request
        )
        
        deals = response.get("results", [])
        
        # Calculate metrics
        total_deals = len(deals)
        total_value = sum(
            float(deal.get("properties", {}).get("amount", 0) or 0) 
            for deal in deals
        )
        
        # Group by month
        monthly_metrics = {}
        for deal in deals:
            close_date = deal.get("properties", {}).get("closedate")
            if close_date:
                # HubSpot timestamps are in milliseconds
                date_obj = datetime.fromtimestamp(int(close_date) / 1000)
                month_key = date_obj.strftime("%Y-%m")
                
                if month_key not in monthly_metrics:
                    monthly_metrics[month_key] = {
                        "count": 0,
                        "total_value": 0,
                        "deals": []
                    }
                
                deal_value = float(deal.get("properties", {}).get("amount", 0) or 0)
                monthly_metrics[month_key]["count"] += 1
                monthly_metrics[month_key]["total_value"] += deal_value
                monthly_metrics[month_key]["deals"].append({
                    "name": deal.get("properties", {}).get("dealname", ""),
                    "value": deal_value,
                    "close_date": close_date,
                    "owner_id": deal.get("properties", {}).get("hubspot_owner_id", "")
                })
        
        return {
            "summary": {
                "total_contracts": total_deals,
                "total_value": total_value,
                "average_deal_size": total_value / max(total_deals, 1)
            },
            "monthly_breakdown": monthly_metrics,
            "date_range": {
                "start": start_date,
                "end": end_date
            }
        }