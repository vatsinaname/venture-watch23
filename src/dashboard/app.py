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
                        
                        # save to database
                        db_manager.save_startup_data(startups)
                        
                        st.success(f"Successfully collected {len(startups)} startups!")

    # main content
    st.markdown("<div class='main-header'>🚀 Venture-Watch</div>", unsafe_allow_html=True)
    st.markdown("Discover recently funded startups that might be looking to expand their teams.")

    # get filtered startups
    startups = db_manager.get_startups(
        months_back=months_back,
        industries=selected_industries if selected_industries else None,
        locations=selected_locations if selected_locations else None,
        funding_rounds=selected_funding_rounds if selected_funding_rounds else None,
        limit=1000  # High limit for analytics
    )

    # convert to DataFrame for easier manipulation
    if startups:
        df = pd.DataFrame(startups)
        
        # convert funding_date to datetime
        df['funding_date'] = pd.to_datetime(df['funding_date'])
        
        # dashboard metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.markdown("<div class='card'>", unsafe_allow_html=True)
            st.markdown(f"<div class='metric-value'>{len(df)}</div>", unsafe_allow_html=True)
            st.markdown("<div class='metric-label'>Startups Found</div>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)
            
        with col2:
            unique_industries = df['industry'].dropna().nunique()
            st.markdown("<div class='card'>", unsafe_allow_html=True)
            st.markdown(f"<div class='metric-value'>{unique_industries}</div>", unsafe_allow_html=True)
            st.markdown("<div class='metric-label'>Industries</div>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)
            
        with col3:
            unique_locations = df['location'].dropna().nunique()
            st.markdown("<div class='card'>", unsafe_allow_html=True)
            st.markdown(f"<div class='metric-value'>{unique_locations}</div>", unsafe_allow_html=True)
            st.markdown("<div class='metric-label'>Locations</div>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)
            
        with col4:
            latest_funding = df['funding_date'].max()
            days_ago = (datetime.now() - latest_funding).days if not pd.isna(latest_funding) else "N/A"
            st.markdown("<div class='card'>", unsafe_allow_html=True)
            st.markdown(f"<div class='metric-value'>{days_ago if days_ago != 'N/A' else 'N/A'}</div>", unsafe_allow_html=True)
            st.markdown("<div class='metric-label'>Days Since Latest Funding</div>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)
        
        # tabs for different views
        tab1, tab2, tab3 = st.tabs(["Analytics", "Startup List", "Company Profiles"])
        
        with tab1:
            st.markdown("<div class='sub-header'>Funding Analytics</div>", unsafe_allow_html=True)
            
            # row 1: time series and industry breakdown
            col1, col2 = st.columns(2)
            
            with col1:
                # time series of funding events
                if not df['funding_date'].isna().all():
                    # group by month and count
                    df_time = df.copy()
                    df_time['month'] = df_time['funding_date'].dt.strftime('%Y-%m')
                    monthly_counts = df_time.groupby('month').size().reset_index(name='count')
                    
                    fig = px.line(
                        monthly_counts, 
                        x='month', 
                        y='count',
                        title='Funding Events Over Time',
                        labels={'month': 'Month', 'count': 'Number of Startups'},
                        markers=True
                    )
                    fig.update_layout(
                        xaxis_title='Month',
                        yaxis_title='Number of Startups',
                        height=400
                    )
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("No time data available for visualization.")
            
            with col2:
                # industry breakdown
                if 'industry' in df.columns and not df['industry'].isna().all():
                    industry_counts = df['industry'].value_counts().reset_index()
                    industry_counts.columns = ['industry', 'count']
                    industry_counts = industry_counts.sort_values('count', ascending=True).tail(10)
                    
                    fig = px.bar(
                        industry_counts,
                        y='industry',
                        x='count',
                        title='Top Industries',
                        labels={'industry': 'Industry', 'count': 'Number of Startups'},
                        orientation='h'
                    )
                    fig.update_layout(
                        xaxis_title='Number of Startups',
                        yaxis_title='Industry',
                        height=400
                    )
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("No industry data available for visualization.")
            
            # row 2: location and funding round breakdown
            col1, col2 = st.columns(2)
            
            with col1:
                # Location breakdown
                if 'location' in df.columns and not df['location'].isna().all():
                    location_counts = df['location'].value_counts().reset_index()
                    location_counts.columns = ['location', 'count']
                    location_counts = location_counts.sort_values('count', ascending=True).tail(10)
                    
                    fig = px.bar(
                        location_counts,
                        y='location',
                        x='count',
                        title='Top Locations',
                        labels={'location': 'Location', 'count': 'Number of Startups'},
                        orientation='h'
                    )
                    fig.update_layout(
                        xaxis_title='Number of Startups',
                        yaxis_title='Location',
                        height=400
                    )
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("No location data available for visualization.")
            
            with col2:
                # funding round breakdown
                if 'funding_round' in df.columns and not df['funding_round'].isna().all():
                    round_counts = df['funding_round'].value_counts().reset_index()
                    round_counts.columns = ['funding_round', 'count']
                    
                    fig = px.pie(
                        round_counts,
                        values='count',
                        names='funding_round',
                        title='Funding Rounds Distribution',
                        hole=0.4
                    )
                    fig.update_layout(height=400)
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("No funding round data available for visualization.")
        
        with tab2:
            st.markdown("<div class='sub-header'>Startup List</div>", unsafe_allow_html=True)
            
            # search box
            search_query = st.text_input("Search startups by name, description, or industry")
            
            # filter by search query if provided
            filtered_df = df
            if search_query:
                search_query = search_query.lower()
                filtered_df = df[
                    df['name'].str.lower().str.contains(search_query, na=False) |
                    df['description'].str.lower().str.contains(search_query, na=False) |
                    df['industry'].str.lower().str.contains(search_query, na=False)
                ]
            
            # sort options
            sort_options = {
                "Most Recent Funding": "funding_date",
                "Company Name (A-Z)": "name",
                "Industry (A-Z)": "industry"
            }
            sort_by = st.selectbox("Sort by", options=list(sort_options.keys()))
            sort_column = sort_options[sort_by]
            
            # sort the dataframe
            if sort_column == "funding_date":
                filtered_df = filtered_df.sort_values(sort_column, ascending=False)
            else:
                filtered_df = filtered_df.sort_values(sort_column)
            
            # display startups
            if len(filtered_df) > 0:
                for _, row in filtered_df.iterrows():
                    st.markdown("<div class='company-card'>", unsafe_allow_html=True)
                    
                    # company name and funding
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.markdown(f"<div class='company-name'>{row['name']}</div>", unsafe_allow_html=True)
                    with col2:
                        if row['funding_amount']:
                            st.markdown(f"<div class='company-funding'>{row['funding_amount']}</div>", unsafe_allow_html=True)
                    
                    # company details
                    if row['description']:
                        st.markdown(f"<div class='company-detail'>{row['description'][:200]}{'...' if len(row['description']) > 200 else ''}</div>", unsafe_allow_html=True)
                    
                    # metadata row
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        if row['industry']:
                            st.markdown(f"<div class='company-detail'><strong>Industry:</strong> {row['industry']}</div>", unsafe_allow_html=True)
                    with col2:
                        if row['location']:
                            st.markdown(f"<div class='company-detail'><strong>Location:</strong> {row['location']}</div>", unsafe_allow_html=True)
                    with col3:
                        if row['funding_round']:
                            st.markdown(f"<div class='company-detail'><strong>Round:</strong> {row['funding_round']}</div>", unsafe_allow_html=True)
                    
                    # funding date and links
                    col1, col2 = st.columns([1, 1])
                    with col1:
                        if not pd.isna(row['funding_date']):
                            funding_date = row['funding_date'].strftime('%Y-%m-%d')
                            st.markdown(f"<div class='company-detail'><strong>Funding Date:</strong> {funding_date}</div>", unsafe_allow_html=True)
                    with col2:
                        links = []
                        if row['company_url']:
                            links.append(f"<a href='{row['company_url']}' target='_blank'>Website</a>")
                        if row['linkedin_url']:
                            links.append(f"<a href='{row['linkedin_url']}' target='_blank'>LinkedIn</a>")
                        if row['source_url']:
                            links.append(f"<a href='{row['source_url']}' target='_blank'>Source</a>")
                        
                        if links:
                            st.markdown(f"<div class='company-detail'><strong>Links:</strong> {' | '.join(links)}</div>", unsafe_allow_html=True)
                    
                    # view details button
                    if st.button(f"View Details", key=f"view_{row['id']}"):
                        st.session_state.selected_startup = row['id']
                        st.experimental_rerun()
                    
                    st.markdown("</div>", unsafe_allow_html=True)
            else:
                st.info("No startups found matching your criteria.")
        
        with tab3:
            st.markdown("<div class='sub-header'>Company Profiles</div>", unsafe_allow_html=True)
            
            # check if a startup is selected
            if hasattr(st.session_state, 'selected_startup'):
                startup_id = st.session_state.selected_startup
                startup = db_manager.get_startup_by_id(startup_id)
                
                if startup:
                    # company header
                    st.markdown(f"<div class='main-header'>{startup['name']}</div>", unsafe_allow_html=True)
                    
                    # company details
                    col1, col2 = st.columns([2, 1])
                    
                    with col1:
                        st.markdown("### About")
                        st.write(startup['description'])
                        
                        st.markdown("### Funding Details")
                        funding_details = []
                        if startup['funding_amount']:
                            funding_details.append(f"**Amount:** {startup['funding_amount']}")
                        if startup['funding_round']:
                            funding_details.append(f"**Round:** {startup['funding_round']}")
                        if startup['funding_date']:
                            funding_date = datetime.fromisoformat(startup['funding_date']).strftime('%Y-%m-%d')
                            funding_details.append(f"**Date:** {funding_date}")
                        
                        if funding_details:
                            st.markdown(" | ".join(funding_details))
                        
                        if startup['investors'] and len(startup['investors']) > 0:
                            st.markdown("### Investors")
                            st.write(", ".join(startup['investors']))
                    
                    with col2:
                        st.markdown("### Company Information")
                        if startup['industry']:
                            st.markdown(f"**Industry:** {startup['industry']}")
                        if startup['location']:
                            st.markdown(f"**Location:** {startup['location']}")
                        if startup['company_size']:
                            st.markdown(f"**Company Size:** {startup['company_size']}")
                        
                        st.markdown("### Links")
                        if startup['company_url']:
                            st.markdown(f"[Company Website]({startup['company_url']})")
                        if startup['linkedin_url']:
                            st.markdown(f"[LinkedIn]({startup['linkedin_url']})")
                        if startup['source_url']:
                            st.markdown(f"[Funding Source]({startup['source_url']})")
                    
                    # key people section
                    if startup['key_people'] and len(startup['key_people']) > 0:
                        st.markdown("### Key People")
                        
                        for person in startup['key_people']:
                            col1, col2, col3 = st.columns([2, 2, 1])
                            with col1:
                                st.write(f"**{person['name']}**")
                            with col2:
                                if person['title']:
                                    st.write(person['title'])
                            with col3:
                                links = []
                                if person['linkedin_url']:
                                    links.append(f"[LinkedIn]({person['linkedin_url']})")
                                if person['email']:
                                    links.append(f"[Email](mailto:{person['email']})")
                                
                                if links:
                                    st.markdown(" | ".join(links))
                    
                    # back button
                    if st.button("Back to List"):
                        del st.session_state.selected_startup
                        st.experimental_rerun()
                else:
                    st.error("Startup not found.")
                    if st.button("Back to List"):
                        del st.session_state.selected_startup
                        st.experimental_rerun()
            else:
                st.info("Select a startup from the list to view detailed profile.")
    else:
        st.info("No startups found in the database. Use the sidebar to collect data.")

    # footer
    st.markdown("<div class='footer'>Venture-Watch - Find your next opportunity</div>", unsafe_allow_html=True)
