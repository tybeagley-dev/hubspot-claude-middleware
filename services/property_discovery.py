"""
Property Discovery Service for dynamically fetching and mapping HubSpot properties
"""

import time
from typing import Dict, List, Any, Optional
from .hubspot_client import HubSpotClient


class PropertyDiscoveryService:
    def __init__(self):
        self.hubspot_client = HubSpotClient()
        self._cache = {}
        self._cache_expiry = {}
        self.CACHE_DURATION = 3600  # 1 hour
    
    async def fetch_all_properties(self, object_type: str = "companies") -> Dict[str, str]:
        """
        Fetch all properties from HubSpot Properties API and generate human-readable mappings
        
        Args:
            object_type: HubSpot object type (companies, contacts, deals, tickets)
        
        Returns:
            Dictionary mapping internal_name -> human_readable_name
        """
        # Check cache first
        if self._is_cache_valid(object_type):
            return self._cache.get(object_type, {})
        
        # Fetch fresh from HubSpot
        try:
            endpoint = f"/crm/v3/properties/{object_type}"
            response = await self.hubspot_client._make_request("GET", endpoint)
            
            properties = response.get("results", [])
            mappings = self._process_properties(properties)
            
            # Cache the results
            self._cache[object_type] = mappings
            self._cache_expiry[object_type] = time.time() + self.CACHE_DURATION
            
            return mappings
            
        except Exception as e:
            # Fallback to empty dict if API fails
            print(f"Warning: Could not fetch properties for {object_type}: {e}")
            return {}
    
    async def fetch_hierarchical_properties(self, object_type: str = "companies") -> Dict[str, Dict[str, Any]]:
        """
        Fetch properties organized by property groups for hierarchical encyclopedia
        
        Args:
            object_type: HubSpot object type (companies, contacts, deals, tickets)
        
        Returns:
            Dictionary mapping group_name -> {properties: {}, metadata: {}}
        """
        try:
            endpoint = f"/crm/v3/properties/{object_type}"
            response = await self.hubspot_client._make_request("GET", endpoint)
            
            properties = response.get("results", [])
            return self._organize_by_groups(properties)
            
        except Exception as e:
            print(f"Warning: Could not fetch hierarchical properties for {object_type}: {e}")
            return {}
    
    def _organize_by_groups(self, raw_properties: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """
        Organize properties by their HubSpot property groups
        
        Args:
            raw_properties: Raw property definitions from HubSpot API
            
        Returns:
            Dictionary organized by property groups
        """
        groups = {}
        
        for prop in raw_properties:
            internal_name = prop.get("name", "")
            if not internal_name:
                continue
            
            # Get property group (HubSpot API includes groupName)
            group_name = prop.get("groupName", "other")
            
            # Normalize group name for consistency
            normalized_group = self._normalize_group_name(group_name)
            
            # Initialize group if not exists
            if normalized_group not in groups:
                groups[normalized_group] = {
                    "display_name": self._humanize_group_name(group_name),
                    "properties": {},
                    "property_count": 0,
                    "original_group_name": group_name
                }
            
            # Add property to group
            readable_name = self._make_readable_name(prop)
            groups[normalized_group]["properties"][internal_name] = {
                "label": readable_name,
                "type": prop.get("type", "string"),
                "description": prop.get("description", ""),
                "options": prop.get("options", []) if prop.get("type") == "enumeration" else []
            }
            groups[normalized_group]["property_count"] += 1
        
        return groups
    
    def _normalize_group_name(self, group_name: str) -> str:
        """Normalize group name for consistent keys"""
        if not group_name:
            return "other"
        
        return group_name.lower().replace(" ", "_").replace("-", "_")
    
    def _humanize_group_name(self, group_name: str) -> str:
        """Convert group name to human-readable format"""
        if not group_name:
            return "Other Properties"
        
        # Handle common group name patterns
        group_map = {
            "companyinformation": "Company Information",
            "company_information": "Company Information", 
            "billing_information": "Billing Information",
            "customer_success": "Customer Success",
            "web_analytics": "Web Analytics",
            "social_media": "Social Media",
            "conversion_information": "Conversion Information"
        }
        
        normalized = group_name.lower().replace(" ", "_").replace("-", "_")
        
        if normalized in group_map:
            return group_map[normalized]
        
        # Fallback: title case with spaces
        return group_name.replace("_", " ").replace("-", " ").title()
    
    def _process_properties(self, raw_properties: List[Dict[str, Any]]) -> Dict[str, str]:
        """
        Convert raw HubSpot property definitions to human-readable mappings
        
        Args:
            raw_properties: Raw property definitions from HubSpot API
        
        Returns:
            Dictionary mapping internal_name -> human_readable_name
        """
        mappings = {}
        
        for prop in raw_properties:
            internal_name = prop.get("name", "")
            if not internal_name:
                continue
            
            # Try to get a good human-readable name
            readable_name = self._make_readable_name(prop)
            mappings[internal_name] = readable_name
        
        return mappings
    
    def _make_readable_name(self, property_def: Dict[str, Any]) -> str:
        """
        Generate human-readable name from property definition
        
        Priority:
        1. Clean property label (if exists and readable)
        2. Humanized internal name
        3. Raw internal name as fallback
        """
        internal_name = property_def.get("name", "")
        label = property_def.get("label", "")
        
        # Try to use label if it's clean and readable
        if label and self._is_clean_label(label):
            return self._clean_label(label)
        
        # Fallback to humanized internal name
        return self._humanize_internal_name(internal_name)
    
    def _is_clean_label(self, label: str) -> bool:
        """Check if label is already human-readable"""
        if not label:
            return False
        
        # Skip labels that look like internal names
        problematic_patterns = [
            "_", "camelCase", "ALLCAPS", "snake_case"
        ]
        
        # Simple heuristics for clean labels
        has_spaces = " " in label
        not_all_lowercase = not label.islower()
        not_snake_case = "_" not in label
        reasonable_length = 3 <= len(label) <= 50
        
        return has_spaces and not_all_lowercase and not_snake_case and reasonable_length
    
    def _clean_label(self, label: str) -> str:
        """Clean up a mostly-good label"""
        # Basic cleanup
        cleaned = label.strip()
        
        # Ensure proper title case
        if not any(c.isupper() for c in cleaned[1:]):  # If not already title case
            cleaned = cleaned.title()
        
        return cleaned
    
    def _humanize_internal_name(self, internal_name: str) -> str:
        """Convert internal_name to human-readable format"""
        if not internal_name:
            return ""
        
        # Handle common HubSpot prefixes
        name = internal_name
        if name.startswith("hs_"):
            name = name[3:]  # Remove "hs_" prefix
        
        # Convert snake_case to Title Case
        if "_" in name:
            words = name.split("_")
            return " ".join(word.capitalize() for word in words if word)
        
        # Convert camelCase to Title Case
        if any(c.isupper() for c in name[1:]):
            # Simple camelCase splitting
            result = []
            current_word = []
            
            for char in name:
                if char.isupper() and current_word:
                    result.append("".join(current_word))
                    current_word = [char.lower()]
                else:
                    current_word.append(char.lower())
            
            if current_word:
                result.append("".join(current_word))
            
            return " ".join(word.capitalize() for word in result)
        
        # Fallback: just capitalize
        return name.replace("-", " ").title()
    
    def _is_cache_valid(self, object_type: str) -> bool:
        """Check if cached data is still valid"""
        if object_type not in self._cache:
            return False
        
        expiry_time = self._cache_expiry.get(object_type, 0)
        return time.time() < expiry_time
    
    async def get_property_info(self, object_type: str, property_name: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a specific property
        
        Args:
            object_type: HubSpot object type
            property_name: Internal property name
        
        Returns:
            Property details or None if not found
        """
        try:
            endpoint = f"/crm/v3/properties/{object_type}/{property_name}"
            response = await self.hubspot_client._make_request("GET", endpoint)
            return response
        except Exception:
            return None
    
    async def refresh_cache(self, object_type: str = None) -> Dict[str, int]:
        """
        Force refresh of property cache
        
        Args:
            object_type: Specific object type to refresh, or None for all
        
        Returns:
            Dictionary with counts of properties refreshed per object type
        """
        results = {}
        
        if object_type:
            object_types = [object_type]
        else:
            object_types = ["companies", "contacts", "deals", "tickets"]
        
        for obj_type in object_types:
            # Clear cache for this object type
            if obj_type in self._cache:
                del self._cache[obj_type]
            if obj_type in self._cache_expiry:
                del self._cache_expiry[obj_type]
            
            # Fetch fresh data
            mappings = await self.fetch_all_properties(obj_type)
            results[obj_type] = len(mappings)
        
        return results