"""Configuration settings for the application."""
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# API Keys
PERPLEXITY_API_KEY = os.getenv('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', '')

# Other configuration settings can be added here
