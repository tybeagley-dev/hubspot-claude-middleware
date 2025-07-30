# HubSpot Claude Middleware - Quick Reference

## 🚀 Deployed Service
- **URL**: https://hubspot-claude-middleware.onrender.com
- **GitHub**: https://github.com/tybeagley-dev/hubspot-claude-middleware
- **Render**: [Your Render Dashboard]

## 📋 Key Endpoints
```bash
# Health check
curl https://hubspot-claude-middleware.onrender.com/

# List companies
curl https://hubspot-claude-middleware.onrender.com/companies?limit=5

# Natural language search
curl -X POST https://hubspot-claude-middleware.onrender.com/companies/search \
  -H "Content-Type: application/json" \
  -d '{"query": "technology companies", "limit": 3}'

# Contracts metrics
curl https://hubspot-claude-middleware.onrender.com/metrics/contracts-closed
```

## 🔑 Environment Variables
- `HUBSPOT_ACCESS_TOKEN`: [Your HubSpot Access Token]

## 🎯 What Makes This Unique vs HubSpot MCP
1. **Natural Language Processing** - "technology companies" → HubSpot filters
2. **Custom Value Mapping** - "cancelled" → "Pending Cancellation"
3. **Pre-built Analytics** - /metrics/contracts-closed endpoint
4. **Data Formatting** - "250000000" → "250.0M"
5. **Business Logic Layer** - Abstracts HubSpot complexity

## 🔧 Local Development
```bash
cd /Users/tylerbeagley/hubspot-claude-middleware
export HUBSPOT_ACCESS_TOKEN="your_hubspot_token_here"
python main.py
```

## 📁 Project Structure
```
├── main.py                 # FastAPI application
├── requirements.txt        # Dependencies
├── render.yaml            # Deployment config
├── config/
│   ├── settings.py        # Environment config
│   └── mappings.py        # Property translations
└── services/
    ├── hubspot_client.py  # HubSpot API client
    ├── translator.py      # Property translator
    └── query_parser.py    # Natural language parser
```

## 💡 Example Claude Queries (Only Your Middleware Can Answer)
- "Find companies with 'Pending Cancellation' status"
- "Search for 'technology companies with high revenue' using natural language"
- "Get contracts closed metrics with monthly breakdown"
- "Show companies with formatted revenue (250.0M style)"

## 🔄 Updates & Maintenance
- Code changes: Push to GitHub → Auto-deploys to Render
- Environment vars: Update in Render dashboard
- Logs: View in Render dashboard under "Logs" tab