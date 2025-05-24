"""Configuration settings for Venture-Watch."""
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# API Keys
PERPLEXITY_API_KEY = os.getenv('PERPLEXITY_API_KEY', '')
