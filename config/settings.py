"""
Configuration settings for the HubSpot Claude Middleware
"""

import os
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

class Settings:
    # HubSpot API Configuration
    HUBSPOT_ACCESS_TOKEN: str = os.getenv("HUBSPOT_ACCESS_TOKEN", "")
    HUBSPOT_BASE_URL: str = "https://api.hubapi.com"
    
    # API Configuration
    API_TITLE: str = "HubSpot Claude Middleware"
    API_VERSION: str = "1.0.0"
    API_DESCRIPTION: str = "Middleware for HubSpot integration with Claude"
    
    # Server Configuration
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", 8000))
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    
    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = int(os.getenv("RATE_LIMIT_PER_MINUTE", 100))
    
    # Default Query Limits
    DEFAULT_COMPANY_LIMIT: int = int(os.getenv("DEFAULT_COMPANY_LIMIT", 100))
    MAX_COMPANY_LIMIT: int = int(os.getenv("MAX_COMPANY_LIMIT", 1000))
    
    # Cache Configuration
    CACHE_TTL_SECONDS: int = int(os.getenv("CACHE_TTL_SECONDS", 300))  # 5 minutes
    
    # Logging Configuration
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    # HubSpot API Endpoints
    COMPANIES_ENDPOINT: str = "/crm/v3/objects/companies"
    SEARCH_ENDPOINT: str = "/crm/v3/objects/companies/search"
    DEALS_ENDPOINT: str = "/crm/v3/objects/deals"
    
    # Default properties to fetch for companies
    DEFAULT_COMPANY_PROPERTIES: list = [
        "name",
        "domain", 
        "industry",
        "city",
        "state",
        "country",
        "numberofemployees",
        "annualrevenue",
        "createdate",
        "hs_lastmodifieddate",
        "account_status",
        "lifecyclestage",
        "hubspot_owner_id"
    ]
    
    # Properties for contracts closed metrics
    CONTRACTS_PROPERTIES: list = [
        "dealname",
        "amount",
        "closedate",
        "dealstage",
        "pipeline",
        "dealtype",
        "createdate",
        "hubspot_owner_id"
    ]
    
    @classmethod
    def validate_settings(cls) -> bool:
        """Validate that required settings are present"""
        if not cls.HUBSPOT_ACCESS_TOKEN:
            raise ValueError("HUBSPOT_ACCESS_TOKEN environment variable is required")
        return True

# Create settings instance
settings = Settings()

# Validate settings on import
settings.validate_settings()