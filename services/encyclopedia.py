"""
Encyclopedia Service for comprehensive HubSpot data mapping export
"""

import json
import os
import time
from datetime import datetime
from typing import Dict, List, Any, Optional
from .property_discovery import PropertyDiscoveryService
from .value_discovery import ValueDiscoveryService
from .hubspot_client import HubSpotClient


class EncyclopediaService:
    def __init__(self):
        self.property_discovery = PropertyDiscoveryService()
        self.value_discovery = ValueDiscoveryService()
        self.hubspot_client = HubSpotClient()
        self.encyclopedia_dir = "encyclopedia"
        self._ensure_encyclopedia_dir()
    
    def _ensure_encyclopedia_dir(self):
        """Ensure encyclopedia directory exists"""
        if not os.path.exists(self.encyclopedia_dir):
            os.makedirs(self.encyclopedia_dir)
    
    async def export_full_encyclopedia(self) -> Dict[str, Any]:
        """
        Export comprehensive encyclopedia of all HubSpot data mappings
        
        Returns:
            Complete encyclopedia with all object types, properties, and values
        """
        print("Starting full encyclopedia export...")
        start_time = time.time()
        
        encyclopedia = {
            "export_info": {
                "timestamp": datetime.now().isoformat(),
                "version": "1.0",
                "exported_objects": []
            }
        }
        
        object_types = ["companies", "contacts", "deals", "tickets"]
        
        for obj_type in object_types:
            print(f"Exporting {obj_type}...")
            
            try:
                # Get property mappings (names and human-readable labels)
                property_mappings = await self.property_discovery.fetch_all_properties(obj_type)
                
                # Get value mappings (labels to internal values)
                value_mappings = await self.value_discovery.discover_all_property_values(obj_type)
                
                # Sample actual data to see what values exist in practice
                sample_data = await self._sample_object_data(obj_type)
                
                encyclopedia[obj_type] = {
                    "property_mappings": property_mappings,
                    "value_mappings": value_mappings,
                    "sample_data": sample_data,
                    "export_timestamp": datetime.now().isoformat(),
                    "total_properties": len(property_mappings),
                    "total_value_mappings": sum(len(values) for values in value_mappings.values()),
                    "sample_records": len(sample_data)
                }
                
                encyclopedia["export_info"]["exported_objects"].append({
                    "object_type": obj_type,
                    "properties_count": len(property_mappings),
                    "values_count": sum(len(values) for values in value_mappings.values()),
                    "sample_size": len(sample_data)
                })
                
                print(f"✅ {obj_type}: {len(property_mappings)} properties, {sum(len(values) for values in value_mappings.values())} values")
                
            except Exception as e:
                print(f"❌ Error exporting {obj_type}: {e}")
                encyclopedia[obj_type] = {
                    "error": str(e),
                    "export_timestamp": datetime.now().isoformat()
                }
        
        # Calculate totals
        total_time = time.time() - start_time
        encyclopedia["export_info"]["total_export_time_seconds"] = round(total_time, 2)
        encyclopedia["export_info"]["total_properties"] = sum(
            obj.get("properties_count", 0) for obj in encyclopedia["export_info"]["exported_objects"]
        )
        encyclopedia["export_info"]["total_values"] = sum(
            obj.get("values_count", 0) for obj in encyclopedia["export_info"]["exported_objects"]
        )
        
        print(f"✅ Encyclopedia export completed in {total_time:.2f} seconds")
        
        return encyclopedia
    
    async def _sample_object_data(self, object_type: str, sample_size: int = 100) -> List[Dict[str, Any]]:
        """
        Sample actual object data to understand real-world values
        
        Args:
            object_type: HubSpot object type
            sample_size: Number of records to sample
            
        Returns:
            List of sample records with their actual property values
        """
        try:
            # Use the existing list method to get sample data
            if object_type == "companies":
                # Get a sample of companies with all properties
                response = await self.hubspot_client._make_request(
                    "GET",
                    f"/crm/v3/objects/{object_type}",
                    params={
                        "limit": sample_size,
                        "properties": "name,domain,industry,hubspot_owner_id,account_status,lifecyclestage,numberofemployees,annualrevenue"
                    }
                )
            else:
                # For other object types, get basic sample
                response = await self.hubspot_client._make_request(
                    "GET", 
                    f"/crm/v3/objects/{object_type}",
                    params={"limit": sample_size}
                )
            
            return response.get("results", [])
            
        except Exception as e:
            print(f"Warning: Could not sample {object_type} data: {e}")
            return []
    
    async def save_encyclopedia_to_files(self, encyclopedia: Dict[str, Any]) -> Dict[str, str]:
        """
        Save encyclopedia to individual JSON files for each object type
        
        Args:
            encyclopedia: Complete encyclopedia data
            
        Returns:
            Dictionary mapping object_type to file_path
        """
        saved_files = {}
        
        # Save full encyclopedia
        full_path = os.path.join(self.encyclopedia_dir, "full_encyclopedia.json")
        with open(full_path, 'w') as f:
            json.dump(encyclopedia, f, indent=2)
        saved_files["full"] = full_path
        
        # Save individual object files
        for obj_type in ["companies", "contacts", "deals", "tickets"]:
            if obj_type in encyclopedia and "error" not in encyclopedia[obj_type]:
                file_path = os.path.join(self.encyclopedia_dir, f"{obj_type}.json")
                
                # Create a clean file with just the essential mappings
                clean_data = {
                    "object_type": obj_type,
                    "export_info": encyclopedia["export_info"],
                    "property_mappings": encyclopedia[obj_type]["property_mappings"],
                    "value_mappings": encyclopedia[obj_type]["value_mappings"],
                    "stats": {
                        "total_properties": encyclopedia[obj_type]["total_properties"],
                        "total_value_mappings": encyclopedia[obj_type]["total_value_mappings"],
                        "sample_records": encyclopedia[obj_type]["sample_records"]
                    }
                }
                
                with open(file_path, 'w') as f:
                    json.dump(clean_data, f, indent=2)
                
                saved_files[obj_type] = file_path
        
        return saved_files
    
    def load_encyclopedia(self, object_type: str = None) -> Dict[str, Any]:
        """
        Load encyclopedia from saved files
        
        Args:
            object_type: Specific object type to load, or None for full encyclopedia
            
        Returns:
            Encyclopedia data
        """
        if object_type:
            file_path = os.path.join(self.encyclopedia_dir, f"{object_type}.json")
            if os.path.exists(file_path):
                with open(file_path, 'r') as f:
                    return json.load(f)
            else:
                return {}
        else:
            full_path = os.path.join(self.encyclopedia_dir, "full_encyclopedia.json")
            if os.path.exists(full_path):
                with open(full_path, 'r') as f:
                    return json.load(f)
            else:
                return {}
    
    async def refresh_encyclopedia(self) -> Dict[str, Any]:
        """
        Full refresh of encyclopedia - export and save to files
        
        Returns:
            Export summary with file paths
        """
        print("Starting encyclopedia refresh...")
        
        # Export full encyclopedia
        encyclopedia = await self.export_full_encyclopedia()
        
        # Save to files
        saved_files = await self.save_encyclopedia_to_files(encyclopedia)
        
        return {
            "status": "success",
            "export_info": encyclopedia["export_info"],
            "saved_files": saved_files,
            "summary": {
                "total_objects": len(encyclopedia["export_info"]["exported_objects"]),
                "total_properties": encyclopedia["export_info"]["total_properties"],
                "total_values": encyclopedia["export_info"]["total_values"],
                "export_time": encyclopedia["export_info"]["total_export_time_seconds"]
            }
        }
    
    async def export_hierarchical_encyclopedia(self) -> Dict[str, Any]:
        """
        Export encyclopedia organized by HubSpot property groups for efficient searching
        
        Returns:
            Hierarchical encyclopedia with properties grouped by categories
        """
        print("Starting hierarchical encyclopedia export...")
        start_time = time.time()
        
        encyclopedia = {
            "export_info": {
                "timestamp": datetime.now().isoformat(),
                "version": "2.0",
                "structure": "hierarchical",
                "exported_objects": []
            }
        }
        
        object_types = ["companies", "contacts", "deals", "tickets"]
        
        for obj_type in object_types:
            print(f"Exporting hierarchical {obj_type}...")
            obj_data = await self._export_hierarchical_object(obj_type)
            encyclopedia[obj_type] = obj_data
            
            # Add summary to export info
            encyclopedia["export_info"]["exported_objects"].append({
                "object_type": obj_type,
                "groups_count": len(obj_data.get("groups", {})),
                "total_properties": sum(group.get("property_count", 0) for group in obj_data.get("groups", {}).values()),
                "export_time_seconds": obj_data.get("export_time_seconds", 0)
            })
        
        # Calculate totals
        total_time = time.time() - start_time
        encyclopedia["export_info"]["total_export_time_seconds"] = round(total_time, 2)
        encyclopedia["export_info"]["total_groups"] = sum(obj.get("groups_count", 0) for obj in encyclopedia["export_info"]["exported_objects"])
        encyclopedia["export_info"]["total_properties"] = sum(obj.get("total_properties", 0) for obj in encyclopedia["export_info"]["exported_objects"])
        
        print(f"✅ Hierarchical encyclopedia export completed in {total_time:.2f} seconds")
        return encyclopedia
    
    async def _export_hierarchical_object(self, object_type: str) -> Dict[str, Any]:
        """Export single object type with hierarchical structure"""
        start_time = time.time()
        
        # Get hierarchical property groups
        property_groups = await self.property_discovery.fetch_hierarchical_properties(object_type)
        
        # Get value mappings for enumeration properties
        value_mappings = await self.value_discovery.discover_all_property_values(object_type)
        
        # Merge value mappings into hierarchical structure
        for group_name, group_data in property_groups.items():
            for prop_name, prop_info in group_data["properties"].items():
                if prop_name in value_mappings:
                    prop_info["value_mappings"] = value_mappings[prop_name]
        
        export_time = time.time() - start_time
        
        return {
            "object_type": object_type,
            "groups": property_groups,
            "export_time_seconds": round(export_time, 2),
            "total_groups": len(property_groups),
            "total_properties": sum(group.get("property_count", 0) for group in property_groups.values())
        }
    
    def search_encyclopedia(self, search_term: str, object_type: str = None) -> Dict[str, Any]:
        """
        Search encyclopedia for properties/values matching a term
        
        Args:
            search_term: Term to search for
            object_type: Specific object type to search, or None for all
            
        Returns:
            Matching properties and values
        """
        results = {"matches": {}}
        search_lower = search_term.lower()
        
        object_types = [object_type] if object_type else ["companies", "contacts", "deals", "tickets"]
        
        for obj_type in object_types:
            encyclopedia_data = self.load_encyclopedia(obj_type)
            if not encyclopedia_data:
                continue
                
            obj_matches = {
                "property_matches": {},
                "value_matches": {}
            }
            
            # Search property mappings
            for prop_name, prop_label in encyclopedia_data.get("property_mappings", {}).items():
                if search_lower in prop_name.lower() or search_lower in prop_label.lower():
                    obj_matches["property_matches"][prop_name] = prop_label
            
            # Search value mappings
            for prop_name, values in encyclopedia_data.get("value_mappings", {}).items():
                matching_values = {}
                for label, internal_value in values.items():
                    if search_lower in label.lower():
                        matching_values[label] = internal_value
                
                if matching_values:
                    obj_matches["value_matches"][prop_name] = matching_values
            
            if obj_matches["property_matches"] or obj_matches["value_matches"]:
                results["matches"][obj_type] = obj_matches
        
        return results