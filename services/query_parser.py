"""
Natural language query parser for converting human queries to HubSpot API filters
"""

import re
from typing import Dict, List, Any, Optional
from config.mappings import REVERSE_PROPERTY_MAPPINGS, REVERSE_VALUE_MAPPINGS

class QueryParser:
    def __init__(self):
        self.property_mappings = REVERSE_PROPERTY_MAPPINGS
        self.value_mappings = REVERSE_VALUE_MAPPINGS
        
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
    
    def parse(self, query: str) -> Dict[str, Any]:
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
        filters = self._extract_filters(query)
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
    
    def _extract_filters(self, query: str) -> List[Dict[str, Any]]:
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
                    # Map values if needed
                    mapped_values = [
                        self._map_property_value(hubspot_property, v) for v in values
                    ]
                    
                    filters.append({
                        "propertyName": hubspot_property,
                        "operator": hubspot_operator,
                        "values": mapped_values
                    })
                else:
                    # Single value operators
                    value = value.strip('"\'')
                    mapped_value = self._map_property_value(hubspot_property, value)
                    
                    filters.append({
                        "propertyName": hubspot_property,
                        "operator": hubspot_operator,
                        "value": mapped_value
                    })
        
        # Handle special cases and common phrases
        filters.extend(self._handle_special_cases(query))
        
        return filters
    
    def _handle_special_cases(self, query: str) -> List[Dict[str, Any]]:
        """Handle common query patterns and phrases"""
        filters = []
        
        # Industry-specific queries
        if "technology" in query or "tech" in query:
            filters.append({
                "propertyName": "industry",
                "operator": "CONTAINS_TOKEN",
                "value": "Technology"
            })
        
        # Size-based queries
        if "large companies" in query or "big companies" in query:
            filters.append({
                "propertyName": "numberofemployees",
                "operator": "GT",
                "value": "1000"
            })
        elif "small companies" in query:
            filters.append({
                "propertyName": "numberofemployees",
                "operator": "LT",
                "value": "100"
            })
        
        # Status-based queries
        if "active customers" in query or "active companies" in query:
            # Since there's no explicit "active" status, search for companies that are NOT inactive/cancelled
            filters.append({
                "propertyName": "account_status",
                "operator": "NOT_IN",
                "values": ["cancelled", "inactive", "Pending Cancellation"]
            })
        
        if "cancelled" in query or "canceled" in query:
            filters.append({
                "propertyName": "account_status",
                "operator": "IN", 
                "values": ["cancelled", "Pending Cancellation"]
            })
        
        # Date-based queries
        if "recent" in query or "recently created" in query:
            from datetime import datetime, timedelta
            thirty_days_ago = int((datetime.now() - timedelta(days=30)).timestamp() * 1000)
            filters.append({
                "propertyName": "createdate",
                "operator": "GTE",
                "value": str(thirty_days_ago)
            })
        
        # Revenue-based queries
        if "high revenue" in query or "enterprise" in query:
            filters.append({
                "propertyName": "annualrevenue",
                "operator": "GT",
                "value": "1000000"
            })
        
        # Owner-based queries - search by actual owner ID, not name
        if "tyler beagley" in query or "tyler's" in query:
            # For debugging: find companies with ANY owner assigned
            # This should return companies that have owners, then we can identify Tyler's ID
            filters.append({
                "propertyName": "hubspot_owner_id",
                "operator": "NOT_EQ",
                "value": ""  # Find companies that have an owner (non-empty owner ID)
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
    
    def _map_property_value(self, property_name: str, value: str) -> str:
        """Map human-readable property value to HubSpot value"""
        if property_name in self.value_mappings:
            value_lower = value.lower()
            mapping = self.value_mappings[property_name]
            return mapping.get(value_lower, value)
        
        return value