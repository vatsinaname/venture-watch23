"""
Enhanced Perplexity Sonar API integration for collecting startup funding data
with Streamlit dashboard and improved structured data parsing.
"""
import logging
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, ValidationError, Field
import json
import os
import requests
import re

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RecruitmentEmployee(BaseModel):
    """Schema for recruitment team member data."""
    name: str
    position: Optional[str] = "Unknown"
    linkedin: str

class StartupFundingSchema(BaseModel):
    """Schema for structured startup funding data."""
    company_name: str = Field(..., description="Name of the startup company")
    description: str = Field(..., description="Description of what the company does")
    funding_amount: Optional[str] = Field(None, description="Amount of funding raised")
    funding_round: Optional[str] = Field(None, description="Type of funding round")
    funding_date: Optional[str] = Field(None, description="Date when funding was announced")
    investors: List[str] = Field(default_factory=list, description="List of investors")
    industry: Optional[str] = Field(None, description="Industry or sector")
    location: Optional[str] = Field(None, description="Company location")
    company_size: Optional[str] = Field(None, description="Number of employees")
    company_website: Optional[str] = Field(None, description="Company website URL")
    founding_date: Optional[str] = Field(None, description="Company founding date")
    total_funding: Optional[str] = Field(None, description="Total funding raised to date")
    linkedin_page: Optional[str] = Field(None, description="LinkedIn company page")
    email: Optional[str] = Field(None, description="Contact email")
    recruitment_linkedin_employees: Optional[List[RecruitmentEmployee]] = Field(default_factory=list)
    technologies_used: Optional[List[str]] = Field(default_factory=list)
    key_products_services: Optional[List[str]] = Field(default_factory=list)
    social_links: Optional[Dict[str, str]] = Field(default_factory=dict)
    other_relevant_information: Optional[str] = Field(None)
    source: str = Field(default="Perplexity Sonar API")

class StartupListResponse(BaseModel):
    """Schema for the complete response containing multiple startups."""
    startups: List[StartupFundingSchema] = Field(..., description="List of startup companies")
    total_count: int = Field(..., description="Total number of startups found")

class EnhancedPerplexitySonar:
    """Enhanced Perplexity Sonar API client with structured outputs."""
    
    def __init__(self, api_key: str):
        """Initialize the Perplexity Sonar API client."""
        self.api_key = api_key
        self.base_url = "https://api.perplexity.ai/chat/completions"
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
    
    def query_startups_structured(self, query_text: str) -> Dict[str, Any]:
        """Send a structured query using JSON schema for reliable parsing."""
        payload = {
            "model": "sonar-pro",
            "messages": [
                {
                    "role": "system",
                    "content": """You are a startup funding research assistant. Return data in the exact JSON schema format requested. Focus on:
                    1. Recent startups with seed/early-stage funding
                    2. Tech companies in AI, SaaS, healthtech, fintech
                    3. Companies with detailed information available
                    4. Accurate funding and contact details
                    
                    Always return valid JSON matching the schema. If information is not available, use null or empty arrays."""
                },
                {
                    "role": "user",
                    "content": query_text
                }
            ],
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "schema": StartupListResponse.model_json_schema()
                }
            },
            "max_tokens": 8000,
            "temperature": 0.1,
            "top_p": 0.9
        }
        
        try:
            response = requests.post(self.base_url, headers=self.headers, json=payload, timeout=90)
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

    def query_startups_fallback(self, query_text: str) -> Dict[str, Any]:
        """Fallback method without structured output."""
        payload = {
            "model": "sonar-pro",
            "messages": [
                {
                    "role": "system",
                    "content": """You are a startup funding research assistant. Return data as a valid JSON array without any markdown formatting or additional text. Focus on recently funded startups."""
                },
                {
                    "role": "user",
                    "content": query_text + "\n\nReturn ONLY a valid JSON array of startup objects. No markdown, no explanations, just pure JSON."
                }
            ],
            "max_tokens": 8000,
            "temperature": 0.2
        }
        
        try:
            response = requests.post(self.base_url, headers=self.headers, json=payload, timeout=90)
            response.raise_for_status()
            data = response.json()
            
            if "choices" in data and len(data["choices"]) > 0:
                content = data["choices"][0]["message"]["content"]
                return {"text": content, "success": True}
            else:
                return {"text": "No response from Perplexity API", "success": False}
                
        except Exception as e:
            logger.error(f"Error in fallback query: {e}")
            return {"text": f"Error: {str(e)}", "success": False}

class PerplexityCollector:
    """Enhanced startup data collector with structured parsing."""
    
    def __init__(self, api_key: str):
        """Initialize the collector."""
        self.client = EnhancedPerplexitySonar(api_key=api_key)
        self.storage_file = "startup_funding_data.json"
        self.backup_file = "startup_funding_backup.json"
    
    def collect(
        self, 
        months_back: int = 6, 
        industries: Optional[List[str]] = None,
        locations: Optional[List[str]] = None,
        funding_rounds: Optional[List[str]] = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Collect startup funding data using structured approach."""
        query = self.build_structured_query(months_back, limit, industries, locations, funding_rounds)
        logger.info(f"Querying for {limit} startups from the last {months_back} months")
        
        # Try structured approach first
        response = self.client.query_startups_structured(query)
        startups = []
        
        if response.get("success", False):
            startups = self._parse_structured_response(response["text"])
        
        # Fallback to traditional parsing if structured fails
        if not startups:
            logger.info("Structured parsing failed, trying fallback approach")
            response = self.client.query_startups_fallback(query)
            if response.get("success", False):
                startups = self._parse_fallback_response(response["text"])
        
        if not startups:
            logger.error("Both parsing methods failed")
            return []
        
        # Convert to dictionaries for Streamlit display
        startup_dicts = []
        for startup in startups:
            if isinstance(startup, StartupFundingSchema):
                startup_dict = startup.dict()
                startup_dict['name'] = startup_dict['company_name']  # For compatibility
                startup_dicts.append(startup_dict)
            elif isinstance(startup, dict):
                startup['name'] = startup.get('company_name', 'Unknown')
                startup_dicts.append(startup)
        
        logger.info(f"Successfully collected {len(startup_dicts)} startups")
        
        # Save data
        self._save_startups(startups)
        
        # Store in session state
        if startup_dicts:
            st.session_state['current_startups'] = startup_dicts
            st.session_state['last_update'] = datetime.now().isoformat()
            st.session_state['show_cached'] = False
        
        return startup_dicts

    def build_structured_query(self, months_back: int, target_count: int, industries: List[str] = None, locations: List[str] = None, funding_rounds: List[str] = None) -> str:
        """Build a structured query for JSON schema response."""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30 * months_back)
        
        start_date_str = start_date.strftime("%B %Y")
        end_date_str = end_date.strftime("%B %Y")
        
        industry_filter = ""
        if industries:
            industry_filter = f" Focus on {', '.join(industries)} industries."
        
        location_filter = ""
        if locations:
            location_filter = f" Prioritize companies from {', '.join(locations)}."
        
        round_filter = ""
        if funding_rounds:
            round_filter = f" Focus on {', '.join(funding_rounds)} funding rounds."
        
        query = f"""
        Find {target_count} recently funded startups from {start_date_str} to {end_date_str}.{industry_filter}{location_filter}{round_filter}
        
        For each startup, provide complete information including:
        - Company name and description
        - Funding details (amount, round, date, investors)
        - Company information (industry, location, size, website)
        - Contact information (LinkedIn, email, recruitment contacts)
        - Technologies and products/services
        
        Return the data in the exact JSON schema format requested. Include all available details for each startup.
        """
        
        return query

    def _parse_structured_response(self, content: str) -> List[StartupFundingSchema]:
        """Parse structured JSON response."""
        try:
            logger.info("Attempting structured JSON parsing")
            
            # Clean any potential markdown formatting
            content = self._clean_json_content(content)
            
            # Parse the JSON response
            parsed_data = json.loads(content)
            
            if isinstance(parsed_data, dict) and "startups" in parsed_data:
                startups_data = parsed_data["startups"]
                logger.info(f"Found {len(startups_data)} startups in structured response")
                
                startups = []
                for startup_data in startups_data:
                    try:
                        startup = StartupFundingSchema(**startup_data)
                        startups.append(startup)
                    except ValidationError as e:
                        logger.warning(f"Validation error for startup {startup_data.get('company_name', 'Unknown')}: {e}")
                        # Try to create with minimal required fields
                        try:
                            minimal_startup = StartupFundingSchema(
                                company_name=startup_data.get('company_name', 'Unknown Company'),
                                description=startup_data.get('description', 'No description available'),
                                funding_amount=startup_data.get('funding_amount'),
                                funding_round=startup_data.get('funding_round'),
                                investors=startup_data.get('investors', []),
                                industry=startup_data.get('industry'),
                                location=startup_data.get('location')
                            )
                            startups.append(minimal_startup)
                        except Exception as e2:
                            logger.error(f"Could not create minimal startup: {e2}")
                            continue
                
                return startups
            else:
                logger.warning("Response does not contain 'startups' key")
                return []
                
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error in structured parsing: {e}")
            return []
        except Exception as e:
            logger.error(f"Error in structured parsing: {e}")
            return []

    def _parse_fallback_response(self, content: str) -> List[StartupFundingSchema]:
        """Parse fallback response format."""
        try:
            logger.info("Attempting fallback JSON parsing")
            
            # Clean the content
            content = self._clean_json_content(content)
            
            # Try to extract JSON array
            json_match = re.search(r'\[.*?\]', content, re.DOTALL)
            if json_match:
                json_content = json_match.group(0)
            else:
                json_content = content
            
            parsed_data = json.loads(json_content)
            
            if isinstance(parsed_data, list):
                startups = []
                for item in parsed_data:
                    startup = self._create_startup_from_dict(item)
                    if startup:
                        startups.append(startup)
                return startups
            elif isinstance(parsed_data, dict):
                startup = self._create_startup_from_dict(parsed_data)
                return [startup] if startup else []
            else:
                return []
                
        except Exception as e:
            logger.error(f"Error in fallback parsing: {e}")
            return []

    def _clean_json_content(self, content: str) -> str:
        """Clean JSON content from markdown and formatting issues."""
        # Remove markdown code blocks
        content = re.sub(r'```[\w]*\n?', '', content)
        content = re.sub(r'```\s*', '', content)
        
        # Remove citations
        content = re.sub(r'\[\d+\]', '', content)
        
        # Remove currency symbols
        content = re.sub(r'₹\s*', '', content)
        
        # Fix common JSON issues
        content = re.sub(r',\s*([}\]])', r'\1', content)  # Remove trailing commas
        content = re.sub(r'"\s*\n\s*"', '" "', content)  # Fix broken strings
        
        return content.strip()

    def _create_startup_from_dict(self, data: Dict[str, Any]) -> Optional[StartupFundingSchema]:
        """Create a StartupFundingSchema from a dictionary with error handling."""
        try:
            # Handle recruitment contacts
            if "recruitment_contacts" in data and isinstance(data["recruitment_contacts"], list):
                contacts = []
                for contact in data["recruitment_contacts"]:
                    if isinstance(contact, dict) and contact.get("name") and contact.get("linkedin"):
                        contacts.append(RecruitmentEmployee(**contact))
                data["recruitment_linkedin_employees"] = contacts
                del data["recruitment_contacts"]
            
            # Ensure required fields
            data.setdefault("company_name", "Unknown Company")
            data.setdefault("description", "No description available")
            
            # Clean None and empty values
            cleaned_data = {}
            for key, value in data.items():
                if value is not None and value != "" and value != "Not available":
                    cleaned_data[key] = value
            
            return StartupFundingSchema(**cleaned_data)
            
        except Exception as e:
            logger.error(f"Error creating startup from dict: {e}")
            return None

    def _save_startups(self, startups: List[StartupFundingSchema]):
        """Save startups to JSON file."""
        try:
            data = {
                "timestamp": datetime.now().isoformat(),
                "count": len(startups),
                "startups": [startup.dict() if hasattr(startup, 'dict') else startup for startup in startups]
            }
            
            with open(self.storage_file, "w", encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Saved {len(startups)} startups to {self.storage_file}")
            
        except Exception as e:
            logger.error(f"Error saving startups: {e}")

    def load_startups(self) -> List[Dict[str, Any]]:
        """Load startups from JSON file."""
        try:
            if os.path.exists(self.storage_file):
                with open(self.storage_file, "r", encoding='utf-8') as f:
                    data = json.load(f)
                    return data.get("startups", [])
        except Exception as e:
            logger.error(f"Error loading startups: {e}")
        return []

def display_startup_card(startup: Dict[str, Any], index: int):
    """Display a detailed startup card."""
    with st.container():
        # Header with company name and funding
        col1, col2 = st.columns([3, 1])
        with col1:
            st.subheader(f"🚀 {startup.get('company_name', 'Unknown Company')}")
        with col2:
            if startup.get('funding_amount'):
                st.metric("Funding", startup['funding_amount'])
        
        # Description
        if startup.get('description'):
            st.write("**Description:**")
            st.write(startup['description'])
        
        # Key details in columns
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if startup.get('industry'):
                st.write(f"**Industry:** {startup['industry']}")
            if startup.get('location'):
                st.write(f"**Location:** {startup['location']}")
            if startup.get('company_size'):
                st.write(f"**Size:** {startup['company_size']}")
        
        with col2:
            if startup.get('funding_round'):
                st.write(f"**Round:** {startup['funding_round']}")
            if startup.get('funding_date'):
                st.write(f"**Date:** {startup['funding_date']}")
            if startup.get('founding_date'):
                st.write(f"**Founded:** {startup['founding_date']}")
        
        with col3:
            if startup.get('company_website'):
                st.write(f"**Website:** [{startup['company_website']}]({startup['company_website']})")
            if startup.get('linkedin_page'):
                st.write(f"**LinkedIn:** [{startup['linkedin_page']}]({startup['linkedin_page']})")
            if startup.get('email'):
                st.write(f"**Email:** {startup['email']}")
        
        # Investors
        if startup.get('investors') and len(startup['investors']) > 0:
            st.write("**Investors:**")
            investor_text = ", ".join(startup['investors'])
            st.write(investor_text)
        
        # Technologies
        if startup.get('technologies_used') and len(startup['technologies_used']) > 0:
            st.write("**Technologies:**")
            tech_tags = " ".join([f"`{tech}`" for tech in startup['technologies_used']])
            st.markdown(tech_tags)
        
        # Products/Services
        if startup.get('key_products_services') and len(startup['key_products_services']) > 0:
            st.write("**Products/Services:**")
            st.write(", ".join(startup['key_products_services']))
        
        # Recruitment contacts
        if startup.get('recruitment_linkedin_employees') and len(startup['recruitment_linkedin_employees']) > 0:
            st.write("**Recruitment Contacts:**")
            for contact in startup['recruitment_linkedin_employees']:
                if isinstance(contact, dict):
                    name = contact.get('name', 'Unknown')
                    position = contact.get('position', 'Unknown')
                    linkedin = contact.get('linkedin', '')
                    if linkedin:
                        st.write(f"- {name} ({position}) - [LinkedIn]({linkedin})")
                    else:
                        st.write(f"- {name} ({position})")
        
        # Additional information
        if startup.get('other_relevant_information'):
            st.write("**Additional Information:**")
            st.write(startup['other_relevant_information'])
        
        st.divider()

# Streamlit Dashboard
def main():
    """Main Streamlit application with improved display."""
    st.set_page_config(
        page_title="Startup Funding Tracker",
        page_icon="🚀",
        layout="wide"
    )
    
    st.title("🚀 Startup Funding Tracker")
    st.markdown("Track recently funded startups using Perplexity Sonar Pro API with structured outputs")
    
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
    
    # Search parameters
    st.sidebar.subheader("Search Parameters")
    months_back = st.sidebar.slider("Months to look back", 1, 12, 6)
    target_count = st.sidebar.slider("Number of startups", 5, 30, 15)
    
    # Filters
    industries = st.sidebar.multiselect(
        "Industries (optional)",
        ["AI/ML", "SaaS", "Fintech", "Healthtech", "E-commerce", "EdTech", "Blockchain", "IoT"]
    )
    
    locations = st.sidebar.multiselect(
        "Locations (optional)",
        ["Bangalore", "Mumbai", "Delhi", "Hyderabad", "Chennai", "Pune", "Gurgaon"]
    )
    
    funding_rounds = st.sidebar.multiselect(
        "Funding Rounds (optional)",
        ["Seed", "Series A", "Series B", "Series C", "Pre-Series A"]
    )
    
    # Load existing data
    existing_startups = collector.load_startups()
    
    # Display existing data info
    if existing_startups:
        st.sidebar.success(f"Cached: {len(existing_startups)} startups")
        if st.sidebar.button("Show Cached Data"):
            st.session_state['current_startups'] = existing_startups
            st.session_state['show_cached'] = True
    
    # Search button
    if st.sidebar.button("🔍 Search New Startups", type="primary"):
        with st.spinner("Searching for startups... This may take up to 2 minutes."):
            try:
                startups = collector.collect(
                    months_back=months_back,
                    industries=industries or None,
                    locations=locations or None,
                    funding_rounds=funding_rounds or None,
                    limit=target_count
                )
                
                if startups:
                    st.success(f"Successfully found {len(startups)} startups!")
                    st.rerun()
                else:
                    st.error("No startups found. Please try different search parameters.")
                    
            except Exception as e:
                st.error(f"Error during search: {str(e)}")
                logger.error(f"Search error: {e}")

    # Determine what data to display
    display_data = st.session_state.get('current_startups', [])
    
    if not display_data and existing_startups:
        display_data = existing_startups
        st.info("Showing cached data from previous search")
    
    if display_data:
        # Display summary metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Startups", len(display_data))
        
        with col2:
            funded_count = len([s for s in display_data if s.get("funding_amount")])
            st.metric("With Funding Info", funded_count)
        
        with col3:
            industries_found = set([s.get("industry") for s in display_data if s.get("industry")])
            st.metric("Industries", len(industries_found))
        
        with col4:
            locations_found = set([s.get("location") for s in display_data if s.get("location")])
            st.metric("Locations", len(locations_found))
        
        # Display options
        display_mode = st.radio(
            "Display Mode:",
            ["Detailed Cards", "Table View", "Analytics", "Raw JSON"],
            horizontal=True
        )
        
        if display_mode == "Detailed Cards":
            st.subheader("Startup Details")
            for i, startup in enumerate(display_data):
                display_startup_card(startup, i)
        
        elif display_mode == "Table View":
            # Create DataFrame
            df_data = []
            for startup in display_data:
                df_data.append({
                    "Company": startup.get("company_name", "Unknown"),
                    "Industry": startup.get("industry", "N/A"),
                    "Location": startup.get("location", "N/A"),
                    "Funding": startup.get("funding_amount", "N/A"),
                    "Round": startup.get("funding_round", "N/A"),
                    "Date": startup.get("funding_date", "N/A"),
                    "Investors": ", ".join(startup.get("investors", [])[:3])
                })
            
            df = pd.DataFrame(df_data)
            st.dataframe(df, use_container_width=True, height=600)
        
        elif display_mode == "Analytics":
            col1, col2 = st.columns(2)
            
            with col1:
                # Industry distribution
                industries = [s.get("industry") for s in display_data if s.get("industry")]
                if industries:
                    industry_counts = pd.Series(industries).value_counts()
                    st.subheader("Distribution by Industry")
                    st.bar_chart(industry_counts)
            
            with col2:
                # Location distribution
                locations = [s.get("location") for s in display_data if s.get("location")]
                if locations:
                    location_counts = pd.Series(locations).value_counts().head(10)
                    st.subheader("Top Locations")
                    st.bar_chart(location_counts)
            
            # Funding rounds
            rounds = [s.get("funding_round") for s in display_data if s.get("funding_round")]
            if rounds:
                round_counts = pd.Series(rounds).value_counts()
                st.subheader("Funding Rounds Distribution")
                st.bar_chart(round_counts)
        
        elif display_mode == "Raw JSON":
            st.subheader("Raw JSON Data")
            st.json(display_data)
            
            # Download button
            json_str = json.dumps(display_data, indent=2, default=str)
            st.download_button(
                label="📥 Download JSON",
                data=json_str,
                file_name=f"startup_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json"
            )
    
    else:
        st.info("No startup data available. Use the search function to find startups.")
        
        # show sample of what the tool can find
        st.subheader("What this tool can find:")
        st.write("""
        - Recently funded startups (seed to Series C)
        - Company details and descriptions
        - Funding amounts and investor information
        - Contact details including recruitment team
        - Technologies and products used
        - Industry and location data
        """)

if __name__ == "__main__":
    main()
