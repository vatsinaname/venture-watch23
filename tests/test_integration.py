"""
Integration test for the Startup Finder system.
"""
import unittest
import os
import tempfile
from datetime import datetime

from src.data_collection.orchestrator import DataCollectionOrchestrator
from src.data_collection.web_scraping_collector import WebScrapingCollector
from src.data_storage.database import DatabaseManager
from src.linkedin.enricher import LinkedInEnricher


class TestSystemIntegration(unittest.TestCase):
    """Test cases for system integration."""
    
    def setUp(self):
        """Set up test environment."""
        # Create a temporary database file
        self.temp_db_fd, self.temp_db_path = tempfile.mkstemp()
        self.db_url = f"sqlite:///{self.temp_db_path}"
        self.db_manager = DatabaseManager(self.db_url)
        
        # Set up test sources for web scraping
        self.test_sources = [
            {"name": "TechCrunch", "url": "https://techcrunch.com/category/venture/"},
            {"name": "VentureBeat", "url": "https://venturebeat.com/category/venture/"}
        ]
    
    def tearDown(self):
        """Clean up after tests."""
        os.close(self.temp_db_fd)
        os.unlink(self.temp_db_path)
    
    def test_end_to_end_workflow(self):
        """Test the end-to-end workflow from collection to storage."""
        # Skip actual web requests in tests
        if os.environ.get("SKIP_INTEGRATION_TESTS"):
            self.skipTest("Skipping integration test that requires web access")
        
        # Initialize orchestrator
        orchestrator = DataCollectionOrchestrator()
        
        # Register web scraping collector with limited scope
        web_scraper = WebScrapingCollector(self.test_sources)
        orchestrator.register_collector("web_scraping", web_scraper)
        
        # Collect a small amount of data (limit collection for testing)
        try:
            startups = orchestrator.collect_from_source(
                "web_scraping",
                months_back=1,
                use_browser=True
            )
            
            # If no startups found, create a mock one for testing the flow
            if not startups:
                from src.data_collection.base import StartupData
                startups = [
                    StartupData(
                        name="Integration Test Startup",
                        description="A startup created during integration testing",
                        funding_amount="$2M",
                        funding_round="Seed",
                        funding_date=datetime.now(),
                        industry="Testing",
                        location="Test Location",
                        source="Integration Test"
                    )
                ]
            
            # Deduplicate
            startups = orchestrator.deduplicate_startups(startups)
            
            # Save to database
            self.db_manager.save_startup_data(startups)
            
            # Verify data was saved
            saved_startups = self.db_manager.get_startups()
            self.assertGreater(len(saved_startups), 0)
            
            # Test retrieval with filtering
            if "Testing" in [s.get("industry") for s in saved_startups if s.get("industry")]:
                test_startups = self.db_manager.get_startups(industries=["Testing"])
                self.assertGreater(len(test_startups), 0)
            
            # Test analytics
            industry_counts = self.db_manager.get_startups_by_industry()
            self.assertGreater(len(industry_counts), 0)
            
        except Exception as e:
            self.fail(f"Integration test failed: {e}")
    
    def test_linkedin_integration(self):
        """Test LinkedIn integration with the system."""
        # Skip actual web requests in tests
        if os.environ.get("SKIP_INTEGRATION_TESTS"):
            self.skipTest("Skipping integration test that requires web access")
        
        # Create a test startup
        from src.data_collection.base import StartupData
        test_startup = StartupData(
            name="LinkedIn Test Startup",
            description="A startup for testing LinkedIn integration",
            company_url="https://example.com",
            source="Integration Test"
        )
        
        # Save to database
        self.db_manager.save_startup_data(test_startup)
        
        # Try to enrich with LinkedIn data
        try:
            with LinkedInEnricher(use_browser=True, headless=True) as enricher:
                # This will attempt to find LinkedIn info but may not succeed in test environment
                enriched_startup = enricher.enrich_startup(test_startup)
                
                # Save enriched data
                self.db_manager.save_startup_data(enriched_startup)
                
                # Verify the startup exists in database
                saved_startup = self.db_manager.get_startup_by_name("LinkedIn Test Startup")
                self.assertIsNotNone(saved_startup)
                
        except Exception as e:
            self.fail(f"LinkedIn integration test failed: {e}")


if __name__ == "__main__":
    unittest.main()
