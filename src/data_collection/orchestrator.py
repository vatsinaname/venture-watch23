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
    ) -> List[Dict[str, Any]]:
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
            Combined list of startup dictionaries from all sources
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
                    # Ensure startups are in dictionary format
                    if startups and not isinstance(startups[0], dict):
                        startups = [s if isinstance(s, dict) else s.__dict__ for s in startups]
                elif isinstance(collector, WebScrapingCollector):
                    startups = collector.collect(
                        months_back=months_back,
                        use_browser=use_browser,
                        **kwargs
                    )
                    # Convert to dict if needed
                    if startups and not isinstance(startups[0], dict):
                        startups = [s if isinstance(s, dict) else s.__dict__ for s in startups]
                else:
                    # Generic collector
                    startups = collector.collect(**kwargs)
                    # Convert to dict if needed
                    if startups and not isinstance(startups[0], dict):
                        startups = [s if isinstance(s, dict) else s.__dict__ for s in startups]
                
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
    
    def deduplicate_startups(self, startups: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate startups based on company name."""
        seen = {}
        unique_startups = []
        
        for startup in startups:
            # Use dictionary access and handle potential missing keys
            normalized_name = startup.get('name', '').lower().strip()
            if not normalized_name:
                continue
                
            if normalized_name not in seen:
                seen[normalized_name] = startup
                unique_startups.append(startup)
            else:
                # If we have a duplicate, keep the one with more complete information
                existing = seen[normalized_name]
                if self._is_more_complete(startup, existing):
                    seen[normalized_name] = startup
                    # Replace in unique_startups
                    idx = unique_startups.index(existing)
                    unique_startups[idx] = startup
        
        return unique_startups

    def _is_more_complete(self, startup1: Dict[str, Any], startup2: Dict[str, Any]) -> bool:
        """Compare two startup dictionaries to determine which has more complete information."""
        fields_to_check = ['description', 'funding_amount', 'funding_round', 'funding_date', 
                          'investors', 'industry', 'location', 'company_size', 'company_website']
        
        score1 = sum(1 for field in fields_to_check if startup1.get(field))
        score2 = sum(1 for field in fields_to_check if startup2.get(field))
        
        return score1 > score2
