# Vercel Deployment Configuration

This directory contains configuration files for deploying the Startup Finder application to Vercel.

## Deployment Structure

The deployment to Vercel consists of two main components:

1. **Frontend Dashboard (Streamlit)**: The interactive dashboard for visualizing startup data
2. **Backend API (FastAPI)**: The REST API for data collection, storage, and integration with workflow automation tools

## Configuration Files

- `vercel.json`: Main configuration file for Vercel deployment
- `requirements.txt`: Python dependencies required for the application
- `api/index.py`: Entry point for the FastAPI backend
- `streamlit_app.py`: Entry point for the Streamlit dashboard

## Deployment Instructions

1. Create a Vercel account if you don't have one already
2. Install the Vercel CLI: `npm install -g vercel`
3. Login to Vercel: `vercel login`
4. Navigate to the project directory
5. Deploy the project: `vercel`
6. Follow the prompts to complete the deployment

## Environment Variables

The following environment variables need to be set in your Vercel project:

- `PERPLEXITY_API_KEY`: Your Perplexity API key
- `DATABASE_URL`: URL for your database (SQLite for development, PostgreSQL for production)
- `STREAMLIT_SERVER_PORT`: Port for the Streamlit server (default: 8501)
- `API_SERVER_PORT`: Port for the API server (default: 8000)

## Custom Domain

To set up a custom domain for your deployed application:

1. Go to your Vercel dashboard
2. Select your project
3. Click on "Domains"
4. Add your custom domain
5. Follow the instructions to configure DNS settings

## Continuous Deployment

Vercel supports continuous deployment from GitHub. To set this up:

1. Push your project to GitHub
2. Connect your GitHub repository to Vercel
3. Configure the build settings
4. Enable automatic deployments

## Troubleshooting

If you encounter issues during deployment:

1. Check the Vercel deployment logs
2. Verify that all dependencies are correctly specified in requirements.txt
3. Ensure all environment variables are properly set
4. Check that the entry points (api/index.py and streamlit_app.py) are correctly configured
