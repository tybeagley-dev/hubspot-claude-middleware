"""
Natural language query parser for converting human queries to HubSpot API filters
"""

import re
from typing import Dict, List, Any, Optional
from config.mappings import REVERSE_PROPERTY_MAPPINGS, REVERSE_VALUE_MAPPINGS
from .value_discovery import ValueDiscoveryService

class QueryParser:
    def __init__(self):
        self.property_mappings = REVERSE_PROPERTY_MAPPINGS
        self.value_mappings = REVERSE_VALUE_MAPPINGS
        self.value_discovery = ValueDiscoveryService()
        
        # Common operators and their HubSpot equivalents
        self.operators = {
            "equals": "EQ",
            "is": "EQ", 
            "=": "EQ",
            "==": "EQ",
            "not equals": "NEQ",
            "is not": "NEQ",
            "!=": "NEQ",
            "greater than": "GT",
            ">": "GT",
            "less than": "LT",
            "<": "LT",
            "greater than or equal": "GTE",
            ">=": "GTE",
            "less than or equal": "LTE",
            "<=": "LTE",
            "contains": "CONTAINS_TOKEN",
            "includes": "CONTAINS_TOKEN",
            "has": "CONTAINS_TOKEN",
            "starts with": "STARTS_WITH",
            "ends with": "ENDS_WITH",
            "in": "IN",
            "not in": "NOT_IN"
        }
    
    async def parse(self, query: str) -> Dict[str, Any]:
        """
        Parse natural language query into HubSpot API filters
        
        Args:
            query: Natural language query string
        
        Returns:
            Dictionary with parsed filters and other query parameters
        """
        query = query.lower().strip()
        
        # Initialize result structure
        result = {
            "filters": [],
            "sort": None,
            "limit": None,
            "properties": None
        }
        
        # Extract filters from the query
        filters = await self._extract_filters(query)
        result["filters"] = filters
        
        # Extract sorting information
        sort_info = self._extract_sort(query)
        if sort_info:
            result["sort"] = sort_info
        
        # Extract limit information
        limit = self._extract_limit(query)
        if limit:
            result["limit"] = limit
        
        # Extract specific properties to return
        properties = self._extract_properties(query)
        if properties:
            result["properties"] = properties
        
        return result
    
    async def _extract_filters(self, query: str) -> List[Dict[str, Any]]:
        """Extract filter conditions from the query"""
        filters = []
        
        # Pattern for basic comparisons: "property operator value"
        comparison_patterns = [
            r'(\w+(?:\s+\w+)*)\s+(equals?|is|=|==|not equals?|is not|!=|greater than|>|less than|<|>=|<=|contains?|includes?|has|starts with|ends with)\s+([^\s,]+(?:\s+[^\s,]+)*)',
            r'(\w+(?:\s+\w+)*)\s+(in|not in)\s+\(([^)]+)\)',
            r'(\w+(?:\s+\w+)*)\s+(in|not in)\s+\[([^\]]+)\]'
        ]
        
        for pattern in comparison_patterns:
            matches = re.finditer(pattern, query, re.IGNORECASE)
            for match in matches:
                property_name = match.group(1).strip()
                operator = match.group(2).strip().lower()
                value = match.group(3).strip()
                
                # Map human-readable property to HubSpot property
                hubspot_property = self._map_property_name(property_name)
                hubspot_operator = self.operators.get(operator, "EQ")
                
                # Handle IN/NOT_IN operators with multiple values
                if operator in ["in", "not in"]:
                    values = [v.strip().strip('"\'') for v in value.split(',')]
                    # Map values using Value Discovery - literal mapping only
                    mapped_values = []
                    for v in values:
                        mapped_value = await self._map_property_value(hubspot_property, v)
                        mapped_values.append(mapped_value)
                    
                    filters.append({
                        "propertyName": hubspot_property,
                        "operator": hubspot_operator,
                        "values": mapped_values
                    })
                else:
                    # Single value operators
                    value = value.strip('"\'')
                    mapped_value = await self._map_property_value(hubspot_property, value)
                    
                    filters.append({
                        "propertyName": hubspot_property,
                        "operator": hubspot_operator,
                        "value": mapped_value
                    })
        
        # Handle special cases and common phrases
        special_filters = await self._handle_special_cases(query)
        filters.extend(special_filters)
        
        return filters
    
    async def _handle_special_cases(self, query: str) -> List[Dict[str, Any]]:
        """Handle literal label mappings using Value Discovery for ALL labels"""
        filters = []
        
        # Owner-based queries - literal name mapping
        if "tyler beagley" in query.lower() or "tyler's" in query.lower():
            tyler_id = await self.value_discovery.map_value_to_internal("companies", "hubspot_owner_id", "Tyler Beagley")
            if tyler_id != "Tyler Beagley":
                filters.append({
                    "propertyName": "hubspot_owner_id",
                    "operator": "EQ",
                    "value": tyler_id
                })
        
        # Status-based queries - literal label mapping
        if "active" in query.lower():
            active_status = await self.value_discovery.map_value_to_internal("companies", "account_status", "Active")
            if active_status != "Active":
                filters.append({
                    "propertyName": "account_status",
                    "operator": "EQ",
                    "value": active_status
                })
        
        if "cancelled" in query.lower() or "canceled" in query.lower():
            cancelled_status = await self.value_discovery.map_value_to_internal("companies", "account_status", "Cancelled")
            if cancelled_status != "Cancelled":
                filters.append({
                    "propertyName": "account_status",
                    "operator": "EQ", 
                    "value": cancelled_status
                })
        
        if "inactive" in query.lower():
            inactive_status = await self.value_discovery.map_value_to_internal("companies", "account_status", "Inactive")
            if inactive_status != "Inactive":
                filters.append({
                    "propertyName": "account_status",
                    "operator": "EQ",
                    "value": inactive_status
                })
        
        # Industry-based queries - literal label mapping
        if "technology" in query.lower() or "tech" in query.lower():
            tech_industry = await self.value_discovery.map_value_to_internal("companies", "industry", "Technology")
            if tech_industry != "Technology":
                filters.append({
                    "propertyName": "industry",
                    "operator": "EQ",
                    "value": tech_industry
                })
        
        # Company size queries - map to literal tier labels
        if "large companies" in query.lower() or "big companies" in query.lower():
            # Try to map "Large" as a literal customer tier or company size label
            large_tier = await self.value_discovery.map_value_to_internal("companies", "customer_tier", "Large")
            if large_tier != "Large":
                filters.append({
                    "propertyName": "customer_tier",
                    "operator": "EQ",
                    "value": large_tier
                })
            else:
                # Fallback to employee count if no tier mapping
                filters.append({
                    "propertyName": "numberofemployees",
                    "operator": "GT",
                    "value": "1000"
                })
        
        if "small companies" in query.lower():
            small_tier = await self.value_discovery.map_value_to_internal("companies", "customer_tier", "Small")
            if small_tier != "Small":
                filters.append({
                    "propertyName": "customer_tier",
                    "operator": "EQ",
                    "value": small_tier
                })
            else:
                # Fallback to employee count if no tier mapping
                filters.append({
                    "propertyName": "numberofemployees",
                    "operator": "LT",
                    "value": "100"
                })
        
        # Enterprise/tier queries - literal label mapping
        if "enterprise" in query.lower():
            enterprise_tier = await self.value_discovery.map_value_to_internal("companies", "customer_tier", "Enterprise")
            if enterprise_tier != "Enterprise":
                filters.append({
                    "propertyName": "customer_tier",
                    "operator": "EQ",
                    "value": enterprise_tier
                })
        
        # Revenue-based queries - try tier mapping first, then fallback to amount
        if "high revenue" in query.lower():
            high_revenue_tier = await self.value_discovery.map_value_to_internal("companies", "customer_tier", "High Revenue")
            if high_revenue_tier != "High Revenue":
                filters.append({
                    "propertyName": "customer_tier",
                    "operator": "EQ",
                    "value": high_revenue_tier
                })
            else:
                # Fallback to revenue amount if no tier mapping
                filters.append({
                    "propertyName": "annualrevenue",
                    "operator": "GT",
                    "value": "1000000"
                })
        
        # Date-based queries - for "recent" we keep the logic since it's not a label
        if "recent" in query.lower() or "recently created" in query.lower():
            from datetime import datetime, timedelta
            thirty_days_ago = int((datetime.now() - timedelta(days=30)).timestamp() * 1000)
            filters.append({
                "propertyName": "createdate",
                "operator": "GTE",
                "value": str(thirty_days_ago)
            })
        
        return filters
    
    def _extract_sort(self, query: str) -> Optional[Dict[str, str]]:
        """Extract sorting information from query"""
        sort_patterns = [
            r'sort by (\w+(?:\s+\w+)*)\s*(asc|desc|ascending|descending)?',
            r'order by (\w+(?:\s+\w+)*)\s*(asc|desc|ascending|descending)?'
        ]
        
        for pattern in sort_patterns:
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                property_name = match.group(1).strip()
                direction = match.group(2)
                
                hubspot_property = self._map_property_name(property_name)
                
                if direction and direction.lower() in ['desc', 'descending']:
                    direction = 'DESCENDING'
                else:
                    direction = 'ASCENDING'
                
                return {
                    "propertyName": hubspot_property,
                    "direction": direction
                }
        
        return None
    
    def _extract_limit(self, query: str) -> Optional[int]:
        """Extract limit/count information from query"""
        limit_patterns = [
            r'limit (\d+)',
            r'top (\d+)',
            r'first (\d+)',
            r'show (\d+)',
            r'(\d+) results?'
        ]
        
        for pattern in limit_patterns:
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                return int(match.group(1))
        
        return None
    
    def _extract_properties(self, query: str) -> Optional[List[str]]:
        """Extract specific properties to return from query"""
        properties_patterns = [
            r'show (?:me )?(?:only )?([^,]+(?:,\s*[^,]+)*)',
            r'return ([^,]+(?:,\s*[^,]+)*)',
            r'include ([^,]+(?:,\s*[^,]+)*)'
        ]
        
        for pattern in properties_patterns:
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                properties_str = match.group(1)
                properties = [p.strip() for p in properties_str.split(',')]
                
                # Map to HubSpot property names
                hubspot_properties = [
                    self._map_property_name(prop) for prop in properties
                ]
                
                return hubspot_properties
        
        return None
    
    def _map_property_name(self, readable_name: str) -> str:
        """Map human-readable property name to HubSpot property name"""
        # Clean up the property name
        cleaned_name = readable_name.lower().strip()
        
        # Direct mapping
        if cleaned_name in self.property_mappings:
            return self.property_mappings[cleaned_name]
        
        # Try common variations
        variations = [
            cleaned_name.replace(' ', '_'),
            cleaned_name.replace(' ', ''),
            cleaned_name.replace('_', ' ')
        ]
        
        for variation in variations:
            if variation in self.property_mappings:
                return self.property_mappings[variation]
        
        # Return as-is with underscores if no mapping found
        return cleaned_name.replace(' ', '_')
    
    async def _map_property_value(self, property_name: str, value: str) -> str:
        """Map human-readable property value to HubSpot value using Value Discovery"""
        # First try static mappings for backward compatibility
        if property_name in self.value_mappings:
            value_lower = value.lower()
            mapping = self.value_mappings[property_name]
            static_result = mapping.get(value_lower, value)
            if static_result != value:
                return static_result
        
        # Use Value Discovery for dynamic mapping
        try:
            dynamic_result = await self.value_discovery.map_value_to_internal("companies", property_name, value)
            return dynamic_result
        except Exception as e:
            print(f"Warning: Could not map value '{value}' for property '{property_name}': {e}")
            return value