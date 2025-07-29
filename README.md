# HubSpot Claude Middleware

A FastAPI middleware for HubSpot integration with natural language query processing and property translation.

## Features

- 🔍 Natural language company search
- 🔄 Property name/value translation for human readability  
- 📊 Contracts closed metrics endpoint
- 🚀 Ready for Render deployment
- 🔒 Environment variable configuration

## API Endpoints

- `GET /` - Health check
- `GET /health` - Service health status
- `POST /companies/search` - Search companies with natural language queries
- `GET /companies/{id}` - Get specific company by ID
- `GET /companies` - List companies with pagination
- `GET /metrics/contracts-closed` - Get contracts closed analytics

## Local Development

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Set environment variables:**
   ```bash
   export HUBSPOT_ACCESS_TOKEN="your_token_here"
   ```
   
   Or create a `.env` file:
   ```
   HUBSPOT_ACCESS_TOKEN=your_token_here
   DEBUG=true
   ```

3. **Run the server:**
   ```bash
   python main.py
   # or
   uvicorn main:app --reload
   ```

4. **Test the API:**
   ```bash
   curl http://localhost:8000/
   curl http://localhost:8000/companies?limit=5
   ```

## Deployment to Render

### Prerequisites
- GitHub account
- Render account
- HubSpot access token

### Step-by-Step Deployment

1. **Push to GitHub:**
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git branch -M main
   git remote add origin https://github.com/yourusername/hubspot-claude-middleware.git
   git push -u origin main
   ```

2. **Deploy on Render:**
   - Go to [render.com](https://render.com) and sign in
   - Click "New +" → "Web Service"
   - Connect your GitHub repository
   - Render will auto-detect the `render.yaml` configuration

3. **Set Environment Variables:**
   - In Render dashboard, go to your service
   - Navigate to "Environment" tab
   - Add: `HUBSPOT_ACCESS_TOKEN` = `your_actual_token`

4. **Deploy:**
   - Click "Create Web Service"
   - Render will build and deploy automatically
   - Your API will be available at `https://your-service-name.onrender.com`

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `HUBSPOT_ACCESS_TOKEN` | ✅ | - | HubSpot API access token |
| `DEBUG` | ❌ | `false` | Enable debug mode |
| `LOG_LEVEL` | ❌ | `INFO` | Logging level |
| `DEFAULT_COMPANY_LIMIT` | ❌ | `100` | Default query limit |
| `MAX_COMPANY_LIMIT` | ❌ | `200` | Maximum query limit |
| `RATE_LIMIT_PER_MINUTE` | ❌ | `100` | API rate limit |

## Property Mappings

The middleware includes property translation for better readability:

- `name` → `Company Name`
- `domain` → `Website Domain`
- `industry` → `Industry`
- `account_status` → `Account Status`
  - `cancelled` → `Pending Cancellation` ⭐

## Example Requests

### Search Companies
```bash
curl -X POST "https://your-app.onrender.com/companies/search" \
  -H "Content-Type: application/json" \
  -d '{"query": "technology companies", "limit": 10}'
```

### Get Company
```bash
curl "https://your-app.onrender.com/companies/12345"
```

### Contracts Metrics
```bash
curl "https://your-app.onrender.com/metrics/contracts-closed?start_date=2024-01-01&end_date=2024-12-31"
```

## Architecture

```
├── main.py                 # FastAPI application
├── requirements.txt        # Python dependencies
├── render.yaml            # Render deployment config
├── config/
│   ├── settings.py        # Environment configuration
│   └── mappings.py        # Property translations
└── services/
    ├── hubspot_client.py  # HubSpot API client
    ├── translator.py      # Property translator
    └── query_parser.py    # Natural language parser
```

## Troubleshooting

### Common Issues

1. **"HUBSPOT_ACCESS_TOKEN environment variable is required"**
   - Ensure the token is set in Render environment variables
   - Verify the token has correct permissions

2. **"Rate limit exceeded"**
   - Adjust `RATE_LIMIT_PER_MINUTE` environment variable
   - Implement request throttling

3. **"limit must be in range [0..200]"**
   - Ensure `MAX_COMPANY_LIMIT` is set to 200 or less

### Logs
View logs in Render dashboard under "Logs" tab for debugging.

## License

MIT License