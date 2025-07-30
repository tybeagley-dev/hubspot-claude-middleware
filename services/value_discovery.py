"""
Value Discovery Service for mapping human-readable property values to internal HubSpot values
"""

import time
from typing import Dict, List, Any, Optional
from .hubspot_client import HubSpotClient


class ValueDiscoveryService:
    def __init__(self):
        self.hubspot_client = HubSpotClient()
        self._value_cache = {}
        self._cache_expiry = {}
        self.CACHE_DURATION = 3600  # 1 hour
    
    async def discover_all_property_values(self, object_type: str = "companies") -> Dict[str, Dict[str, str]]:
        """
        Discover all property values for an object type
        
        Args:
            object_type: HubSpot object type (companies, contacts, deals, tickets)
        
        Returns:
            Dictionary mapping property_name -> {label: internal_value}
        """
        cache_key = f"{object_type}_values"
        
        # Check cache first
        if self._is_cache_valid(cache_key):
            return self._value_cache.get(cache_key, {})
        
        all_value_mappings = {}
        
        try:
            # Get owners mapping (applies to all object types)
            owners_mapping = await self._discover_owners()
            if owners_mapping:
                all_value_mappings["hubspot_owner_id"] = owners_mapping
                all_value_mappings["company_owner"] = owners_mapping  # Alternative field name
            
            # Get property-specific option values
            property_options = await self._discover_property_options(object_type)
            all_value_mappings.update(property_options)
            
            # Cache the results
            self._value_cache[cache_key] = all_value_mappings
            self._cache_expiry[cache_key] = time.time() + self.CACHE_DURATION
            
            return all_value_mappings
            
        except Exception as e:
            print(f"Warning: Could not discover property values for {object_type}: {e}")
            return {}
    
    async def _discover_owners(self) -> Dict[str, str]:
        """
        Discover HubSpot owners mapping: name -> owner_id
        
        Returns:
            Dictionary mapping owner names to owner IDs
        """
        try:
            # Fetch owners from HubSpot Owners API
            response = await self.hubspot_client._make_request("GET", "/crm/v3/owners")
            owners = response.get("results", [])
            
            owner_mapping = {}
            for owner in owners:
                owner_id = owner.get("id")
                first_name = owner.get("firstName", "")
                last_name = owner.get("lastName", "")
                email = owner.get("email", "")
                
                if owner_id:
                    # Create multiple mapping variations
                    full_name = f"{first_name} {last_name}".strip()
                    if full_name:
                        owner_mapping[full_name] = owner_id
                    
                    if first_name:
                        owner_mapping[first_name] = owner_id
                    
                    if email:
                        owner_mapping[email] = owner_id
                        # Also map email username part
                        username = email.split("@")[0]
                        owner_mapping[username] = owner_id
            
            return owner_mapping
            
        except Exception as e:
            print(f"Warning: Could not fetch owners: {e}")
            return {}
    
    async def _discover_property_options(self, object_type: str) -> Dict[str, Dict[str, str]]:
        """
        Discover property option values for properties that have predefined options
        
        Args:
            object_type: HubSpot object type
        
        Returns:
            Dictionary mapping property_name -> {option_label: option_value}
        """
        try:
            # Get all properties for this object type
            response = await self.hubspot_client._make_request("GET", f"/crm/v3/properties/{object_type}")
            properties = response.get("results", [])
            
            property_options = {}
            
            for prop in properties:
                property_name = prop.get("name")
                field_type = prop.get("type")
                options = prop.get("options", [])
                
                if not property_name or not options:
                    continue
                
                # Process properties that have predefined options
                if field_type in ["enumeration", "radio", "select", "checkbox"]:
                    option_mapping = {}
                    
                    for option in options:
                        label = option.get("label", "")
                        value = option.get("value", "")
                        
                        if label and value:
                            option_mapping[label] = value
                            # Also map lowercase and cleaned versions
                            option_mapping[label.lower()] = value
                            option_mapping[label.strip()] = value
                    
                    if option_mapping:
                        property_options[property_name] = option_mapping
            
            return property_options
            
        except Exception as e:
            print(f"Warning: Could not fetch property options: {e}")
            return {}
    
    async def get_property_value_mapping(self, object_type: str, property_name: str) -> Dict[str, str]:
        """
        Get value mapping for a specific property
        
        Args:
            object_type: HubSpot object type
            property_name: Internal property name
        
        Returns:
            Dictionary mapping human-readable labels to internal values
        """
        all_mappings = await self.discover_all_property_values(object_type)
        return all_mappings.get(property_name, {})
    
    async def map_value_to_internal(self, object_type: str, property_name: str, human_value: str) -> str:
        """
        Map a human-readable value to its internal representation
        
        Args:
            object_type: HubSpot object type
            property_name: Internal property name
            human_value: Human-readable value to map
        
        Returns:
            Internal value or original value if no mapping found
        """
        value_mapping = await self.get_property_value_mapping(object_type, property_name)
        
        # Try exact match first
        if human_value in value_mapping:
            return value_mapping[human_value]
        
        # Try case-insensitive match
        human_value_lower = human_value.lower()
        for label, internal_value in value_mapping.items():
            if label.lower() == human_value_lower:
                return internal_value
        
        # Try partial matches for names
        for label, internal_value in value_mapping.items():
            if human_value_lower in label.lower() or label.lower() in human_value_lower:
                return internal_value
        
        # Return original if no mapping found
        return human_value
    
    async def map_internal_to_human(self, object_type: str, property_name: str, internal_value: str) -> str:
        """
        Map an internal value to its human-readable representation
        
        Args:
            object_type: HubSpot object type
            property_name: Internal property name
            internal_value: Internal value to map
        
        Returns:
            Human-readable value or original value if no mapping found
        """
        value_mapping = await self.get_property_value_mapping(object_type, property_name)
        
        # Reverse lookup
        for label, internal_val in value_mapping.items():
            if internal_val == internal_value:
                return label
        
        # Return original if no mapping found
        return internal_value
    
    async def search_values_by_keyword(self, object_type: str, keyword: str) -> Dict[str, Dict[str, str]]:
        """
        Search for property values that match a keyword
        
        Args:
            object_type: HubSpot object type
            keyword: Keyword to search for
        
        Returns:
            Dictionary mapping property_name -> {matching_label: internal_value}
        """
        all_mappings = await self.discover_all_property_values(object_type)
        matching_values = {}
        
        keyword_lower = keyword.lower()
        
        for property_name, value_mapping in all_mappings.items():
            matches = {}
            for label, internal_value in value_mapping.items():
                if keyword_lower in label.lower():
                    matches[label] = internal_value
            
            if matches:
                matching_values[property_name] = matches
        
        return matching_values
    
    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if cached data is still valid"""
        if cache_key not in self._value_cache:
            return False
        
        expiry_time = self._cache_expiry.get(cache_key, 0)
        return time.time() < expiry_time
    
    async def refresh_cache(self, object_type: str = None) -> Dict[str, int]:
        """
        Force refresh of value mappings cache
        
        Args:
            object_type: Specific object type to refresh, or None for all
        
        Returns:
            Dictionary with counts of values refreshed per object type
        """
        results = {}
        
        if object_type:
            object_types = [object_type]
        else:
            object_types = ["companies", "contacts", "deals", "tickets"]
        
        for obj_type in object_types:
            cache_key = f"{obj_type}_values"
            
            # Clear cache for this object type
            if cache_key in self._value_cache:
                del self._value_cache[cache_key]
            if cache_key in self._cache_expiry:
                del self._cache_expiry[cache_key]
            
            # Fetch fresh data
            mappings = await self.discover_all_property_values(obj_type)
            
            # Count total values across all properties
            total_values = sum(len(values) for values in mappings.values())
            results[obj_type] = total_values
        
        return results