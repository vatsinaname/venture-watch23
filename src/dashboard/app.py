"""
Main Streamlit dashboard application for Startup Finder.
"""
import os
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import json

# import local modules
from src.data_storage.database import DatabaseManager
from src.data_collection.orchestrator import DataCollectionOrchestrator
from src.data_collection.perplexity_collector import PerplexityCollector
from src.data_collection.web_scraping_collector import WebScrapingCollector

def main():
    # set page config
    st.set_page_config(
        page_title="Venture-Watch",
        page_icon="🚀",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    # initialize database manager
    @st.cache_resource
    def get_database_manager():
        """Get or create database manager instance."""
        db_path = os.path.join(os.getcwd(), "data", "startups.db")
        return DatabaseManager(f"sqlite:///" + db_path)

    db_manager = get_database_manager()

    # Load startup data from JSON file
    def load_startup_data():
        try:
            with open("startup_data.json", "r") as f:
                data = json.load(f)
                df = pd.DataFrame(data)

                # Check if 'funding_date' column exists
                if 'funding_date' in df.columns:
                    df['funding_date'] = pd.to_datetime(df['funding_date'], errors='coerce')
                else:
                    df['funding_date'] = None  # Or create an empty column

                return df
        except FileNotFoundError:
            st.error("Startup data file not found. Please collect data first.")
            return pd.DataFrame()
        except Exception as e:
            st.error(f"Error loading startup data: {e}")
            return pd.DataFrame()

    # custom CSS
    st.markdown("""
    <style>
        .main-header {
            font-size: 2.5rem;
            font-weight: 700;
            color: #1E88E5;
            margin-bottom: 1rem;
        }
        .sub-header {
            font-size: 1.5rem;
            font-weight: 600;
            color: #424242;
            margin-bottom: 1rem;
        }
        .card {
            padding: 1.5rem;
            border-radius: 0.5rem;
            background-color: #f8f9fa;
            box-shadow: 0 0.125rem 0.25rem rgba(0, 0, 0, 0.075);
            margin-bottom: 1rem;
        }
        .metric-value {
            font-size: 2rem;
            font-weight: 700;
            color: #1E88E5;
        }
        .metric-label {
            font-size: 1rem;
            color: #616161;
        }
        .footer {
            margin-top: 3rem;
            padding-top: 1rem;
            border-top: 1px solid #e0e0e0;
            text-align: center;
            color: #9e9e9e;
        }
        .company-card {
            padding: 1rem;
            border-radius: 0.5rem;
            background-color: white;
            box-shadow: 0 0.125rem 0.25rem rgba(0, 0, 0, 0.075);
            margin-bottom: 1rem;
            border-left: 4px solid #1E88E5;
        }
        .company-name {
            font-size: 1.25rem;
            font-weight: 600;
            color: #1E88E5;
            margin-bottom: 0.5rem;
        }
        .company-detail {
            margin-bottom: 0.25rem;
            color: #616161;
        }
        .company-funding {
            font-weight: 600;
            color: #43a047;
        }
        .filter-section {
            margin-bottom: 1rem;
        }
        /* Custom dark theme for Streamlit widgets */
        .stTextInput > div > div > input,
        .stTextArea textarea,
        .stNumberInput input,
        .stMultiSelect > div > div > div,
        .stSelectbox > div > div > div,
        select,
        input[type="text"],
        input[type="number"],
        textarea {
            background-color: #23232b !important;
            color: #f1f1f1 !important;
            border: 1px solid #444 !important;
            caret-color: #1E88E5 !important;
        }
        .stTextInput > div > div > input::placeholder,
        .stTextArea textarea::placeholder,
        .stMultiSelect > div > div > div,
        .stSelectbox > div > div > div {
            color: #888 !important;
        }
        /* Remove box/border from slider container */
        .stSlider > div {
            background: none !important;
            border: none !important;
            box-shadow: none !important;
        }
        /* Prevent caret/cursor and focus on headings and labels */
        .main-header, .sub-header, label, .metric-label, .company-name, .company-detail, .stMarkdown, .stText, h1, h2, h3, h4, h5, h6, .st-expanderHeader, b, strong {
            user-select: none !important;
            caret-color: transparent !important;
        }
        .st-expanderHeader, .st-expanderHeader * {
            user-select: none !important;
            caret-color: transparent !important;
            outline: none !important;
        }
        .st-expanderHeader:focus, .st-expanderHeader *:focus {
            outline: none !important;
            caret-color: transparent !important;
        }
        /* Aggressively hide Streamlit's input helper text (e.g., 'Press Enter to apply') but keep the eye icon */
        .stTextInput [data-testid="stTextInputHelperText"],
        .stTextInput div[style*="absolute"]:not(:has(svg)) {
            display: none !important;
        }
    </style>
    """, unsafe_allow_html=True)

    # sidebar
    with st.sidebar:
        st.markdown("<div class='sub-header'>Filters</div>", unsafe_allow_html=True)
        
        # time range filter
        st.markdown("<div class='filter-section'>", unsafe_allow_html=True)
        months_back = st.slider("Lookback Period (Months)", min_value=1, max_value=12, value=3, step=1)
        st.markdown("</div>", unsafe_allow_html=True)
        
        # industry filter
        st.markdown("<div class='filter-section'>", unsafe_allow_html=True)
        industries = db_manager.get_industries()
        if not industries:
            industries = [
                "Technology", "Healthcare", "Finance", "Education", "Retail",
                "Energy", "Transportation", "Real Estate", "Media", "Food & Beverage"
            ]
        selected_industries = st.multiselect("Industries", options=industries, default=None)
        st.markdown("</div>", unsafe_allow_html=True)
        
        # location filter
        st.markdown("<div class='filter-section'>", unsafe_allow_html=True)
        locations = [
            "Bengaluru", "Mumbai", "Delhi", "Hyderabad", "Chennai",
            "Pune", "Gurugram", "Noida", "Kolkata", "Ahmedabad"
        ]
        selected_locations = st.multiselect("Locations", options=locations, default=None)
        st.markdown("</div>", unsafe_allow_html=True)
        
        # funding round filter
        st.markdown("<div class='filter-section'>", unsafe_allow_html=True)
        funding_rounds = db_manager.get_funding_rounds()
        if not funding_rounds:
            funding_rounds = [
                "Seed", "Pre-Seed", "Series A", "Series B", "Series C",
                "Series D", "Series E", "Angel", "Venture", "Private Equity"
            ]
        selected_funding_rounds = st.multiselect("Funding Rounds", options=funding_rounds, default=None)
        st.markdown("</div>", unsafe_allow_html=True)
        
        # data collection section
        st.markdown("<div class='sub-header'>Data Collection</div>", unsafe_allow_html=True)
        
        with st.expander("Collect New Data"):
            perplexity_api_key = st.text_input("Perplexity API Key", type="password")
            
            st.markdown("### Automated Data Collection Sources")
            
            # default sources
            default_sources = [
                {"name": "TechCrunch", "url": "https://techcrunch.com/category/venture/"},
                {"name": "VentureBeat", "url": "https://venturebeat.com/category/venture/"}
            ]
            
            # load saved sources if available
            sources_file = os.path.join(os.getcwd(), "data", "sources.json")
            if os.path.exists(sources_file):
                with open(sources_file, "r") as f:
                    try:
                        saved_sources = json.load(f)
                        if saved_sources:
                            default_sources = saved_sources
                    except:
                        pass
            
            # create input fields for sources
            sources = []
            for i in range(5):  # allow up to 5 sources
                col1, col2 = st.columns([1, 2])
                with col1:
                    source_name = st.text_input(
                        f"Source {i+1} Name",
                        value=default_sources[i]["name"] if i < len(default_sources) else "",
                        key=f"source_name_{i}"
                    )
                with col2:
                    source_url = st.text_input(
                        f"Source {i+1} URL",
                        value=default_sources[i]["url"] if i < len(default_sources) else "",
                        key=f"source_url_{i}"
                    )
                
                if source_name and source_url:
                    sources.append({"name": source_name, "url": source_url})
            
            # collection options
            use_perplexity = st.checkbox("Use Perplexity API", value=True)
            use_web_scraping = st.checkbox("Use Automated Data Collection", value=True)
            use_browser = st.checkbox("Use Browser for Data Collection (slower but more robust)", value=True)
            
            if st.button("Collect Data"):
                if not use_perplexity and not use_web_scraping:
                    st.error("Please select at least one data collection method.")
                else:
                    with st.spinner("Collecting data..."):
                        # save sources for future use
                        os.makedirs(os.path.dirname(sources_file), exist_ok=True)
                        with open(sources_file, "w") as f:
                            json.dump(sources, f)
                        
                        # initialize orchestrator
                        orchestrator = DataCollectionOrchestrator()
                        
                        # register collectors
                        if use_perplexity and perplexity_api_key:
                            orchestrator.register_perplexity_collector(perplexity_api_key)
                        
                        if use_web_scraping and sources:
                            orchestrator.register_web_scraping_collector(sources)
                        
                        # collect data
                        startups = orchestrator.collect_from_all_sources(
                            months_back=months_back,
                            industries=selected_industries if selected_industries else None,
                            locations=selected_locations if selected_locations else None,
                            funding_rounds=selected_funding_rounds if selected_funding_rounds else None,
                            use_browser=use_browser
                        )
                        
                        # deduplicate
                        startups = orchestrator.deduplicate_startups(startups)
                        
                        # If using Perplexity, store in session and display directly
                        if use_perplexity:
                            st.session_state['perplexity_startups'] = startups
                            st.success(f"Successfully collected {len(startups)} startups from Perplexity API!")
                        else:
                            db_manager.save_startup_data(startups)
                            st.success(f"Successfully collected {len(startups)} startups!")

    # main content
    st.markdown("<div class='main-header'>🚀 Venture-Watch</div>", unsafe_allow_html=True)
    st.markdown("Discover recently funded startups that might be looking to expand their teams.")

    # Initialize session state if needed
    if 'current_startups' not in st.session_state:
        # Try loading from the JSON file first
        try:
            with open("startup_funding_data.json", "r", encoding='utf-8') as f:
                data = json.load(f)
                st.session_state['current_startups'] = data.get("startups", [])
                st.session_state['show_cached'] = True
        except (FileNotFoundError, json.JSONDecodeError):
            st.session_state['current_startups'] = []
            st.session_state['show_cached'] = False

    # Load historical data from database
    existing_startups = db_manager.get_startups(
        months_back=months_back,
        industries=selected_industries if selected_industries else None,
        locations=selected_locations if selected_locations else None,
        funding_rounds=selected_funding_rounds if selected_funding_rounds else None,
        limit=1000
    )
    
    # Convert existing startups to list of dicts if any found
    if existing_startups:
        historical_data = [s.__dict__ for s in existing_startups]
        # Merge with current startups if any
        if 'current_startups' in st.session_state:
            # Use a set to track unique names
            seen_names = set()
            merged_startups = []
            
            # Add current startups first
            for startup in st.session_state['current_startups']:
                name = startup.get('name') or startup.get('company_name')
                if name and name not in seen_names:
                    seen_names.add(name)
                    merged_startups.append(startup)
            
            # Add historical startups if not already present
            for startup in historical_data:
                name = startup.get('name') or startup.get('company_name')
                if name and name not in seen_names:
                    seen_names.add(name)
                    merged_startups.append(startup)
            
            st.session_state['current_startups'] = merged_startups

    # Display data section
    if st.session_state.get('current_startups'):
        display_data = st.session_state['current_startups']
        
        # Debug information
        st.sidebar.info(f"Number of startups in memory: {len(display_data)}")
        
        # Create DataFrame for display
        df_data = []
        for startup in display_data:
            # Normalize the data structure
            company_data = {
                "Company": startup.get('name') or startup.get('company_name', 'N/A'),
                "Industry": startup.get('industry', 'N/A'),
                "Location": startup.get('location', 'N/A'),
                "Funding Amount": startup.get('funding_amount', 'N/A'),
                "Round": startup.get('funding_round', 'N/A'),
                "Description": startup.get('description', 'N/A'),
                "Funding Date": startup.get('funding_date'),
                "Website": startup.get('company_website') or startup.get('company_url', 'N/A'),
                "Investors": ", ".join(startup.get('investors', [])[:2]) + ("..." if len(startup.get('investors', [])) > 2 else "")
            }
            df_data.append(company_data)
        
        df = pd.DataFrame(df_data)
        
        # Display all three tabs
        tab1, tab2, tab3 = st.tabs(["📊 Analytics", "📋 Startup List", "👥 Company Profiles"])
        
        with tab1:
            st.markdown("<div class='sub-header'>Funding Analytics</div>", unsafe_allow_html=True)
            
            col1, col2 = st.columns(2)
            
            with col1:
                # Industry distribution
                if 'Industry' in df.columns:
                    industry_counts = df['Industry'].value_counts()
                    st.subheader("Top Industries")
                    st.bar_chart(industry_counts)
            
            with col2:
                # Funding rounds distribution
                if 'Round' in df.columns:
                    round_counts = df['Round'].value_counts()
                    st.subheader("Funding Rounds")
                    st.bar_chart(round_counts)
        
        with tab2:
            # Add search and filter options
            search = st.text_input("🔍 Search startups by name, industry, or location")
            
            filtered_df = df
            if search:
                search = search.lower()
                filtered_df = df[
                    df['Company'].str.lower().str.contains(search, na=False) |
                    df['Industry'].str.lower().str.contains(search, na=False) |
                    df['Location'].str.lower().str.contains(search, na=False)
                ]
            
            st.markdown("<div class='sub-header'>Startup List</div>", unsafe_allow_html=True)
            st.info(f"Showing {len(filtered_df)} startups")
            
            # Display startups in cards
            for _, row in filtered_df.iterrows():
                with st.container():
                    st.markdown("<div class='company-card'>", unsafe_allow_html=True)
                    col1, col2 = st.columns([3, 1])
                    
                    with col1:
                        st.markdown(f"<div class='company-name'>{row['Company']}</div>", unsafe_allow_html=True)
                    with col2:
                        if row['Funding Amount'] != 'N/A':
                            st.markdown(f"<div class='company-funding'>{row['Funding Amount']}</div>", unsafe_allow_html=True)
                    
                    if row['Description'] != 'N/A':
                        st.markdown(f"<div class='company-detail'>{row['Description'][:200]}...</div>", unsafe_allow_html=True)
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.markdown(f"<div class='company-detail'><strong>Industry:</strong> {row['Industry']}</div>", unsafe_allow_html=True)
                    with col2:
                        st.markdown(f"<div class='company-detail'><strong>Location:</strong> {row['Location']}</div>", unsafe_allow_html=True)
                    with col3:
                        st.markdown(f"<div class='company-detail'><strong>Round:</strong> {row['Round']}</div>", unsafe_allow_html=True)
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        if row['Investors'] != 'N/A':
                            st.markdown(f"<div class='company-detail'><strong>Investors:</strong> {row['Investors']}</div>", unsafe_allow_html=True)
                    with col2:
                        if row['Website'] != 'N/A':
                            st.markdown(f"<div class='company-detail'><strong>Website:</strong> <a href='{row['Website']}' target='_blank'>Visit</a></div>", unsafe_allow_html=True)
                    
                    st.markdown("</div>", unsafe_allow_html=True)
        
        with tab3:
            st.markdown("<div class='sub-header'>Company Profiles</div>", unsafe_allow_html=True)
            
            # Add company selector
            selected_company = st.selectbox("Select a company to view detailed profile", df['Company'].tolist())
            
            if selected_company:
                company_data = df[df['Company'] == selected_company].iloc[0]
                
                st.markdown(f"<div class='main-header'>{selected_company}</div>", unsafe_allow_html=True)
                
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    st.markdown("### About")
                    st.write(company_data['Description'])
                    
                    st.markdown("### Funding Details")
                    st.write(f"**Amount:** {company_data['Funding Amount']}")
                    st.write(f"**Round:** {company_data['Round']}")
                    if company_data['Investors'] != 'N/A':
                        st.write(f"**Investors:** {company_data['Investors']}")
                
                with col2:
                    st.markdown("### Company Information")
                    st.write(f"**Industry:** {company_data['Industry']}")
                    st.write(f"**Location:** {company_data['Location']}")
                    if company_data['Website'] != 'N/A':
                        st.write(f"**Website:** [{company_data['Website']}]({company_data['Website']})")
    else:
        st.info("No startups found. Use the sidebar to collect data.")

    # footer
    st.markdown("<div class='footer'>Venture-Watch - Find your next opportunity</div>", unsafe_allow_html=True)
