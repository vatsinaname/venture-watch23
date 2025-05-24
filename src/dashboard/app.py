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
            background-color: #1E1E1E;
            box-shadow: 0 0.125rem 0.25rem rgba(0, 0, 0, 0.2);
            margin-bottom: 0.5rem;  /* Reduced margin between cards */
            border-left: 4px solid #1E88E5;
        }
        .card-grid {
            display: grid;
            grid-template-columns: 2fr 1fr;
            gap: 1rem;
            align-items: start;
        }
        .right-aligned {
            text-align: right;
            justify-self: end;
        }
        .metadata-grid {
            display: grid;
            grid-template-columns: auto auto auto;
            gap: 0.5rem;
            margin-top: 0.5rem;
        }
        /* Remove white space between expanders */
        .streamlit-expanderHeader {
            margin-top: 0 !important;
            margin-bottom: 0 !important;
        }
        .streamlit-expanderContent {
            border-bottom: none !important;
        }
        /* Adjusting the background of even cards for better visibility */
        .company-card:nth-child(even) {
            background-color: #252525;
        }
    </style>
    """, unsafe_allow_html=True)

    # sidebar
    with st.sidebar:
        st.markdown("<div class='sub-header'>Controls</div>", unsafe_allow_html=True)
        
        # reset button
        if st.button("🔄 Reset Data"):
            st.session_state['current_startups'] = []
            st.session_state['show_cached'] = False
            if os.path.exists("startup_funding_data.json"):
                os.remove("startup_funding_data.json")
            st.success("Data reset successful! Click 'Search New Startups' to collect fresh data.")
            st.experimental_rerun()

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
            use_browser = st.checkbox("Use Browser for Data Collection (slower)", value=True)
            
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
                        
                        # ff using Perplexity, store in session and display directly
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
        
        # Update tab layout with new Analytics tabs
        tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 Overview", "📈 Funding Analysis", "🔍 Deep Insights", "🏢 Company Profiles", "📄 Raw Data"])
        
        with tab1:
            st.markdown("<div class='sub-header'>Funding Analytics</div>", unsafe_allow_html=True)
            
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
            
            # Charts
            col1, col2 = st.columns(2)
            
            with col1:
                if industries:
                    st.subheader("Industry Distribution")
                    industry_counts = pd.Series(industries).value_counts()
                    st.bar_chart(industry_counts)
                
                if locations:
                    st.subheader("Top Locations")
                    location_counts = pd.Series(locations).value_counts().head(10)
                    st.bar_chart(location_counts)
            
            with col2:
                rounds = [s.get("funding_round") for s in display_data if s.get("funding_round")]
                if rounds:
                    st.subheader("Funding Rounds")
                    round_counts = pd.Series(rounds).value_counts()
                    fig = px.pie(values=round_counts.values, names=round_counts.index)
                    st.plotly_chart(fig, use_container_width=True)
        
        with tab2:
            st.markdown("<div class='sub-header'>Funding Analysis</div>", unsafe_allow_html=True)
            
            # Funding amount distribution
            if display_data:
                col1, col2 = st.columns(2)
                
                with col1:
                    # Funding amount by round
                    funding_data = []
                    for startup in display_data:
                        amount = startup.get('funding_amount', '0')
                        # Convert amount to numeric, handling different formats
                        try:
                            amount = float(''.join(filter(str.isdigit, amount)))
                            round_type = startup.get('funding_round', 'Unknown')
                            funding_data.append({'Round': round_type, 'Amount': amount})
                        except ValueError:
                            continue
                    
                    if funding_data:
                        df_funding = pd.DataFrame(funding_data)
                        fig = px.box(df_funding, x='Round', y='Amount',
                                   title='Funding Amount Distribution by Round',
                                   template='plotly_dark')
                        st.plotly_chart(fig, use_container_width=True)
                
                with col2:
                    # Funding timeline
                    timeline_data = []
                    for startup in display_data:
                        if startup.get('funding_date'):
                            try:
                                date = pd.to_datetime(startup.get('funding_date'))
                                amount = float(''.join(filter(str.isdigit, startup.get('funding_amount', '0'))))
                                timeline_data.append({'Date': date, 'Amount': amount})
                            except:
                                continue
                    
                    if timeline_data:
                        df_timeline = pd.DataFrame(timeline_data)
                        fig = px.line(df_timeline.sort_values('Date'), 
                                    x='Date', y='Amount',
                                    title='Funding Amount Timeline',
                                    template='plotly_dark')
                        st.plotly_chart(fig, use_container_width=True)

        with tab3:
            st.markdown("<div class='sub-header'>Deep Insights</div>", unsafe_allow_html=True)
            
            if display_data:
                col1, col2 = st.columns(2)
                
                with col1:
                    # Industry-Location Heatmap
                    industry_location = []
                    for startup in display_data:
                        industry = startup.get('industry', 'Unknown')
                        location = startup.get('location', 'Unknown')
                        industry_location.append({'Industry': industry, 'Location': location})
                    
                    df_heatmap = pd.DataFrame(industry_location)
                    heatmap_data = pd.crosstab(df_heatmap['Industry'], df_heatmap['Location'])
                    
                    fig = px.imshow(heatmap_data,
                                   title='Industry-Location Distribution',
                                   template='plotly_dark',
                                   color_continuous_scale='Viridis')
                    st.plotly_chart(fig, use_container_width=True)
                
                with col2:
                    # Technology stack analysis
                    tech_stack = []
                    for startup in display_data:
                        techs = startup.get('technologies_used', [])
                        if isinstance(techs, list):
                            tech_stack.extend(techs)
                    
                    if tech_stack:
                        tech_counts = pd.Series(tech_stack).value_counts()
                        fig = px.treemap(names=tech_counts.index,
                                       parents=['Technology']*len(tech_counts),
                                       values=tech_counts.values,
                                       title='Technology Stack Distribution',
                                       template='plotly_dark')
                        st.plotly_chart(fig, use_container_width=True)
                
                # Additional metrics
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    # Average funding by industry
                    industry_funding = []
                    for startup in display_data:
                        try:
                            amount = float(''.join(filter(str.isdigit, startup.get('funding_amount', '0'))))
                            industry = startup.get('industry', 'Unknown')
                            industry_funding.append({'Industry': industry, 'Amount': amount})
                        except:
                            continue
                    
                    if industry_funding:
                        df_industry = pd.DataFrame(industry_funding)
                        avg_by_industry = df_industry.groupby('Industry')['Amount'].mean().sort_values(ascending=False)
                        fig = px.bar(x=avg_by_industry.index, y=avg_by_industry.values,
                                    title='Average Funding by Industry',
                                    template='plotly_dark')
                        st.plotly_chart(fig, use_container_width=True)
                
                with col2:
                    # Funding success rate by location
                    location_counts = pd.Series([s.get('location', 'Unknown') for s in display_data]).value_counts()
                    funded_locations = pd.Series([s.get('location', 'Unknown') for s in display_data if s.get('funding_amount')]).value_counts()
                    success_rate = (funded_locations / location_counts * 100).sort_values(ascending=True)
                    
                    fig = px.bar(x=success_rate.values, y=success_rate.index,
                                title='Funding Success Rate by Location (%)',
                                orientation='h',
                                template='plotly_dark')
                    st.plotly_chart(fig, use_container_width=True)
                
                with col3:
                    # Company size distribution
                    size_dist = pd.Series([s.get('company_size', 'Unknown') for s in display_data]).value_counts()
                    fig = px.pie(values=size_dist.values,
                               names=size_dist.index,
                               title='Company Size Distribution',
                               template='plotly_dark')
                    st.plotly_chart(fig, use_container_width=True)
        
        with tab4:
            st.markdown("<div class='sub-header'>Company Profiles</div>", unsafe_allow_html=True)
            
            # Detailed company profiles
            for startup in display_data:
                with st.expander(f"{startup.get('company_name')} - {startup.get('funding_amount', 'N/A')}"):
                    # Header section
                    col1, col2 = st.columns([2, 1])
                    with col1:
                        st.markdown(f"### {startup.get('company_name')}")
                        if startup.get('company_website'):
                            st.markdown(f"🌐 [Website]({startup.get('company_website')})")
                    with col2:
                        st.markdown(f"<div style='text-align: right;'><h3 style='color: #43a047;'>{startup.get('funding_amount', 'N/A')}</h3></div>", unsafe_allow_html=True)
                    
                    # Company Overview
                    st.markdown("#### 📝 Company Overview")
                    st.write(startup.get('description', 'No description available'))
                    
                    # Quick Info Grid
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.markdown("#### 🏢 Company Details")
                        st.write(f"**Industry:** {startup.get('industry', 'N/A')}")
                        st.write(f"**Location:** {startup.get('location', 'N/A')}")
                        st.write(f"**Size:** {startup.get('company_size', 'N/A')}")
                    
                    with col2:
                        st.markdown("#### 💰 Funding Details")
                        st.write(f"**Round:** {startup.get('funding_round', 'N/A')}")
                        st.write(f"**Date:** {startup.get('funding_date', 'N/A')}")
                        st.write(f"**Total Raised:** {startup.get('total_funding_raised_to_date', 'N/A')}")
                    
                    with col3:
                        st.markdown("#### 🔗 Links & Contact")
                        if startup.get('linkedin_page'):
                            st.markdown(f"[Company LinkedIn]({startup.get('linkedin_page')})")
                        if startup.get('email'):
                            st.markdown(f"📧 {startup.get('email')}")
                    
                    # Investors and Team
                    col1, col2 = st.columns(2)
                    with col1:
                        if startup.get('investors'):
                            st.markdown("#### 🤝 Investors")
                            for investor in startup.get('investors'):
                                st.markdown(f"• {investor}")
                    
                    with col2:
                        if startup.get('recruitment_linkedin_profiles'):
                            st.markdown("#### 👥 Recruitment Team")
                            for profile in startup.get('recruitment_linkedin_profiles'):
                                st.markdown(f"• [Team Member]({profile})")
                    
                    # Technical Details
                    if startup.get('technologies_used') or startup.get('key_products_services'):
                        st.markdown("#### 💻 Technical Stack & Products")
                        col1, col2 = st.columns(2)
                        with col1:
                            if startup.get('technologies_used'):
                                st.markdown("**Technologies:**")
                                st.write(", ".join(startup.get('technologies_used')))
                        with col2:
                            if startup.get('key_products_services'):
                                st.markdown("**Products/Services:**")
                                for product in startup.get('key_products_services'):
                                    st.markdown(f"• {product}")
                    
                    # Social Media Links
                    if startup.get('social_media_links'):
                        st.markdown("#### 📱 Social Media")
                        cols = st.columns(4)
                        for i, (platform, url) in enumerate(startup.get('social_media_links').items()):
                            cols[i].markdown(f"[{platform.capitalize()}]({url})")
        
        with tab5:
            # Raw JSON data display
            st.markdown("<div class='sub-header'>Raw Data</div>", unsafe_allow_html=True)
            
            # Show raw data
            st.json(display_data)
            
            # Download functionality
            if st.download_button(
                label="📥 Download JSON Data",
                data=json.dumps(display_data, indent=2),
                file_name="startup_funding_data.json",
                mime="application/json"
            ):
                st.success("✅ Download started!")

    # Update API key handling in the sidebar
    with st.sidebar:
        with st.expander("Collect New Data"):
            # Try to get API key from config first
            api_key = PERPLEXITY_API_KEY
            if not api_key:
                api_key = st.text_input("Perplexity API Key", type="password")
            else:
                st.success("✅ API Key loaded from configuration")
                if st.checkbox("Override API Key"):
                    api_key = st.text_input("New API Key", type="password")

if __name__ == "__main__":
    main()
