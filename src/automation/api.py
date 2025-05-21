"""
API endpoints for workflow automation integration with n8n/Zapier.
"""
import logging
import os
from datetime import datetime
from typing import List, Dict, Any, Optional

from fastapi import FastAPI, HTTPException, Depends, Query, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from src.data_collection.orchestrator import DataCollectionOrchestrator
from src.data_collection.perplexity_collector import PerplexityCollector
from src.data_collection.web_scraping_collector import WebScrapingCollector
from src.data_storage.database import DatabaseManager
from src.linkedin.enricher import LinkedInEnricher

logger = logging.getLogger(__name__)

# initialize FastAPI app
app = FastAPI(
    title="Startup Finder API",
    description="API for integrating Startup Finder with workflow automation tools like n8n and Zapier",
    version="1.0.0"
)

# add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, this should be restricted
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# models for API requests and responses
class StartupBase(BaseModel):
    name: str
    description: Optional[str] = None
    funding_amount: Optional[str] = None
    funding_round: Optional[str] = None
    funding_date: Optional[str] = None
    investors: Optional[List[str]] = None
    industry: Optional[str] = None
    location: Optional[str] = None
    company_size: Optional[str] = None
    company_url: Optional[str] = None
    linkedin_url: Optional[str] = None
    source: Optional[str] = None
    source_url: Optional[str] = None

class StartupCreate(StartupBase):
    pass

class StartupResponse(StartupBase):
    id: int
    created_at: str
    updated_at: str
    key_people: Optional[List[Dict[str, str]]] = None

class WebScrapingSource(BaseModel):
    name: str
    url: str

class DataCollectionRequest(BaseModel):
    months_back: int = 3
    industries: Optional[List[str]] = None
    locations: Optional[List[str]] = None
    funding_rounds: Optional[List[str]] = None
    use_perplexity: bool = True
    perplexity_api_key: Optional[str] = None
    use_web_scraping: bool = True
    web_scraping_sources: Optional[List[WebScrapingSource]] = None
    use_browser: bool = True

class DataCollectionResponse(BaseModel):
    success: bool
    message: str
    startups_collected: int = 0

class LinkedInEnrichmentRequest(BaseModel):
    startup_ids: Optional[List[int]] = None
    use_browser: bool = True
    headless: bool = True

class LinkedInEnrichmentResponse(BaseModel):
    success: bool
    message: str
    startups_enriched: int = 0

# dependencies
def get_db_manager():
    """get database manager instance."""
    db_path = os.path.join(os.getcwd(), "data", "startups.db")
    return DatabaseManager(f"sqlite:///{db_path}")

# API endpoints
@app.get("/", tags=["Root"])
async def root():
    """Root endpoint to check if API is running."""
    return {"message": "Startup Finder API is running"}

@app.get("/startups", response_model=List[StartupResponse], tags=["Startups"])
async def get_startups(
    db_manager: DatabaseManager = Depends(get_db_manager),
    months_back: int = Query(3, description="Number of months to look back"),
    industries: Optional[List[str]] = Query(None, description="List of industries to filter by"),
    locations: Optional[List[str]] = Query(None, description="List of locations to filter by"),
    funding_rounds: Optional[List[str]] = Query(None, description="List of funding rounds to filter by"),
    limit: int = Query(100, description="Maximum number of results"),
    offset: int = Query(0, description="Offset for pagination")
):
    """Get startups with filtering."""
    startups = db_manager.get_startups(
        months_back=months_back,
        industries=industries,
        locations=locations,
        funding_rounds=funding_rounds,
        limit=limit,
        offset=offset
    )
    return startups

@app.get("/startups/{startup_id}", response_model=StartupResponse, tags=["Startups"])
async def get_startup(
    startup_id: int,
    db_manager: DatabaseManager = Depends(get_db_manager)
):
    """Get a startup by ID."""
    startup = db_manager.get_startup_by_id(startup_id)
    if not startup:
        raise HTTPException(status_code=404, detail="Startup not found")
    return startup

@app.post("/startups", response_model=StartupResponse, tags=["Startups"])
async def create_startup(
    startup: StartupCreate,
    db_manager: DatabaseManager = Depends(get_db_manager)
):
    """Create a new startup."""
    from src.data_collection.base import StartupData
    
    # convert to StartupData
    funding_date = None
    if startup.funding_date:
        try:
            funding_date = datetime.fromisoformat(startup.funding_date)
        except ValueError:
            pass
    
    startup_data = StartupData(
        name=startup.name,
        description=startup.description or "",
        funding_amount=startup.funding_amount,
        funding_round=startup.funding_round,
        funding_date=funding_date,
        investors=startup.investors or [],
        industry=startup.industry,
        location=startup.location,
        company_size=startup.company_size,
        company_url=startup.company_url,
        linkedin_url=startup.linkedin_url,
        source=startup.source,
        source_url=startup.source_url
    )
    
    # save to database
    db_manager.save_startup_data(startup_data)
    
    # get the saved startup
    saved_startup = db_manager.get_startup_by_name(startup.name)
    if not saved_startup:
        raise HTTPException(status_code=500, detail="Failed to save startup")
    
    return saved_startup

@app.post("/collect", response_model=DataCollectionResponse, tags=["Data Collection"])
async def collect_data(
    request: DataCollectionRequest,
    db_manager: DatabaseManager = Depends(get_db_manager)
):
    """Collect startup data from various sources."""
    try:
        # initialize orchestrator
        orchestrator = DataCollectionOrchestrator()
        
        # register collectors
        if request.use_perplexity and request.perplexity_api_key:
            orchestrator.register_perplexity_collector(request.perplexity_api_key)
        
        if request.use_web_scraping and request.web_scraping_sources:
            sources = [
                {"name": source.name, "url": source.url}
                for source in request.web_scraping_sources
            ]
            orchestrator.register_web_scraping_collector(sources)
        
        # collect data
        startups = orchestrator.collect_from_all_sources(
            months_back=request.months_back,
            industries=request.industries,
            locations=request.locations,
            funding_rounds=request.funding_rounds,
            use_browser=request.use_browser
        )
        
        # deduplicate
        startups = orchestrator.deduplicate_startups(startups)
        
        # save to database
        db_manager.save_startup_data(startups)
        
        return {
            "success": True,
            "message": f"Successfully collected {len(startups)} startups",
            "startups_collected": len(startups)
        }
    
    except Exception as e:
        logger.error(f"Error collecting data: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/enrich", response_model=LinkedInEnrichmentResponse, tags=["LinkedIn Enrichment"])
async def enrich_startups(
    request: LinkedInEnrichmentRequest,
    db_manager: DatabaseManager = Depends(get_db_manager)
):
    """Enrich startups with LinkedIn information."""
    try:
        # get startups to enrich
        if request.startup_ids:
            startups_data = []
            for startup_id in request.startup_ids:
                startup = db_manager.get_startup_by_id(startup_id)
                if startup:
                    # convert to StartupData
                    from src.data_collection.base import StartupData
                    
                    funding_date = None
                    if startup.get("funding_date"):
                        try:
                            funding_date = datetime.fromisoformat(startup["funding_date"])
                        except ValueError:
                            pass
                    
                    startup_data = StartupData(
                        name=startup["name"],
                        description=startup.get("description", ""),
                        funding_amount=startup.get("funding_amount"),
                        funding_round=startup.get("funding_round"),
                        funding_date=funding_date,
                        investors=startup.get("investors", []),
                        industry=startup.get("industry"),
                        location=startup.get("location"),
                        company_size=startup.get("company_size"),
                        company_url=startup.get("company_url"),
                        linkedin_url=startup.get("linkedin_url"),
                        source=startup.get("source"),
                        source_url=startup.get("source_url"),
                        key_people=startup.get("key_people", [])
                    )
                    
                    startups_data.append(startup_data)
        else:
            # get all startups without LinkedIn info
            all_startups = db_manager.get_startups(limit=1000)
            startups_data = []
            
            for startup in all_startups:
                if not startup.get("linkedin_url") or not startup.get("key_people"):
                    # convert to StartupData
                    from src.data_collection.base import StartupData
                    
                    funding_date = None
                    if startup.get("funding_date"):
                        try:
                            funding_date = datetime.fromisoformat(startup["funding_date"])
                        except ValueError:
                            pass
                    
                    startup_data = StartupData(
                        name=startup["name"],
                        description=startup.get("description", ""),
                        funding_amount=startup.get("funding_amount"),
                        funding_round=startup.get("funding_round"),
                        funding_date=funding_date,
                        investors=startup.get("investors", []),
                        industry=startup.get("industry"),
                        location=startup.get("location"),
                        company_size=startup.get("company_size"),
                        company_url=startup.get("company_url"),
                        linkedin_url=startup.get("linkedin_url"),
                        source=startup.get("source"),
                        source_url=startup.get("source_url"),
                        key_people=startup.get("key_people", [])
                    )
                    
                    startups_data.append(startup_data)
        
        # enrich startups
        with LinkedInEnricher(use_browser=request.use_browser, headless=request.headless) as enricher:
            enriched_startups = enricher.enrich_startups(startups_data)
        
        # save enriched startups
        db_manager.save_startup_data(enriched_startups)
        
        return {
            "success": True,
            "message": f"Successfully enriched {len(enriched_startups)} startups",
            "startups_enriched": len(enriched_startups)
        }
    
    except Exception as e:
        logger.error(f"Error enriching startups: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/analytics/industries", tags=["Analytics"])
async def get_industry_analytics(
    db_manager: DatabaseManager = Depends(get_db_manager),
    limit: int = Query(10, description="Maximum number of industries to return")
):
    """Get startup counts grouped by industry."""
    return db_manager.get_startups_by_industry(limit=limit)

@app.get("/analytics/locations", tags=["Analytics"])
async def get_location_analytics(
    db_manager: DatabaseManager = Depends(get_db_manager),
    limit: int = Query(10, description="Maximum number of locations to return")
):
    """Get startup counts grouped by location."""
    return db_manager.get_startups_by_location(limit=limit)

@app.get("/analytics/funding-rounds", tags=["Analytics"])
async def get_funding_round_analytics(
    db_manager: DatabaseManager = Depends(get_db_manager)
):
    """Get startup counts grouped by funding round."""
    return db_manager.get_startups_by_funding_round()

@app.get("/analytics/monthly", tags=["Analytics"])
async def get_monthly_analytics(
    db_manager: DatabaseManager = Depends(get_db_manager),
    months_back: int = Query(12, description="Number of months to look back")
):
    """Get startup counts grouped by month."""
    return db_manager.get_startups_by_month(months_back=months_back)

# run the API with uvicorn
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
