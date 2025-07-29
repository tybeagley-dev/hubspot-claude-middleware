"""
Property translator for converting between HubSpot property names/values and human-readable formats
"""

from typing import Dict, Any, Optional
from config.mappings import PROPERTY_MAPPINGS, VALUE_MAPPINGS, REVERSE_PROPERTY_MAPPINGS, REVERSE_VALUE_MAPPINGS

class PropertyTranslator:
    def __init__(self):
        self.property_mappings = PROPERTY_MAPPINGS
        self.value_mappings = VALUE_MAPPINGS
        self.reverse_property_mappings = REVERSE_PROPERTY_MAPPINGS
        self.reverse_value_mappings = REVERSE_VALUE_MAPPINGS
    
    def translate_property_name(self, property_name: str, reverse: bool = False) -> str:
        """
        Translate property name to/from human-readable format
        
        Args:
            property_name: The property name to translate
            reverse: If True, translate from human-readable to HubSpot format
        
        Returns:
            Translated property name or original if no mapping exists
        """
        if reverse:
            return self.reverse_property_mappings.get(property_name, property_name)
        else:
            return self.property_mappings.get(property_name, property_name)
    
    def translate_property_value(
        self, 
        property_name: str, 
        value: Any, 
        reverse: bool = False
    ) -> Any:
        """
        Translate property value to/from human-readable format
        
        Args:
            property_name: The property name (used to determine mapping)
            value: The value to translate
            reverse: If True, translate from human-readable to HubSpot format
        
        Returns:
            Translated value or original if no mapping exists
        """
        if value is None:
            return value
        
        value_str = str(value).lower()
        
        if reverse:
            mapping = self.reverse_value_mappings.get(property_name, {})
        else:
            mapping = self.value_mappings.get(property_name, {})
        
        return mapping.get(value_str, value)
    
    def translate_company_properties(self, company: Dict[str, Any]) -> Dict[str, Any]:
        """
        Translate all properties in a company object to human-readable format
        
        Args:
            company: Company object from HubSpot API
        
        Returns:
            Company object with translated property names and values
        """
        if not company or "properties" not in company:
            return company
        
        translated_company = {
            "id": company.get("id"),
            "created_at": company.get("createdAt"),
            "updated_at": company.get("updatedAt"),
            "archived": company.get("archived", False),
            "properties": {}
        }
        
        original_properties = company.get("properties", {})
        
        for property_name, value in original_properties.items():
            # Translate property name
            readable_name = self.translate_property_name(property_name)
            
            # Translate property value if mapping exists
            readable_value = self.translate_property_value(property_name, value)
            
            # Format dates for better readability
            if readable_value and ("date" in property_name.lower() or "createdate" in property_name.lower()):
                readable_value = self._format_date(readable_value)
            
            # Format numbers for better readability
            if readable_value and property_name in ["annualrevenue", "numberofemployees"]:
                readable_value = self._format_number(readable_value)
            
            translated_company["properties"][readable_name] = readable_value
        
        return translated_company
    
    def translate_query_filters(self, filters: list) -> list:
        """
        Translate filters from human-readable format to HubSpot API format
        
        Args:
            filters: List of filter objects with human-readable property names
        
        Returns:
            List of filters with HubSpot property names
        """
        translated_filters = []
        
        for filter_obj in filters:
            translated_filter = filter_obj.copy()
            
            # Translate property name
            if "propertyName" in translated_filter:
                property_name = translated_filter["propertyName"]
                translated_filter["propertyName"] = self.translate_property_name(
                    property_name, reverse=True
                )
            
            # Translate filter values
            if "value" in translated_filter:
                original_property = translated_filter["propertyName"]
                translated_filter["value"] = self.translate_property_value(
                    original_property, 
                    translated_filter["value"], 
                    reverse=True
                )
            
            if "values" in translated_filter:
                original_property = translated_filter["propertyName"]
                translated_filter["values"] = [
                    self.translate_property_value(original_property, val, reverse=True)
                    for val in translated_filter["values"]
                ]
            
            translated_filters.append(translated_filter)
        
        return translated_filters
    
    def _format_date(self, date_value: str) -> str:
        """Format date string for better readability"""
        try:
            # HubSpot dates are typically in milliseconds timestamp format
            if date_value.isdigit():
                from datetime import datetime
                timestamp = int(date_value) / 1000
                dt = datetime.fromtimestamp(timestamp)
                return dt.strftime("%Y-%m-%d %H:%M:%S")
            return date_value
        except (ValueError, TypeError):
            return date_value
    
    def _format_number(self, number_value: str) -> str:
        """Format number for better readability"""
        try:
            num = float(number_value)
            if num >= 1000000:
                return f"{num/1000000:.1f}M"
            elif num >= 1000:
                return f"{num/1000:.1f}K"
            else:
                return f"{int(num):,}"
        except (ValueError, TypeError):
            return str(number_value)
    
    def get_hubspot_property_name(self, readable_name: str) -> str:
        """Get HubSpot property name from readable name"""
        return self.reverse_property_mappings.get(readable_name, readable_name.lower().replace(" ", "_"))
    
    def get_available_properties(self) -> Dict[str, str]:
        """Get all available property mappings"""
        return self.property_mappings.copy()
    
    def get_available_values(self, property_name: str) -> Dict[str, str]:
        """Get available value mappings for a specific property"""
        return self.value_mappings.get(property_name, {}).copy()