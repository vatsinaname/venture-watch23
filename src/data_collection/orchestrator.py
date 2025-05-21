"""
Data collection orchestrator that integrates multiple data sources.
"""
import logging
from typing import List, Dict, Any, Optional

from src.data_collection.base import DataCollector, StartupData
from src.data_collection.perplexity_collector import PerplexityCollector
from src.data_collection.web_scraping_collector import WebScrapingCollector

logger = logging.getLogger(__name__)


class DataCollectionOrchestrator:
    """
    Orchestrates data collection from multiple sources and combines results.
    """
    
    def __init__(self):
        """Initialize the data collection orchestrator."""
        self.collectors = {}
        
    def register_collector(self, name: str, collector: DataCollector) -> None:
        """
        Register a data collector.
        
        Args:
            name: Unique name for the collector
            collector: DataCollector instance
        """
        self.collectors[name] = collector
        logger.info(f"Registered collector: {name}")
        
    def register_perplexity_collector(self, api_key: str) -> None:
        """
        Register a Perplexity API collector.
        
        Args:
            api_key: Perplexity API key
        """
        collector = PerplexityCollector(api_key)
        self.register_collector("perplexity", collector)
        
    def register_web_scraping_collector(self, sources: List[Dict[str, str]]) -> None:
        """
        Register a web scraping collector.
        
        Args:
            sources: List of source configurations with 'name' and 'url' keys
        """
        collector = WebScrapingCollector(sources)
        self.register_collector("web_scraping", collector)
        
    def collect_from_all_sources(
        self, 
        months_back: int = 3,
        industries: Optional[List[str]] = None,
        locations: Optional[List[str]] = None,
        funding_rounds: Optional[List[str]] = None,
        use_browser: bool = True,
        **kwargs
    ) -> List[StartupData]:
        """
        Collect startup data from all registered sources.
        
        Args:
            months_back: Number of months to look back for funding news
            industries: List of industries to focus on
            locations: List of locations to focus on
            funding_rounds: List of funding rounds to focus on
            use_browser: Whether to use browser-based scraping for web sources
            **kwargs: Additional parameters passed to collectors
            
        Returns:
            Combined list of StartupData objects from all sources
        """
        all_startups = []
        
        for name, collector in self.collectors.items():
            try:
                logger.info(f"Collecting data from source: {name}")
                
                # Prepare parameters based on collector type
                if isinstance(collector, PerplexityCollector):
                    startups = collector.collect(
                        months_back=months_back,
                        industries=industries,
                        locations=locations,
                        funding_rounds=funding_rounds,
                        **kwargs
                    )
                elif isinstance(collector, WebScrapingCollector):
                    startups = collector.collect(
                        months_back=months_back,
                        use_browser=use_browser,
                        **kwargs
                    )
                else:
                    # Generic collector
                    startups = collector.collect(**kwargs)
                
                logger.info(f"Collected {len(startups)} startups from {name}")
                all_startups.extend(startups)
                
            except Exception as e:
                logger.error(f"Error collecting from {name}: {e}")
                continue
                
        return all_startups
    
    def collect_from_source(self, source_name: str, **kwargs) -> List[StartupData]:
        """
        Collect startup data from a specific source.
        
        Args:
            source_name: Name of the source to collect from
            **kwargs: Parameters passed to the collector
            
        Returns:
            List of StartupData objects from the specified source
        """
        if source_name not in self.collectors:
            logger.error(f"Source not found: {source_name}")
            return []
            
        try:
            collector = self.collectors[source_name]
            return collector.collect(**kwargs)
        except Exception as e:
            logger.error(f"Error collecting from {source_name}: {e}")
            return []
    
    def deduplicate_startups(self, startups: List[StartupData]) -> List[StartupData]:
        """
        Remove duplicate startup entries based on name similarity.
        
        Args:
            startups: List of StartupData objects
            
        Returns:
            Deduplicated list of StartupData objects
        """
        if not startups:
            return []
            
        # Simple deduplication based on exact name match
        # In a production system, this would use more sophisticated fuzzy matching
        unique_startups = {}
        
        for startup in startups:
            # Normalize name for comparison
            normalized_name = startup.name.lower().strip()
            
            if normalized_name in unique_startups:
                # If we already have this startup, merge any missing information
                existing = unique_startups[normalized_name]
                
                # Always prefer non-None values from the newer record
                # This ensures we get the most up-to-date information
                if startup.funding_amount:
                    existing.funding_amount = startup.funding_amount
                    
                if startup.funding_round:
                    existing.funding_round = startup.funding_round
                    
                if startup.funding_date:
                    existing.funding_date = startup.funding_date
                    
                if startup.investors:
                    existing.investors = startup.investors
                    
                if startup.industry:
                    existing.industry = startup.industry
                    
                if startup.location:
                    existing.location = startup.location
                    
                if startup.company_size:
                    existing.company_size = startup.company_size
                    
                if startup.company_url:
                    existing.company_url = startup.company_url
                    
                if startup.linkedin_url:
                    existing.linkedin_url = startup.linkedin_url
                    
                if startup.key_people:
                    existing.key_people = startup.key_people
                    
                # Update the source to indicate multiple sources
                if existing.source != startup.source:
                    existing.source = f"{existing.source}, {startup.source}"
                    
                # Keep the most recent updated_at timestamp
                if startup.updated_at > existing.updated_at:
                    existing.updated_at = startup.updated_at
            else:
                # New unique startup
                unique_startups[normalized_name] = startup
                
        return list(unique_startups.values())
