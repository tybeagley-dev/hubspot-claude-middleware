from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import os
from services.hubspot_client import HubSpotClient
from services.translator import PropertyTranslator
from services.query_parser import QueryParser
from services.property_discovery import PropertyDiscoveryService
from services.value_discovery import ValueDiscoveryService

app = FastAPI(
    title="HubSpot Claude Middleware",
    description="Middleware for HubSpot integration with Claude",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
hubspot_client = HubSpotClient()
translator = PropertyTranslator()
query_parser = QueryParser()
property_discovery = PropertyDiscoveryService()
value_discovery = ValueDiscoveryService()

class CompanyQuery(BaseModel):
    query: str
    limit: Optional[int] = 100
    properties: Optional[List[str]] = None

class CompanyResponse(BaseModel):
    companies: List[Dict[str, Any]]
    total: int

@app.get("/")
async def root():
    return {"message": "HubSpot Claude Middleware is running"}

@app.get("/health")
async def health():
    return {"status": "healthy"}

@app.post("/companies/search", response_model=CompanyResponse)
async def search_companies(query: CompanyQuery):
    """Search for companies based on natural language query"""
    try:
        # Parse the natural language query
        parsed_query = await query_parser.parse(query.query)
        
        # Search companies using HubSpot API
        companies = await hubspot_client.search_companies(
            filters=parsed_query.get("filters", []),
            properties=query.properties,
            limit=query.limit
        )
        
        # Translate properties for better readability
        translated_companies = [
            translator.translate_company_properties(company) 
            for company in companies
        ]
        
        return CompanyResponse(
            companies=translated_companies,
            total=len(translated_companies)
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/companies/{company_id}")
async def get_company(company_id: str):
    """Get a specific company by ID"""
    try:
        company = await hubspot_client.get_company(company_id)
        if not company:
            raise HTTPException(status_code=404, detail="Company not found")
        
        translated_company = translator.translate_company_properties(company)
        return translated_company
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/metrics/contracts-closed")
async def contracts_closed_metrics(
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)")
):
    """Get contracts closed metrics within a date range"""
    try:
        metrics = await hubspot_client.get_contracts_closed_metrics(
            start_date=start_date,
            end_date=end_date
        )
        
        return {
            "period": {
                "start_date": start_date,
                "end_date": end_date
            },
            "metrics": metrics
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/companies")
async def list_companies(
    limit: int = Query(100, description="Number of companies to return"),
    properties: Optional[str] = Query(None, description="Comma-separated list of properties to include")
):
    """List companies with optional property filtering"""
    try:
        property_list = properties.split(",") if properties else None
        companies = await hubspot_client.list_companies(
            limit=limit,
            properties=property_list
        )
        
        translated_companies = [
            translator.translate_company_properties(company) 
            for company in companies
        ]
        
        return CompanyResponse(
            companies=translated_companies,
            total=len(translated_companies)
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/properties/discover/{object_type}")
async def discover_properties(object_type: str):
    """Discover and return all properties for a HubSpot object type"""
    try:
        valid_types = ["companies", "contacts", "deals", "tickets"]
        if object_type not in valid_types:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid object type. Must be one of: {valid_types}"
            )
        
        mappings = await property_discovery.fetch_all_properties(object_type)
        
        return {
            "object_type": object_type,
            "total_properties": len(mappings),
            "mappings": mappings,
            "sample": dict(list(mappings.items())[:10])  # Show first 10 as sample
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/properties/refresh")
async def refresh_properties(object_types: Optional[List[str]] = None):
    """Force refresh of property mappings cache"""
    try:
        if object_types:
            # Validate object types
            valid_types = ["companies", "contacts", "deals", "tickets"]
            invalid_types = [t for t in object_types if t not in valid_types]
            if invalid_types:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid object types: {invalid_types}"
                )
        
        results = {}
        if object_types:
            for obj_type in object_types:
                count_result = await property_discovery.refresh_cache(obj_type)
                results.update(count_result)
        else:
            results = await property_discovery.refresh_cache()
        
        return {
            "message": "Property mappings refreshed successfully",
            "refreshed_counts": results
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/values/discover/{object_type}")
async def discover_values(object_type: str):
    """Discover all property values (labels -> internal values) for a HubSpot object type"""
    try:
        valid_types = ["companies", "contacts", "deals", "tickets"]
        if object_type not in valid_types:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid object type. Must be one of: {valid_types}"
            )
        
        value_mappings = await value_discovery.discover_all_property_values(object_type)
        
        # Calculate total values across all properties
        total_values = sum(len(values) for values in value_mappings.values())
        
        return {
            "object_type": object_type,
            "total_properties": len(value_mappings),
            "total_values": total_values,
            "property_values": value_mappings,
            "sample_mappings": {
                prop: dict(list(values.items())[:5])  # Show first 5 values per property
                for prop, values in list(value_mappings.items())[:3]  # Show first 3 properties
            }
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/values/search/{object_type}")
async def search_values(object_type: str, keyword: str):
    """Search for property values that match a keyword"""
    try:
        valid_types = ["companies", "contacts", "deals", "tickets"]
        if object_type not in valid_types:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid object type. Must be one of: {valid_types}"
            )
        
        matching_values = await value_discovery.search_values_by_keyword(object_type, keyword)
        
        return {
            "object_type": object_type,
            "keyword": keyword,
            "matching_properties": len(matching_values),
            "matches": matching_values
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)