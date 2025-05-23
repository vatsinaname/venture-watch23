"""
Enhanced Perplexity Sonar API integration for collecting startup funding data
with Streamlit dashboard and improved data parsing.
"""
import logging
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
import json
import os
import requests
import re

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class StartupFundingSchema(BaseModel):
    """Schema for structured startup funding data."""
    company_name: str
    description: str
    funding_amount: Optional[str]
    funding_round: Optional[str]
    funding_date: Optional[str]
    investors: List[str]
    industry: Optional[str]
    location: Optional[str]
    company_size: Optional[str]
    company_website: Optional[str]
    source: str = "Perplexity Sonar API"

class EnhancedPerplexitySonar:
    """Enhanced Perplexity Sonar API client with better model selection."""
    
    def __init__(self, api_key: str):
        """
        Initialize the Perplexity Sonar API client.
        
        Args:
            api_key: Perplexity API key
        """
        self.api_key = api_key
        self.base_url = "https://api.perplexity.ai/chat/completions"
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
    
    def query_startups(self, query_text: str, model: str = "sonar-pro") -> Dict[str, Any]:
        """
        Send a structured query to get startup funding data.
        
        Args:
            query_text: Query text
            model: Model to use (sonar-pro recommended for complex queries)
            
        Returns:
            Response from Perplexity API
        """
        payload = {
            "model": model,
            "messages": [
                {
                    "role": "system",
                    "content": """You are a startup funding research assistant. 
                    Provide accurate, up-to-date information about recently funded startups.
                    Return responses in a structured JSON array format with detailed information for each startup.
                    Ensure all data is factual and include citations where possible."""
                },
                {
                    "role": "user",
                    "content": query_text
                }
            ],
            "max_tokens": 8000,  # sonar-pro supports up to 8k output tokens
            "temperature": 0.2,  # Lower temperature for more factual responses
            "top_p": 0.9
        }
        
        try:
            response = requests.post(self.base_url, headers=self.headers, json=payload, timeout=60)
            response.raise_for_status()
            data = response.json()
            
            if "choices" in data and len(data["choices"]) > 0:
                content = data["choices"][0]["message"]["content"]
                return {"text": content, "success": True}
            else:
                return {"text": "No response from Perplexity API", "success": False}
                
        except requests.exceptions.Timeout:
            logger.error("Request timed out")
            return {"text": "Request timed out", "success": False}
        except Exception as e:
            logger.error(f"Error querying Perplexity API: {e}")
            return {"text": f"Error: {str(e)}", "success": False}

class PerplexityCollector:
    """Enhanced startup data collector with improved parsing and storage."""
    
    def __init__(self, api_key: str):
        """Initialize the collector."""
        self.client = EnhancedPerplexitySonar(api_key=api_key)
        self.storage_file = "startup_funding_data.json"
        self.backup_file = "startup_funding_backup.json"
    
    def get_source_name(self) -> str:
        """Get the name of the data source."""
        return "Perplexity API"
    
    def collect(
        self, 
        months_back: int = 3, 
        industries: Optional[List[str]] = None,
        locations: Optional[List[str]] = None,
        funding_rounds: Optional[List[str]] = None,
        limit: int = 30
    ) -> List[Dict[str, Any]]:
        """Collect startup funding data."""
        query = self.build_enhanced_query(months_back, limit)
        logger.info(f"Querying for {limit} startups from the last {months_back} months")
        
        response = self.client.query_startups(query)
        
        if not response.get("success", False):
            logger.error("Failed to get response from API")
            return []
        
        startups = self._parse_enhanced_response(response["text"])
        
        # Convert StartupFundingSchema to dict with consistent field names
        startup_dicts = []
        for startup in startups:
            startup_dict = startup.dict()
            # Keep both name and company_name fields for compatibility
            startup_dict['name'] = startup_dict['company_name']
            startup_dicts.append(startup_dict)
        
        # Debug log
        logger.info("Processed startup data:")
        for startup in startup_dicts:
            logger.info(f"Name: {startup.get('name')}, Company Name: {startup.get('company_name')}")
        
        self._save_startups(startups)
        
        # Store in session state if we're in a Streamlit context
        if 'st' in globals():
            st.session_state['current_startups'] = startup_dicts
            st.session_state['show_cached'] = False
            # Debug display in Streamlit
            st.sidebar.write("Debug: Found startups", [s.get('name') for s in startup_dicts])
        
        return startup_dicts

    def build_enhanced_query(self, months_back: int = 6, target_count: int = 30) -> str:
        """Build an enhanced query to get more startups."""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30 * months_back)
        
        start_date_str = start_date.strftime("%B %Y")
        end_date_str = end_date.strftime("%B %Y")
        
        query = f"""
        Find and list {target_count} recently funded startups from {start_date_str} to {end_date_str}.
        
        For each startup, provide the following information in a structured JSON array format:
        
        [
          {{
            "company_name": "Exact company name",
            "description": "Brief description of what the company does",
            "funding_amount": "Amount raised (e.g., $10M, $5.2M)",
            "funding_round": "Type of round (e.g., Seed, Series A, Series B)",
            "funding_date": "Date of funding announcement (YYYY-MM-DD format)",
            "investors": ["List of investors"],
            "industry": "Primary industry/sector",
            "location": "Company headquarters location",
            "company_size": "Number of employees (if available)",
            "company_website": "Official website URL (if available)"
          }}
        ]
        
        Focus on:
        - Tech startups (AI, SaaS, fintech, biotech, e-commerce, etc.)
        - Seed, Series A, Series B, and Series C rounds
        - Companies from major startup hubs (US, Europe, Asia)
        - Recent announcements from reliable sources
        
        Ensure the response is a valid JSON array with complete information for each startup.
        """
        
        return query
    
    def _parse_enhanced_response(self, content: str) -> List[StartupFundingSchema]:
        """Enhanced parsing to extract multiple startups from API response."""
        startups = []
        logger.info("Raw response content:")
        logger.info(content)
        
        try:
            # Try to find JSON content first
            matches = [
                # Look for JSON array
                re.search(r'\[\s*{.*?}\s*(?:,\s*{\s*.*?}\s*)*\]', content, re.DOTALL),
                # Look for JSON object
                re.search(r'{\s*".*?}', content, re.DOTALL),
                # Look for markdown code block
                re.search(r'```(?:json)?\s*(.*?)```', content, re.DOTALL)
            ]
            
            json_str = None
            for match in matches:
                if match:
                    json_str = match.group(1) if len(match.groups()) > 0 else match.group(0)
                    try:
                        parsed_data = json.loads(json_str)
                        if parsed_data:  # If valid JSON, use this match
                            break
                    except:
                        continue
            
            if not json_str:
                json_str = content
            
            try:
                parsed_data = json.loads(json_str)
                logger.info(f"Successfully parsed JSON data: {json.dumps(parsed_data, indent=2)}")
                
                if isinstance(parsed_data, list):
                    for item in parsed_data:
                        startup = self._create_startup_from_dict(item)
                        if startup:
                            startups.append(startup)
                elif isinstance(parsed_data, dict):
                    startup = self._create_startup_from_dict(parsed_data)
                    if startup:
                        startups.append(startup)
            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error: {e}")
                startups = self._parse_text_response(content)
                
        except Exception as e:
            logger.error(f"Error parsing response: {e}")
            startups = self._parse_text_response(content)
        
        logger.info(f"Successfully parsed {len(startups)} startups")
        for startup in startups:
            logger.info(f"Startup name: {startup.company_name}")
        
        return startups
    
    def _create_startup_from_dict(self, data: Dict[str, Any]) -> Optional[StartupFundingSchema]:
        """Create a StartupFundingSchema from a dictionary."""
        try:
            # Normalize field names and handle variations
            normalized_data = {}
            for key, value in data.items():
                key_lower = key.lower().replace(" ", "_").replace("-", "_")
                if "name" in key_lower and "company" in key_lower:
                    normalized_data["company_name"] = str(value)
                elif key_lower in ["company_name", "name", "startup_name"]:
                    normalized_data["company_name"] = str(value)
                elif key_lower in ["description", "desc", "about"]:
                    normalized_data["description"] = str(value)
                elif "funding" in key_lower and "amount" in key_lower:
                    normalized_data["funding_amount"] = str(value) if value else None
                elif "round" in key_lower or "stage" in key_lower:
                    normalized_data["funding_round"] = str(value) if value else None
                elif "date" in key_lower:
                    normalized_data["funding_date"] = str(value) if value else None
                elif "investor" in key_lower:
                    if isinstance(value, list):
                        normalized_data["investors"] = [str(inv) for inv in value]
                    else:
                        normalized_data["investors"] = [str(value)] if value else []
                elif "industry" in key_lower or "sector" in key_lower:
                    normalized_data["industry"] = str(value) if value else None
                elif "location" in key_lower or "city" in key_lower:
                    normalized_data["location"] = str(value) if value else None
                elif "size" in key_lower or "employees" in key_lower:
                    normalized_data["company_size"] = str(value) if value else None
                elif "website" in key_lower or "url" in key_lower:
                    normalized_data["company_website"] = str(value) if value else None
            
            # Ensure required fields
            if "company_name" not in normalized_data:
                return None
            
            if "description" not in normalized_data:
                normalized_data["description"] = "No description available"
            
            if "investors" not in normalized_data:
                normalized_data["investors"] = []
            
            return StartupFundingSchema(**normalized_data)
            
        except Exception as e:
            logger.error(f"Error creating startup from dict: {e}")
            return None
    
    def _parse_text_response(self, content: str) -> List[StartupFundingSchema]:
        """Parse text response when JSON parsing fails."""
        startups = []
        
        # Split by numbered entries or clear delimiters
        patterns = [
            r'\n\s*\d+\.\s*([^\n]+)',  # Numbered list
            r'\n\s*\*\*([^*]+)\*\*',   # Bold company names
            r'\n\s*##?\s*([^\n]+)',    # Headers
        ]
        
        entries = []
        for pattern in patterns:
            matches = re.findall(pattern, content)
            if len(matches) > 5:  # If we find many matches, use this pattern
                entries = re.split(pattern, content)[1:]  # Skip first empty split
                break
        
        if not entries:
            # Try splitting by paragraphs
            entries = [p.strip() for p in content.split('\n\n') if p.strip()]
        
        for entry in entries[:30]:  # Limit to 30 entries
            startup = self._parse_single_entry(entry)
            if startup:
                startups.append(startup)
        
        return startups
    
    def _parse_single_entry(self, entry: str) -> Optional[StartupFundingSchema]:
        """Parse a single text entry into a StartupFundingSchema."""
        try:
            # Extract company name (first line or bold text)
            name_patterns = [
                r'^\*\*([^*]+)\*\*',
                r'^([^:\n.]+)',
                r'(?:Company|Name|Startup):\s*([^\n]+)',
            ]
            
            name = None
            for pattern in name_patterns:
                match = re.search(pattern, entry, re.MULTILINE)
                if match:
                    name = match.group(1).strip()
                    break
            
            if not name:
                return None
            
            # Extract other fields using regex patterns
            funding_amount = self._extract_field(entry, [
                r'(?:funding|raised|amount):\s*([^\n]+)',
                r'\$[\d.]+[MB]',
                r'[\d.]+\s*(?:million|billion)',
            ])
            
            funding_round = self._extract_field(entry, [
                r'(?:round|series|stage):\s*([^\n]+)',
                r'(?:seed|series\s*[abc]|pre-seed)',
            ])
            
            description = self._extract_field(entry, [
                r'(?:description|about):\s*([^\n]+)',
                r'[.!?]\s*([^.!?]*(?:company|startup|platform)[^.!?]*[.!?])',
            ])
            
            investors_text = self._extract_field(entry, [
                r'(?:investors?):\s*([^\n]+)',
                r'(?:led by|backed by):\s*([^\n]+)',
            ])
            
            investors = []
            if investors_text:
                investors = [inv.strip() for inv in re.split(r',|\band\b', investors_text)]
            
            industry = self._extract_field(entry, [
                r'(?:industry|sector):\s*([^\n]+)',
                r'(?:AI|fintech|biotech|SaaS|e-commerce|healthtech)',
            ])
            
            location = self._extract_field(entry, [
                r'(?:location|based|headquarters):\s*([^\n]+)',
                r'(?:San Francisco|New York|London|Berlin|Singapore)',
            ])
            
            return StartupFundingSchema(
                company_name=name,
                description=description or "No description available",
                funding_amount=funding_amount,
                funding_round=funding_round,
                funding_date=None,  # Difficult to extract reliably from text
                investors=investors,
                industry=industry,
                location=location,
                company_size=None,
                company_website=None
            )
            
        except Exception as e:
            logger.error(f"Error parsing entry: {e}")
            return None
    
    def _extract_field(self, text: str, patterns: List[str]) -> Optional[str]:
        """Extract a field from text using multiple patterns."""
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                result = match.group(1) if len(match.groups()) > 0 else match.group(0)
                return result.strip()
        return None
    
    def _save_startups(self, startups: List[StartupFundingSchema]):
        """Save startups to JSON file with backup."""
        try:
            # Handle backup file
            if os.path.exists(self.storage_file):
                # Remove old backup if it exists
                if os.path.exists(self.backup_file):
                    os.remove(self.backup_file)
                # Create new backup
                os.rename(self.storage_file, self.backup_file)
            
            # Save new data
            data = [startup.dict() for startup in startups]
            with open(self.storage_file, "w", encoding='utf-8') as f:
                json.dump({
                    "timestamp": datetime.now().isoformat(),
                    "count": len(startups),
                    "startups": data
                }, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Saved {len(startups)} startups to {self.storage_file}")
            
        except Exception as e:
            logger.error(f"Error saving startups: {e}")
            # If something went wrong, try direct save without backup
            try:
                data = [startup.dict() for startup in startups]
                with open(self.storage_file, "w", encoding='utf-8') as f:
                    json.dump({
                        "timestamp": datetime.now().isoformat(),
                        "count": len(startups),
                        "startups": data
                    }, f, indent=2, ensure_ascii=False)
                logger.info(f"Saved {len(startups)} startups without backup")
            except Exception as e2:
                logger.error(f"Failed to save even without backup: {e2}")
    
    def load_startups(self) -> List[StartupFundingSchema]:
        """Load startups from JSON file."""
        try:
            if os.path.exists(self.storage_file):
                with open(self.storage_file, "r", encoding='utf-8') as f:
                    data = json.load(f)
                    startups_data = data.get("startups", [])
                    return [StartupFundingSchema(**startup) for startup in startups_data]
        except Exception as e:
            logger.error(f"Error loading startups: {e}")
        return []

# Streamlit Dashboard
def main():
    """Main Streamlit application."""
    st.set_page_config(
        page_title="Startup Funding Tracker",
        page_icon="🚀",
        layout="wide"
    )
    
    st.title("🚀 Startup Funding Tracker")
    st.markdown("Track recently funded startups using Perplexity Sonar API")
    
    # Sidebar configuration
    st.sidebar.header("Configuration")
    
    # API Key input
    api_key = st.sidebar.text_input(
        "Perplexity API Key", 
        type="password",
        help="Enter your Perplexity API key"
    )
    
    if not api_key:
        st.warning("Please enter your Perplexity API key in the sidebar to continue.")
        st.stop()
    
    # Initialize collector
    collector = PerplexityCollector(api_key)
    
    # Parameters
    months_back = st.sidebar.slider("Months to look back", 1, 12, 6)
    target_count = st.sidebar.slider("Number of startups", 10, 50, 30)
    
    # Load existing data
    existing_startups = collector.load_startups()
    
    # Display existing data info
    if existing_startups:
        st.sidebar.success(f"Loaded {len(existing_startups)} existing startups")
        if st.sidebar.button("Show Cached Data"):
            st.session_state.show_cached = True
    
    # Collect new data button
    if st.sidebar.button("🔍 Search New Startups", type="primary"):
        with st.spinner("Searching for startups... This may take a few minutes."):
            try:
                startups = collector.collect(months_back, limit=target_count)
                if startups:
                    st.session_state.current_startups = startups
                    st.success(f"Found {len(startups)} startups!")
                else:
                    st.error("No startups found. Please try adjusting your search parameters.")
            except Exception as e:
                st.error(f"Error collecting data: {e}")
    
    # Determine which data to display
    display_data = None
    if hasattr(st.session_state, 'current_startups'):
        display_data = st.session_state.current_startups
        st.info("Showing newly collected data")
    elif st.session_state.get('show_cached', False) and existing_startups:
        display_data = existing_startups
        st.info("Showing cached data")
    elif existing_startups:
        display_data = existing_startups
        st.info("Showing previously cached data (click 'Search New Startups' for fresh data)")
    
    if display_data:
        # Display metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Startups", len(display_data))
        
        with col2:
            funded_count = len([s for s in display_data if s.get("funding_amount")])
            st.metric("With Funding Info", funded_count)
        
        with col3:
            industries = [s.get("industry") for s in display_data if s.get("industry")]
            unique_industries = len(set(industries)) if industries else 0
            st.metric("Industries", unique_industries)
        
        with col4:
            locations = [s.get("location") for s in display_data if s.get("location")]
            unique_locations = len(set(locations)) if locations else 0
            st.metric("Locations", unique_locations)
        
        # Tabs for different views
        tab1, tab2, tab3, tab4 = st.tabs(["📊 Overview", "📋 Detailed List", "📈 Analytics", "📄 Raw JSON"])
        
        with tab1:
            # Create DataFrame for overview
            df_data = []
            for startup in display_data:
                df_data.append({
                    "Company": startup.get("company_name"),
                    "Industry": startup.get("industry") or "N/A",
                    "Location": startup.get("location") or "N/A",
                    "Funding Amount": startup.get("funding_amount") or "N/A",
                    "Round": startup.get("funding_round") or "N/A",
                    "Investors": ", ".join(startup.get("investors", [])[:2]) + ("..." if len(startup.get("investors", [])) > 2 else "")
                })
            
            df = pd.DataFrame(df_data)
            st.dataframe(df, use_container_width=True)
        
        with tab2:
            # Detailed cards view
            for i, startup in enumerate(display_data):
                with st.expander(f"{startup.get('company_name')} - {startup.get('funding_amount') or 'Amount N/A'}"):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.write("**Description:**", startup.get("description"))
                        st.write("**Industry:**", startup.get("industry") or "N/A")
                        st.write("**Location:**", startup.get("location") or "N/A")
                    
                    with col2:
                        st.write("**Funding Amount:**", startup.get("funding_amount") or "N/A")
                        st.write("**Round:**", startup.get("funding_round") or "N/A")
                        st.write("**Date:**", startup.get("funding_date") or "N/A")
                        if startup.get("investors"):
                            st.write("**Investors:**", ", ".join(startup.get("investors")))
                        if startup.get("company_website"):
                            st.write("**Website:**", startup.get("company_website"))
        
        with tab3:
            # Analytics
            if display_data:
                # Industry distribution
                industries = [s.get("industry") for s in display_data if s.get("industry")]
                if industries:
                    industry_counts = pd.Series(industries).value_counts()
                    st.subheader("Distribution by Industry")
                    st.bar_chart(industry_counts)
                
                # Location distribution
                locations = [s.get("location") for s in display_data if s.get("location")]
                if locations:
                    location_counts = pd.Series(locations).value_counts().head(10)
                    st.subheader("Top 10 Locations")
                    st.bar_chart(location_counts)
                
                # Funding rounds
                rounds = [s.get("funding_round") for s in display_data if s.get("funding_round")]
                if rounds:
                    round_counts = pd.Series(rounds).value_counts()
                    st.subheader("Funding Rounds")
                    st.pie_chart(round_counts)
        
        with tab4:
            # Raw JSON data
            st.subheader("Raw JSON Data")
            json_data = display_data
            st.json(json_data)
            
            # Download button
            json_str = json.dumps(json_data, indent=2, default=str)
            st.download_button(
                label="📥 Download JSON",
                data=json_str,
                file_name=f"startup_funding_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json"
            )
    
    else:
        st.info("No startup data available. Click 'Search New Startups' to begin.")

if __name__ == "__main__":
    main()
