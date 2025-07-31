#!/usr/bin/env python3
"""
Encyclopedia-powered MCP server for HubSpot middleware
Uses comprehensive label-to-internal mapping for accurate queries
"""

import asyncio
import json
import logging
from typing import Any, Sequence
from mcp.server.models import InitializationOptions
from mcp.server import NotificationOptions, Server
from mcp.types import Tool, TextContent, CallToolRequest
import mcp.types as types
import httpx

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("hubspot-encyclopedia-mcp")

# MCP server instance
server = Server("hubspot-encyclopedia-mcp")

# Middleware base URL - use environment variable or default to Render deployment
import os
MIDDLEWARE_URL = os.environ.get("HUBSPOT_MIDDLEWARE_URL", "https://hubspot-claude-middleware.onrender.com")

@server.list_tools()
async def handle_list_tools() -> list[Tool]:
    """List available tools for encyclopedia-powered HubSpot searches"""
    return [
        Tool(
            name="search_companies_encyclopedia",
            description="Search HubSpot companies using natural language. AUTOMATICALLY uses encyclopedia to understand data structure first, then searches. The encyclopedia maps user labels to correct internal HubSpot values (e.g., 'Active' → 'Evaluating'). Always shows the encyclopedia mappings used and provides comprehensive results with context.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Natural language query (e.g., 'Tyler Beagley's active companies with upcoming texting renewal dates', 'enterprise customers in technology')"
                    },
                    "limit": {
                        "type": "integer", 
                        "description": "Maximum number of results to return (default: 200, max: 1000)",
                        "default": 200
                    }
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="get_company_mappings",
            description="Get available label mappings for companies to understand what search terms are possible",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="search_mappings",
            description="Search for specific label mappings to understand how user terms map to internal values",
            inputSchema={
                "type": "object",
                "properties": {
                    "search_term": {
                        "type": "string",
                        "description": "Term to search for in the mappings (e.g., 'tyler', 'active', 'technology')"
                    },
                    "object_type": {
                        "type": "string",
                        "description": "HubSpot object type to search",
                        "enum": ["companies", "contacts", "deals", "tickets"],
                        "default": "companies"
                    }
                },
                "required": ["search_term"]
            }
        ),
        Tool(
            name="refresh_encyclopedia",
            description="Refresh the encyclopedia data from HubSpot (required before first use)",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        )
    ]

@server.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> Sequence[TextContent]:
    """Handle tool calls for encyclopedia-powered searches"""
    
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            
            if name == "search_companies_encyclopedia":
                query = arguments.get("query", "")
                limit = arguments.get("limit", 200)
                
                if not query:
                    return [TextContent(
                        type="text",
                        text="Error: Query parameter is required"
                    )]
                
                # Use encyclopedia-powered search endpoint
                response = await client.post(
                    f"{MIDDLEWARE_URL}/search/encyclopedia",
                    json={"query": query, "limit": limit},
                    params={"object_type": "companies"}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # Format the response with clear encyclopedia authority and better context
                    total_returned = data.get('total_returned', 0)
                    limit_applied = data.get('limit_applied', 0)
                    note = data.get('note')
                    resolved_filters = data.get('resolved_filters', [])
                    query_analysis = data.get('query_analysis', {})
                    
                    result_text = f"**🔍 Encyclopedia-Powered HubSpot Search**\n"
                    result_text += f"**Query:** {query}\n"
                    result_text += f"**Results:** {total_returned} companies found\n\n"
                    
                    # Show the encyclopedia analysis process
                    if query_analysis:
                        result_text += "**📚 Encyclopedia Analysis:**\n"
                        detected_terms = query_analysis.get('detected_terms', [])
                        if detected_terms:
                            for term in detected_terms:
                                result_text += f"- Detected: '{term}'\n"
                        result_text += "\n"
                    
                    # Show the authoritative mapping used
                    if resolved_filters:
                        result_text += "**🔧 Applied Mappings:**\n"
                        for filter_item in resolved_filters:
                            prop = filter_item.get('propertyName', '')
                            value = filter_item.get('value', '')
                            operator = filter_item.get('operator', 'EQ')
                            if prop == 'account_status':
                                result_text += f"- Account Status: User term → '{value}' (HubSpot internal)\n"
                            elif prop == 'hubspot_owner_id':
                                result_text += f"- Owner: 'Tyler Beagley' → ID '{value}'\n"
                            elif prop == 'next_renewal_date':
                                result_text += f"- Texting Renewal Date: {operator} {value}\n"
                            else:
                                result_text += f"- {prop}: {operator} {value}\n"
                        result_text += "\n"
                    
                    # Show data quality insights
                    if note:
                        result_text += f"**💡 Data Insights:**\n{note}\n\n"
                    
                    result_text += f"**📋 Companies Found:**\n"
                    
                    for i, company in enumerate(data.get('results', [])[:10], 1):
                        name = company.get('properties', {}).get('name', 'N/A')
                        domain = company.get('properties', {}).get('domain', 'N/A')
                        owner = company.get('properties', {}).get('hubspot_owner_id', 'N/A')
                        status = company.get('properties', {}).get('account_status', 'N/A')
                        renewal_date = company.get('properties', {}).get('next_renewal_date', 'N/A')
                        
                        result_text += f"**{i}. {name}**\n"
                        result_text += f"   • Domain: {domain}\n"
                        result_text += f"   • Owner: {owner}\n"
                        result_text += f"   • Status: {status}\n"
                        if renewal_date != 'N/A':
                            result_text += f"   • Next Texting Renewal: {renewal_date}\n"
                        result_text += "\n"
                    
                    if total_returned > 10:
                        result_text += f"*... and {total_returned - 10} more companies*\n\n"
                    
                    # Add comprehensive footer
                    result_text += f"**✅ Encyclopedia Authority:** This search used comprehensive HubSpot property mappings to translate your natural language query into precise database filters. The {total_returned} results represent the exact count from your HubSpot data."
                    
                    return [TextContent(type="text", text=result_text)]
                else:
                    return [TextContent(
                        type="text",
                        text=f"Error searching companies: {response.status_code} - {response.text}"
                    )]
            
            elif name == "get_company_mappings":
                response = await client.get(f"{MIDDLEWARE_URL}/encyclopedia/mappings/companies")
                
                if response.status_code == 200:
                    data = response.json()
                    
                    if data.get("total_properties", 0) == 0:
                        return [TextContent(
                            type="text",
                            text="No encyclopedia data loaded. Run the 'refresh_encyclopedia' tool first."
                        )]
                    
                    result_text = f"**Available Company Mappings**\n\n"
                    result_text += f"**Total Properties with Mappings:** {data.get('total_properties', 0)}\n\n"
                    
                    # Show top properties with most mappings
                    properties = data.get('properties', {})
                    sorted_props = sorted(properties.items(), key=lambda x: x[1].get('total_values', 0), reverse=True)
                    
                    result_text += "**Top Properties by Value Count:**\n"
                    for prop_name, prop_info in sorted_props[:10]:
                        total_values = prop_info.get('total_values', 0)
                        sample_values = prop_info.get('sample_values', [])
                        result_text += f"- **{prop_name}**: {total_values} values\n"
                        if sample_values:
                            result_text += f"  Sample values: {', '.join(sample_values[:3])}\n"
                        result_text += "\n"
                    
                    return [TextContent(type="text", text=result_text)]
                else:
                    return [TextContent(
                        type="text", 
                        text=f"Error getting mappings: {response.status_code} - {response.text}"
                    )]
            
            elif name == "search_mappings":
                search_term = arguments.get("search_term", "")
                object_type = arguments.get("object_type", "companies")
                
                if not search_term:
                    return [TextContent(
                        type="text",
                        text="Error: search_term parameter is required"
                    )]
                
                response = await client.get(
                    f"{MIDDLEWARE_URL}/encyclopedia/search-mappings/{object_type}",
                    params={"search_term": search_term}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    
                    result_text = f"**Mapping Search Results for '{search_term}' in {object_type}**\n\n"
                    result_text += f"**Matching Properties:** {data.get('matching_properties', 0)}\n\n"
                    
                    matches = data.get('matches', {})
                    for prop_name, values in matches.items():
                        result_text += f"**{prop_name}:**\n"
                        for label, internal_value in list(values.items())[:10]:
                            result_text += f"  - '{label}' → {internal_value}\n"
                        if len(values) > 10:
                            result_text += f"  ... and {len(values) - 10} more values\n"
                        result_text += "\n"
                    
                    if not matches:
                        result_text += "No matching mappings found.\n"
                    
                    return [TextContent(type="text", text=result_text)]
                else:
                    return [TextContent(
                        type="text",
                        text=f"Error searching mappings: {response.status_code} - {response.text}"
                    )]
            
            elif name == "refresh_encyclopedia":
                response = await client.post(f"{MIDDLEWARE_URL}/encyclopedia/refresh")
                
                if response.status_code == 200:
                    data = response.json()
                    
                    result_text = "**Encyclopedia Refresh Completed Successfully!**\n\n"
                    
                    export_info = data.get('export_info', {})
                    result_text += f"**Export Summary:**\n"
                    result_text += f"- Total Objects: {len(export_info.get('exported_objects', []))}\n"
                    result_text += f"- Total Properties: {export_info.get('total_properties', 0)}\n"
                    result_text += f"- Total Value Mappings: {export_info.get('total_values', 0)}\n"
                    result_text += f"- Export Time: {export_info.get('total_export_time_seconds', 0)} seconds\n\n"
                    
                    result_text += "**Per Object Type:**\n"
                    for obj_info in export_info.get('exported_objects', []):
                        obj_type = obj_info.get('object_type', '')
                        props_count = obj_info.get('properties_count', 0)
                        values_count = obj_info.get('values_count', 0)
                        result_text += f"- **{obj_type}**: {props_count} properties, {values_count} value mappings\n"
                    
                    result_text += "\nEncyclopedia is now ready for searches!"
                    
                    return [TextContent(type="text", text=result_text)]
                else:
                    return [TextContent(
                        type="text",
                        text=f"Error refreshing encyclopedia: {response.status_code} - {response.text}"
                    )]
            
            else:
                return [TextContent(
                    type="text",
                    text=f"Unknown tool: {name}"
                )]
                
    except Exception as e:
        logger.error(f"Error in tool call: {e}")
        return [TextContent(
            type="text",
            text=f"Error: {str(e)}"
        )]

async def main():
    # Import here to avoid issues with event loops
    from mcp.server.stdio import stdio_server
    
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="hubspot-encyclopedia-mcp",
                server_version="1.0.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )

if __name__ == "__main__":
    asyncio.run(main())