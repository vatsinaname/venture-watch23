"""
API entry point for Vercel deployment.
"""
import os
import sys

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.automation.api import app as api_app

# Create the main FastAPI app
app = FastAPI(
    title="Startup Finder API",
    description="API for finding recently funded startups",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, this should be restricted
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include the API routes
app.mount("/", api_app)

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint to check if API is running."""
    return {"message": "Startup Finder API is running"}
