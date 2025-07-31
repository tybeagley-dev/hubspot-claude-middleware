"""
Encyclopedia-powered query resolver for reliable HubSpot searches
"""

import re
from typing import Dict, List, Any, Optional, Tuple
from .encyclopedia import EncyclopediaService
from .hubspot_client import HubSpotClient


class EncyclopediaResolver:
    def __init__(self):
        self.encyclopedia = EncyclopediaService()
        self.hubspot_client = HubSpotClient()
        self._encyclopedia_cache = {}
        self._load_encyclopedia_cache()
    
    def _load_encyclopedia_cache(self):
        """Load encyclopedia data into memory for fast lookups"""
        for object_type in ["companies", "contacts", "deals", "tickets"]:
            data = self.encyclopedia.load_encyclopedia(object_type)
            if data:
                self._encyclopedia_cache[object_type] = data
                value_count = len(data.get('value_mappings', {}))
                print(f"✅ Loaded {object_type} encyclopedia: {value_count} properties with value mappings")
    
    async def resolve_and_search(self, object_type: str, user_query: str, limit: int = 200) -> Dict[str, Any]:
        """
        Encyclopedia-first search: Analyze query thoroughly, then search
        
        Args:
            object_type: HubSpot object type (companies, contacts, deals, tickets)
            user_query: Natural language query from user
            limit: Maximum results to return
            
        Returns:
            Search results with comprehensive query analysis and resolved filters
        """
        # Step 1: Analyze the query against encyclopedia
        query_analysis = self._analyze_query_comprehensively(object_type, user_query)
        
        # Step 2: Resolve query to HubSpot filters using analysis
        filters = self.resolve_query_to_filters(object_type, user_query)
        
        # Step 3: Execute search
        results = await self._execute_search(object_type, filters, limit)
        
        # Step 4: Generate insights about the data
        data_insights = self._generate_data_insights(query_analysis, filters, results, user_query)
        
        return {
            "query": user_query,
            "object_type": object_type,
            "query_analysis": query_analysis,
            "resolved_filters": filters,
            "results": results,
            "total_returned": len(results),
            "limit_applied": limit,
            "note": data_insights
        }
    
    def _analyze_query_comprehensively(self, object_type: str, user_query: str) -> Dict[str, Any]:
        """Analyze the user's query against encyclopedia to understand intent"""
        query_lower = user_query.lower()
        encyclopedia_data = self._encyclopedia_cache.get(object_type, {})
        
        analysis = {
            "detected_terms": [],
            "owner_terms": [],
            "status_terms": [],
            "date_terms": [],
            "location_terms": [],
            "industry_terms": [],
            "tier_terms": []
        }
        
        if not encyclopedia_data:
            return analysis
        
        value_mappings = encyclopedia_data.get('value_mappings', {})
        
        # Detect owner terms
        for owner_prop in ["hubspot_owner_id", "company_owner"]:
            if owner_prop in value_mappings:
                for owner_label in value_mappings[owner_prop].keys():
                    if owner_label.lower() in query_lower or f"{owner_label.lower()}'s" in query_lower:
                        analysis["owner_terms"].append(owner_label)
                        analysis["detected_terms"].append(f"Owner: {owner_label}")
        
        # Detect status terms
        if "account_status" in value_mappings:
            for status_label in value_mappings["account_status"].keys():
                if status_label.lower() in query_lower:
                    analysis["status_terms"].append(status_label)
                    analysis["detected_terms"].append(f"Status: {status_label}")
        
        # Detect date/renewal terms
        renewal_terms = ["renewal", "renew", "texting renewal", "upcoming", "next"]
        for term in renewal_terms:
            if term in query_lower:
                analysis["date_terms"].append(term)
                analysis["detected_terms"].append(f"Date: {term}")
        
        # Detect location terms
        location_terms = ["dallas", "texas", "houston", "austin", "utah", "provo"]
        for term in location_terms:
            if term in query_lower:
                analysis["location_terms"].append(term)
                analysis["detected_terms"].append(f"Location: {term}")
        
        return analysis
    
    def _generate_data_insights(self, query_analysis: Dict, filters: List[Dict], results: List[Dict], original_query: str) -> str:
        """Generate intelligent insights about the search results"""
        insights = []
        
        # Analyze what was found vs expected
        total_results = len(results)
        
        if total_results == 0:
            if query_analysis.get("status_terms"):
                status = query_analysis["status_terms"][0]
                insights.append(f"No companies found with '{status}' status. This could mean:")
                insights.append("• The status is labeled differently in your HubSpot")
                insights.append("• No companies currently have this status")
                insights.append("• Companies might be in 'Evaluating' or other statuses instead")
            elif query_analysis.get("date_terms"):
                insights.append("No companies found with upcoming renewal dates. This could mean:")
                insights.append("• Renewal dates haven't been set for companies yet")
                insights.append("• The renewal date field is named differently")
                insights.append("• All renewals may be past due or future-dated")
        else:
            # Analyze the actual results to provide insights
            if query_analysis.get("owner_terms") and query_analysis.get("date_terms"):
                owner = query_analysis["owner_terms"][0]
                insights.append(f"Found {total_results} companies for {owner} with renewal date criteria.")
                
                # Check if any actually have renewal dates
                companies_with_dates = 0
                for company in results:
                    renewal_date = company.get('properties', {}).get('next_renewal_date')
                    if renewal_date and renewal_date != 'N/A':
                        companies_with_dates += 1
                
                if companies_with_dates == 0:
                    insights.append(f"However, none of these {total_results} companies have renewal dates populated in HubSpot.")
                else:
                    insights.append(f"{companies_with_dates} of these companies have actual renewal dates set.")
        
        return " ".join(insights) if insights else None
    
    def resolve_query_to_filters(self, object_type: str, user_query: str) -> List[Dict[str, Any]]:
        """
        Resolve user query to HubSpot API filters using encyclopedia
        
        Args:
            object_type: HubSpot object type
            user_query: User's natural language query
            
        Returns:
            List of HubSpot API filters
        """
        filters = []
        query_lower = user_query.lower()
        
        # Get encyclopedia data for this object type
        encyclopedia_data = self._encyclopedia_cache.get(object_type, {})
        if not encyclopedia_data:
            return filters
        
        value_mappings = encyclopedia_data.get('value_mappings', {})
        
        # Owner-based searches
        owner_filters = self._resolve_owner_queries(query_lower, value_mappings)
        filters.extend(owner_filters)
        
        # Status-based searches  
        status_filters = self._resolve_status_queries(query_lower, value_mappings)
        filters.extend(status_filters)
        
        # Industry-based searches
        industry_filters = self._resolve_industry_queries(query_lower, value_mappings)
        filters.extend(industry_filters)
        
        # Tier/size-based searches
        tier_filters = self._resolve_tier_queries(query_lower, value_mappings)
        filters.extend(tier_filters)
        
        # Location-based searches
        location_filters = self._resolve_location_queries(query_lower, value_mappings)
        filters.extend(location_filters)
        
        # Date-based searches (renewal dates, etc.)
        date_filters = self._resolve_date_queries(query_lower, value_mappings)
        filters.extend(date_filters)
        
        # Generic property value searches
        generic_filters = self._resolve_generic_queries(query_lower, value_mappings)
        filters.extend(generic_filters)
        
        return filters
    
    def _resolve_owner_queries(self, query: str, value_mappings: Dict) -> List[Dict[str, Any]]:
        """Resolve owner-based queries using encyclopedia"""
        filters = []
        
        # Check both hubspot_owner_id and company_owner mappings
        for owner_prop in ["hubspot_owner_id", "company_owner"]:
            if owner_prop not in value_mappings:
                continue
                
            owner_mappings = value_mappings[owner_prop]
            
            # Only look for owner names if query explicitly mentions ownership or person names
            # Skip owner matching for generic location/status queries
            owner_indicators = ["owner", "owned by", "'s", "portfolio"]
            has_owner_context = any(indicator in query for indicator in owner_indicators)
            
            if not has_owner_context:
                continue  # Skip owner matching entirely
            
            # Look for owner names in query - prioritize exact matches
            exact_matches = []
            partial_matches = []
            
            for owner_label, owner_id in owner_mappings.items():
                owner_lower = owner_label.lower()
                
                # Check for exact full name matches first (including possessive)
                if owner_lower in query or f"{owner_lower}'s" in query:
                    exact_matches.append((owner_prop, owner_id))
                    continue
                
                # Check for first name matches only if query has clear owner context
                if " " in owner_label and "'s" in query:  # Only if possessive is used
                    first_name = owner_label.split()[0].lower()
                    if f"{first_name}'s" in query:
                        partial_matches.append((owner_prop, owner_id, owner_lower))
            
            # Prefer exact matches, then longest partial match
            if exact_matches:
                prop, owner_id = exact_matches[0]
                filters.append({
                    "propertyName": prop,
                    "operator": "EQ", 
                    "value": owner_id
                })
                return filters
            elif partial_matches:
                # Find the longest matching name to avoid "Tyler" matching both "Tyler Price" and "Tyler Beagley"
                longest_match = max(partial_matches, key=lambda x: len(x[2]))
                prop, owner_id, _ = longest_match
                filters.append({
                    "propertyName": prop,
                    "operator": "EQ", 
                    "value": owner_id
                })
                return filters
        
        return filters
    
    def _resolve_status_queries(self, query: str, value_mappings: Dict) -> List[Dict[str, Any]]:
        """Resolve status-based queries using encyclopedia"""
        filters = []
        
        # Check account_status mappings
        if "account_status" in value_mappings:
            status_mappings = value_mappings["account_status"]
            
            for status_label, internal_value in status_mappings.items():
                if status_label.lower() in query:
                    filters.append({
                        "propertyName": "account_status",
                        "operator": "EQ",
                        "value": internal_value
                    })
                    break  # Take first match
        
        return filters
    
    def _resolve_industry_queries(self, query: str, value_mappings: Dict) -> List[Dict[str, Any]]:
        """Resolve industry-based queries using encyclopedia"""  
        filters = []
        
        if "industry" in value_mappings:
            industry_mappings = value_mappings["industry"]
            
            for industry_label, internal_value in industry_mappings.items():
                # Match industry terms (technology, restaurants, etc.)
                industry_terms = [
                    industry_label.lower(),
                    industry_label.lower().rstrip('s'),  # Remove plural
                    "tech" if "technology" in industry_label.lower() else None
                ]
                
                for term in industry_terms:
                    if term and term in query:
                        filters.append({
                            "propertyName": "industry", 
                            "operator": "EQ",
                            "value": internal_value
                        })
                        return filters
        
        return filters
    
    def _resolve_tier_queries(self, query: str, value_mappings: Dict) -> List[Dict[str, Any]]:
        """Resolve tier/size-based queries using encyclopedia"""
        filters = []
        
        # Check customer_tier mappings
        if "customer_tier" in value_mappings:
            tier_mappings = value_mappings["customer_tier"]
            
            tier_terms = {
                "enterprise": ["enterprise", "large", "big"],
                "small": ["small", "startup"],
                "professional": ["professional", "pro"],
                "standard": ["standard", "regular"]
            }
            
            for tier_label, internal_value in tier_mappings.items():
                tier_lower = tier_label.lower()
                
                # Check direct matches and synonyms
                search_terms = tier_terms.get(tier_lower, [tier_lower])
                
                for term in search_terms:
                    if term in query:
                        filters.append({
                            "propertyName": "customer_tier",
                            "operator": "EQ", 
                            "value": internal_value
                        })
                        return filters
        
        return filters
    
    def _resolve_location_queries(self, query: str, value_mappings: Dict) -> List[Dict[str, Any]]:
        """Resolve location-based queries using encyclopedia"""
        filters = []
        
        # Common city searches
        cities = {
            "dallas": "Dallas",
            "texas": "TX",  # State searches
            "houston": "Houston", 
            "austin": "Austin",
            "san antonio": "San Antonio",
            "new york": "New York",
            "chicago": "Chicago",
            "los angeles": "Los Angeles",
            "miami": "Miami",
            "atlanta": "Atlanta",
            "denver": "Denver",
            "seattle": "Seattle",
            "portland": "Portland",
            "phoenix": "Phoenix",
            "salt lake city": "Salt Lake City",
            "provo": "Provo",
            "utah": "UT"
        }
        
        # Check for city matches - prioritize specific cities over states
        city_filters = []
        state_filters = []
        
        for city_term, city_value in cities.items():
            if city_term in query:
                # Determine if it's a state or city
                if len(city_value) == 2:  # State abbreviation
                    state_filters.append({
                        "propertyName": "state",
                        "operator": "EQ",
                        "value": city_value
                    })
                else:  # City name
                    city_filters.append({
                        "propertyName": "city", 
                        "operator": "EQ",
                        "value": city_value
                    })
        
        # Prioritize city filters over state filters
        if city_filters:
            filters.extend(city_filters)
        elif state_filters:
            filters.extend(state_filters)
        
        return filters
    
    def _resolve_generic_queries(self, query: str, value_mappings: Dict) -> List[Dict[str, Any]]:
        """Resolve generic property value queries using encyclopedia"""
        filters = []
        
        # Search through all property value mappings for matches
        for property_name, property_values in value_mappings.items():
            # Skip properties we've already handled specifically
            if property_name in ["hubspot_owner_id", "company_owner", "account_status", "industry", "customer_tier"]:
                continue
                
            for value_label, internal_value in property_values.items():
                if len(value_label) > 2 and value_label.lower() in query:
                    filters.append({
                        "propertyName": property_name,
                        "operator": "EQ",
                        "value": internal_value  
                    })
                    # Only add first match per property to avoid conflicts
                    break
        
        return filters
    
    def _resolve_date_queries(self, query: str, value_mappings: Dict) -> List[Dict[str, Any]]:
        """Resolve date-based queries (renewal dates, upcoming dates, etc.)"""
        filters = []
        
        # Handle renewal date queries
        renewal_terms = ["renewal", "renew", "texting renewal", "text renewal", "upcoming renewal"]
        has_renewal_term = any(term in query for term in renewal_terms)
        
        if has_renewal_term:
            # Look for next_renewal_date or similar properties
            date_properties = []
            for prop_name in value_mappings.keys():
                if any(term in prop_name.lower() for term in ["renewal", "renew", "next_", "due", "expire"]):
                    date_properties.append(prop_name)
            
            # If we found renewal-related properties, filter for non-empty values
            for prop in date_properties:
                # Check for companies that actually have renewal dates set
                if "upcoming" in query or "next" in query:
                    # Filter for dates that are not null/empty
                    filters.append({
                        "propertyName": prop,
                        "operator": "HAS_PROPERTY",
                        "value": ""  # HAS_PROPERTY checks for non-null values
                    })
                break  # Only add one date filter to avoid conflicts
        
        return filters
    
    async def _execute_search(self, object_type: str, filters: List[Dict], limit: int) -> List[Dict[str, Any]]:
        """Execute search using HubSpot API"""
        try:
            if object_type == "companies":
                # Use existing company search
                results = await self.hubspot_client.search_companies(filters=filters, limit=limit)
            else:
                # Generic search for other object types
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
    
    def get_available_mappings(self, object_type: str) -> Dict[str, Any]:
        """Get available mappings for an object type"""
        encyclopedia_data = self._encyclopedia_cache.get(object_type, {})
        
        if not encyclopedia_data:
            return {"error": f"No encyclopedia data loaded for {object_type}"}
        
        value_mappings = encyclopedia_data.get('value_mappings', {})
        
        # Return summary of available mappings
        summary = {}
        for prop_name, values in value_mappings.items():
            if len(values) > 0:
                sample_values = list(values.keys())[:5]  # First 5 values as sample
                summary[prop_name] = {
                    "total_values": len(values),
                    "sample_values": sample_values
                }
        
        return {
            "object_type": object_type,
            "total_properties": len(summary),
            "properties": summary
        }
    
    def search_mappings(self, object_type: str, search_term: str) -> Dict[str, Any]:
        """Search for mappings containing a term"""
        encyclopedia_data = self._encyclopedia_cache.get(object_type, {})
        
        if not encyclopedia_data:
            return {"error": f"No encyclopedia data loaded for {object_type}"}
        
        value_mappings = encyclopedia_data.get('value_mappings', {})
        matches = {}
        
        search_lower = search_term.lower()
        
        for prop_name, values in value_mappings.items():
            matching_values = {}
            for label, internal_value in values.items():
                if search_lower in label.lower():
                    matching_values[label] = internal_value
            
            if matching_values:
                matches[prop_name] = matching_values
        
        return {
            "object_type": object_type,
            "search_term": search_term,
            "matching_properties": len(matches),
            "matches": matches
        }