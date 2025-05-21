"""
Integration guide for n8n and Zapier workflow automation.
"""

# Venture-watch - Workflow Automation Integration Guide

This guide explains how to integrate Venture-watch with workflow automation tools like n8n and Zapier.

## API Overview

Startup Finder provides a RESTful API that can be used to automate various tasks:

- Data collection from multiple sources
- LinkedIn enrichment of startup data
- Retrieval of startup information with filtering
- Access to analytics data

## n8n Integration

### Setting Up n8n Connection

1. In n8n, add an HTTP Request node
2. Configure the node to connect to the Startup Finder API
3. Set the appropriate endpoint and method

### Example Workflows

#### New Startup Alert Workflow

This workflow checks for new startups and sends notifications:

1. **HTTP Request** node:
   - Method: GET
   - URL: `http://your-api-url/startups?months_back=1&limit=10`
   - Authentication: None (or as configured)

2. **Filter** node:
   - Filter for startups added in the last 24 hours

3. **Send Email/Slack/Teams** node:
   - Configure to send notifications with startup details

#### Data Collection Workflow

This workflow triggers data collection:

1. **HTTP Request** node:
   - Method: POST
   - URL: `http://your-api-url/collect`
   - Body: JSON with collection parameters
   ```json
   {
     "months_back": 3,
     "use_perplexity": true,
     "perplexity_api_key": "your-api-key",
     "use_web_scraping": true,
     "web_scraping_sources": [
       {"name": "TechCrunch", "url": "https://techcrunch.com/category/venture/"}
     ],
     "use_browser": true
   }
   ```

2. **Process results** as needed

## Zapier Integration

### Setting Up Zapier Connection

1. Create a new Zap
2. Choose "Webhooks by Zapier" as the trigger app
3. Select "Catch Hook" as the trigger event
4. Use the Zapier webhook URL in your application

### Example Zaps

#### New Startup Notification

1. **Trigger**: Schedule (e.g., daily)
2. **Action**: Webhook to `GET /startups` with appropriate filters
3. **Action**: Filter for new startups
4. **Action**: Send notification (Email, Slack, etc.)

#### LinkedIn Enrichment

1. **Trigger**: Webhook or Schedule
2. **Action**: Webhook to `POST /enrich`
3. **Action**: Process results or send notification

## Important Notes

- **Manual Triggering**: Due to system limitations, scheduled or periodic tasks should be manually triggered rather than relying on automatic scheduling.
- **Rate Limiting**: Be mindful of API rate limits, especially for LinkedIn enrichment which involves web scraping.
- **API Keys**: Store API keys securely and never expose them in client-side code.

## API Reference

See the full API documentation at `/docs` when the API is running.

### Key Endpoints

- `GET /startups` - Get startups with filtering
- `GET /startups/{id}` - Get a specific startup
- `POST /collect` - Collect new startup data
- `POST /enrich` - Enrich startups with LinkedIn data
- `GET /analytics/*` - Various analytics endpoints
