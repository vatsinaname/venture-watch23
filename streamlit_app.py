"""
Streamlit entry for Vercel deploy.
"""
import os
import sys

# add the project root to the python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# import the Streamlit app
from src.dashboard.app import main

# run the app
if __name__ == "__main__":
    main()
