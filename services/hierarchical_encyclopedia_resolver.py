"""
Hierarchical Encyclopedia Resolver for efficient, group-based property searching
Uses HubSpot property groups to dramatically reduce search scope and token usage
"""

import re
from typing import Dict, List, Any, Optional, Tuple
from .encyclopedia import EncyclopediaService
from .hubspot_client import HubSpotClient


class HierarchicalEncyclopediaResolver:
    def __init__(self):
        self.encyclopedia = EncyclopediaService()
        self.hubspot_client = HubSpotClient()
        self._hierarchical_cache = {}
        self._group_keywords = {}
        self._load_hierarchical_cache()
    
    def _load_hierarchical_cache(self):
        """Load hierarchical encyclopedia data and build keyword indexes"""
        for object_type in ["companies", "contacts", "deals", "tickets"]:
            data = self.encyclopedia.load_encyclopedia(object_type)
            if data and data.get("groups"):
                self._hierarchical_cache[object_type] = data
                self._build_group_keywords(object_type, data["groups"])
                print(f"✅ Loaded hierarchical {object_type}: {len(data['groups'])} groups")
    
    def _build_group_keywords(self, object_type: str, groups: Dict[str, Any]):
        """Build keyword mapping for efficient group identification"""
        if object_type not in self._group_keywords:
            self._group_keywords[object_type] = {}
        
        for group_name, group_data in groups.items():
            keywords = set()
            
            # Add group display name keywords
            display_name = group_data.get("display_name", "").lower()
            keywords.update(display_name.split())
            
            # Add keywords from property names and labels
            for prop_name, prop_info in group_data.get("properties", {}).items():
                # Add property internal name keywords
                keywords.update(prop_name.lower().split("_"))
                
                # Add property label keywords
                label = prop_info.get("label", "").lower()
                keywords.update(label.split())
            
            # Store keywords for this group
            self._group_keywords[object_type][group_name] = keywords
    
    async def resolve_and_search(self, object_type: str, user_query: str, limit: int = 200, user_email: str = None) -> Dict[str, Any]:
        """
        Hierarchical encyclopedia-first search with dramatic efficiency improvements
        
        Args:
            object_type: HubSpot object type (companies, contacts, deals, tickets)
            user_query: Natural language query from user
            limit: Maximum results to return
            user_email: User's email for personalized queries
            
        Returns:
            Search results with hierarchical analysis and resolved filters
        """
        # Step 1: Identify relevant property groups (massive scope reduction)
        relevant_groups = self._identify_relevant_groups(object_type, user_query)
        
        # Step 2: Analyze query within relevant groups only
        query_analysis = self._analyze_query_hierarchically(object_type, user_query, relevant_groups)
        
        # Step 3: Resolve query to filters using focused search
        filters = self._resolve_query_to_filters_hierarchical(object_type, user_query, relevant_groups, user_email)
        
        # Step 4: Execute search
        results = await self._execute_search(object_type, filters, limit)
        
        # Step 5: Generate insights
        insights = self._generate_hierarchical_insights(query_analysis, filters, results, user_query, relevant_groups)
        
        return {
            "query": user_query,
            "object_type": object_type,
            "relevant_groups": [group["display_name"] for group in relevant_groups],
            "query_analysis": query_analysis,
            "resolved_filters": filters,
            "results": results,
            "total_returned": len(results),
            "limit_applied": limit,
            "note": insights,
            "efficiency_stats": {
                "total_groups_available": len(self._hierarchical_cache.get(object_type, {}).get("groups", {})),
                "groups_searched": len(relevant_groups),
                "efficiency_improvement": f"{((1 - len(relevant_groups) / max(1, len(self._hierarchical_cache.get(object_type, {}).get('groups', {})))) * 100):.1f}% reduction in search scope"
            }
        }
    
    def _identify_relevant_groups(self, object_type: str, user_query: str) -> List[Dict[str, Any]]:
        """
        Identify which property groups are relevant to the user's query
        This dramatically reduces the search scope
        """
        query_lower = user_query.lower()
        query_words = set(re.findall(r'\b\w+\b', query_lower))
        
        hierarchical_data = self._hierarchical_cache.get(object_type, {})
        groups = hierarchical_data.get("groups", {})
        
        relevant_groups = []
        group_scores = []
        
        for group_name, group_data in groups.items():
            # Get keywords for this group
            group_keywords = self._group_keywords.get(object_type, {}).get(group_name, set())
            
            # Calculate relevance score
            common_words = query_words.intersection(group_keywords)
            relevance_score = len(common_words)
            
            # Boost score for exact matches
            display_name_lower = group_data.get("display_name", "").lower()
            for query_word in query_words:
                if query_word in display_name_lower:
                    relevance_score += 2
            
            # Add group if relevant
            if relevance_score > 0:
                group_info = {
                    "name": group_name,
                    "display_name": group_data.get("display_name", ""),
                    "properties": group_data.get("properties", {}),
                    "property_count": group_data.get("property_count", 0),
                    "relevance_score": relevance_score,
                    "matched_keywords": list(common_words)
                }
                relevant_groups.append(group_info)
                group_scores.append(relevance_score)
        
        # Sort by relevance score (highest first)
        relevant_groups.sort(key=lambda x: x["relevance_score"], reverse=True)
        
        # If no specific groups found, include most common groups as fallback
        if not relevant_groups:
            common_groups = ["company_information", "companyinformation", "billing_information", "customer_success"]
            for group_name in common_groups:
                if group_name in groups:
                    relevant_groups.append({
                        "name": group_name,
                        "display_name": groups[group_name].get("display_name", ""),
                        "properties": groups[group_name].get("properties", {}),
                        "property_count": groups[group_name].get("property_count", 0),
                        "relevance_score": 0,
                        "matched_keywords": []
                    })
        
        return relevant_groups[:5]  # Limit to top 5 most relevant groups
    
    def _analyze_query_hierarchically(self, object_type: str, user_query: str, relevant_groups: List[Dict]) -> Dict[str, Any]:
        """Analyze query within the context of relevant groups only"""
        query_lower = user_query.lower()
        
        analysis = {
            "detected_terms": [],
            "owner_terms": [],
            "status_terms": [],
            "date_terms": [],
            "location_terms": [],
            "industry_terms": [],
            "groups_analyzed": [group["display_name"] for group in relevant_groups]
        }
        
        # Search only within relevant groups for efficiency
        for group in relevant_groups:
            properties = group.get("properties", {})
            
            for prop_name, prop_info in properties.items():
                prop_label_lower = prop_info.get("label", "").lower()
                
                # Check if query terms match this property
                if any(term in prop_label_lower for term in query_lower.split()):
                    # Categorize the property
                    if "owner" in prop_label_lower:
                        analysis["owner_terms"].append(prop_info.get("label", ""))
                    elif "status" in prop_label_lower or "stage" in prop_label_lower:
                        analysis["status_terms"].append(prop_info.get("label", ""))
                    elif "date" in prop_label_lower or "renewal" in prop_label_lower:
                        analysis["date_terms"].append(prop_info.get("label", ""))
                    
                    analysis["detected_terms"].append(f"{group['display_name']}: {prop_info.get('label', '')}")
        
        return analysis
    
    def _resolve_query_to_filters_hierarchical(self, object_type: str, user_query: str, relevant_groups: List[Dict], user_email: str = None) -> List[Dict[str, Any]]:
        """Resolve query to filters using hierarchical group data"""
        filters = []
        query_lower = user_query.lower()
        
        # Search within relevant groups only (massive efficiency gain)
        for group in relevant_groups:
            properties = group.get("properties", {})
            
            # Owner resolution
            owner_filters = self._resolve_owner_in_group(query_lower, properties, user_email)
            filters.extend(owner_filters)
            
            # Status resolution  
            status_filters = self._resolve_status_in_group(query_lower, properties)
            filters.extend(status_filters)
            
            # Date resolution
            date_filters = self._resolve_date_in_group(query_lower, properties)
            filters.extend(date_filters)
            
            # Break after finding filters to avoid conflicts
            if filters:
                break
        
        return filters
    
    def _resolve_owner_in_group(self, query: str, properties: Dict[str, Any], user_email: str = None) -> List[Dict[str, Any]]:
        """Resolve owner queries within a specific property group"""
        filters = []
        
        # Look for owner-like properties in this group
        for prop_name, prop_info in properties.items():
            prop_label_lower = prop_info.get("label", "").lower()
            
            if "owner" in prop_label_lower and prop_info.get("value_mappings"):
                owner_mappings = prop_info["value_mappings"]
                
                # Handle "my name" with email matching
                if ("my name" in query or "in my name" in query) and user_email:
                    if user_email and '@' in user_email:
                        email_name = user_email.split('@')[0].lower()
                        email_parts = email_name.replace('.', ' ').replace('_', ' ')
                        
                        for owner_label, owner_id in owner_mappings.items():
                            owner_lower = owner_label.lower()
                            if email_parts in owner_lower or any(part in owner_lower for part in email_parts.split()):
                                filters.append({
                                    "propertyName": prop_name,
                                    "operator": "EQ",
                                    "value": owner_id
                                })
                                return filters
                
                # Handle explicit owner names
                for owner_label, owner_id in owner_mappings.items():
                    owner_lower = owner_label.lower()
                    if owner_lower in query or f"{owner_lower}'s" in query:
                        filters.append({
                            "propertyName": prop_name,
                            "operator": "EQ",
                            "value": owner_id
                        })
                        return filters
        
        return filters
    
    def _resolve_status_in_group(self, query: str, properties: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Resolve status queries within a specific property group"""
        filters = []
        
        for prop_name, prop_info in properties.items():
            prop_label_lower = prop_info.get("label", "").lower()
            
            if ("status" in prop_label_lower or "stage" in prop_label_lower) and prop_info.get("value_mappings"):
                status_mappings = prop_info["value_mappings"]
                
                for status_label, internal_value in status_mappings.items():
                    if status_label.lower() in query:
                        filters.append({
                            "propertyName": prop_name,
                            "operator": "EQ",
                            "value": internal_value
                        })
                        return filters
        
        return filters
    
    def _resolve_date_in_group(self, query: str, properties: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Resolve date queries within a specific property group"""
        filters = []
        
        renewal_terms = ["renewal", "renew", "texting renewal", "upcoming"]
        has_renewal_term = any(term in query for term in renewal_terms)
        
        if has_renewal_term:
            for prop_name, prop_info in properties.items():
                prop_label_lower = prop_info.get("label", "").lower()
                
                if "renewal" in prop_label_lower or "renew" in prop_label_lower:
                    # Prioritize texting renewal
                    if "texting" in prop_label_lower:
                        filters.insert(0, {
                            "propertyName": prop_name,
                            "operator": "HAS_PROPERTY",
                            "value": ""
                        })
                    else:
                        filters.append({
                            "propertyName": prop_name,
                            "operator": "HAS_PROPERTY", 
                            "value": ""
                        })
                    
                    # Return first match to avoid conflicts
                    if filters:
                        return filters[:1]
        
        return filters
    
    async def _execute_search(self, object_type: str, filters: List[Dict], limit: int) -> List[Dict[str, Any]]:
        """Execute search using HubSpot API"""
        try:
            if object_type == "companies":
                # Ensure we request essential display properties
                results = await self.hubspot_client.search_companies(
                    filters=filters, 
                    limit=limit,
                    properties=["name", "domain", "hubspot_owner_id", "account_status", "next_renewal_date", "renewal_status", "city", "state", "industry"]
                )
            else:
                search_request = {
                    "filterGroups": [{"filters": filters}] if filters else [],
                    "limit": limit
                }
                
                response = await self.hubspot_client._make_request(
                    "POST",
                    f"/crm/v3/objects/{object_type}/search", 
                    json=search_request
                )
                results = response.get("results", [])
            
            return results
            
        except Exception as e:
            print(f"Search error for {object_type}: {e}")
            return []
    
    def _generate_hierarchical_insights(self, query_analysis: Dict, filters: List[Dict], results: List[Dict], original_query: str, relevant_groups: List[Dict]) -> str:
        """Generate insights about hierarchical search results"""
        insights = []
        total_results = len(results)
        
        # Efficiency insight
        groups_searched = len(relevant_groups)
        insights.append(f"Searched {groups_searched} most relevant property groups for maximum efficiency.")
        
        if total_results == 0:
            insights.append("No results found. This could indicate:")
            if query_analysis.get("owner_terms"):
                insights.append("• Owner assignments may need to be verified")
            if query_analysis.get("date_terms"):
                insights.append("• Date fields may not be populated yet")
        else:
            if query_analysis.get("owner_terms") and query_analysis.get("date_terms"):
                insights.append(f"Found {total_results} companies matching your criteria.")
        
        return " ".join(insights) if insights else None