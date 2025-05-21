"""
Test module for validating Startup Finder functionality.
"""
import unittest
import os
import json
from datetime import datetime, timedelta

from src.data_collection.base import StartupData
from src.data_collection.orchestrator import DataCollectionOrchestrator
from src.data_storage.database import DatabaseManager
from src.linkedin.enricher import LinkedInEnricher


class TestStartupFinder(unittest.TestCase):
    """Test cases for Startup Finder functionality."""
    
    def setUp(self):
        """Set up test environment."""
        # Use in-memory SQLite database for testing
        self.db_manager = DatabaseManager("sqlite:///:memory:")
        
        # Create test data
        self.test_startups = [
            StartupData(
                name="Test Startup 1",
                description="A test startup for unit testing",
                funding_amount="$1M",
                funding_round="Seed",
                funding_date=datetime.now() - timedelta(days=30),
                investors=["Test Investor 1", "Test Investor 2"],
                industry="Technology",
                location="San Francisco, CA",
                company_url="https://teststartup1.com",
                source="Test Source"
            ),
            StartupData(
                name="Test Startup 2",
                description="Another test startup",
                funding_amount="$5M",
                funding_round="Series A",
                funding_date=datetime.now() - timedelta(days=60),
                investors=["Test Investor 3"],
                industry="Healthcare",
                location="New York, NY",
                company_url="https://teststartup2.com",
                source="Test Source"
            )
        ]
    
    def test_database_storage_and_retrieval(self):
        """Test storing and retrieving startups from the database."""
        # Save test startups
        self.db_manager.save_startup_data(self.test_startups)
        
        # Retrieve all startups
        startups = self.db_manager.get_startups()
        
        # Check if we got the correct number of startups
        self.assertEqual(len(startups), 2)
        
        # Check if the data is correct
        self.assertEqual(startups[0]["name"], "Test Startup 1")
        self.assertEqual(startups[1]["name"], "Test Startup 2")
        
        # Test filtering by industry
        tech_startups = self.db_manager.get_startups(industries=["Technology"])
        self.assertEqual(len(tech_startups), 1)
        self.assertEqual(tech_startups[0]["name"], "Test Startup 1")
        
        # Test filtering by location
        ny_startups = self.db_manager.get_startups(locations=["New York, NY"])
        self.assertEqual(len(ny_startups), 1)
        self.assertEqual(ny_startups[0]["name"], "Test Startup 2")
        
        # Test filtering by funding round
        seed_startups = self.db_manager.get_startups(funding_rounds=["Seed"])
        self.assertEqual(len(seed_startups), 1)
        self.assertEqual(seed_startups[0]["name"], "Test Startup 1")
    
    def test_startup_deduplication(self):
        """Test deduplication of startups."""
        # Create duplicate startup with some different data
        duplicate_startup = StartupData(
            name="Test Startup 1",  # Same name
            description="Updated description",
            funding_amount="$1.5M",  # Different amount
            funding_round="Seed",
            funding_date=datetime.now() - timedelta(days=25),  # More recent date
            investors=["Test Investor 1", "Test Investor 2", "New Investor"],
            industry="Technology",
            location="San Francisco, CA",
            company_url="https://teststartup1.com",
            source="Another Source"
        )
        
        # Create orchestrator for deduplication
        orchestrator = DataCollectionOrchestrator()
        
        # Combine original and duplicate
        combined_startups = self.test_startups + [duplicate_startup]
        
        # Deduplicate
        deduplicated = orchestrator.deduplicate_startups(combined_startups)
        
        # Check if we have the correct number of startups
        self.assertEqual(len(deduplicated), 2)
        
        # Check if the duplicate was merged correctly
        for startup in deduplicated:
            if startup.name == "Test Startup 1":
                # Should have the updated values
                self.assertEqual(startup.funding_amount, "$1.5M")
                self.assertEqual(len(startup.investors), 3)
                self.assertIn("New Investor", startup.investors)
                self.assertEqual(startup.source, "Test Source, Another Source")
    
    def test_data_validation(self):
        """Test data validation and integrity."""
        # Test with missing required fields
        invalid_startup = StartupData(
            name="",  # Empty name
            description="Invalid startup"
        )
        
        # Save to database should still work but with empty name
        self.db_manager.save_startup_data(invalid_startup)
        
        # Retrieve and check - we should be able to find it by description
        startups = self.db_manager.get_startups(months_back=0)  # Get all startups
        
        # Look for our invalid startup by description
        found_invalid = False
        for startup in startups:
            if startup["description"] == "Invalid startup":
                found_invalid = True
                self.assertEqual(startup["name"], "")  # Name should be empty
        
        self.assertTrue(found_invalid, "Failed to find startup with empty name")
        
        # Test with very long text
        long_description = "A" * 10000  # 10,000 characters
        long_desc_startup = StartupData(
            name="Long Description Startup",
            description=long_description
        )
        
        # Save to database
        self.db_manager.save_startup_data(long_desc_startup)
        
        # Retrieve and check
        startup = self.db_manager.get_startup_by_name("Long Description Startup")
        self.assertIsNotNone(startup)
        self.assertEqual(len(startup["description"]), 10000)
    
    def test_analytics(self):
        """Test analytics functionality."""
        # Save test startups
        self.db_manager.save_startup_data(self.test_startups)
        
        # Test industry analytics
        industry_counts = self.db_manager.get_startups_by_industry()
        self.assertEqual(len(industry_counts), 2)
        self.assertIn("Technology", industry_counts)
        self.assertIn("Healthcare", industry_counts)
        self.assertEqual(industry_counts["Technology"], 1)
        self.assertEqual(industry_counts["Healthcare"], 1)
        
        # Test location analytics
        location_counts = self.db_manager.get_startups_by_location()
        self.assertEqual(len(location_counts), 2)
        self.assertIn("San Francisco, CA", location_counts)
        self.assertIn("New York, NY", location_counts)
        
        # Test funding round analytics
        round_counts = self.db_manager.get_startups_by_funding_round()
        self.assertEqual(len(round_counts), 2)
        self.assertIn("Seed", round_counts)
        self.assertIn("Series A", round_counts)
    
    def test_historical_tracking(self):
        """Test historical data tracking."""
        # Create startups with different dates
        recent_startup = StartupData(
            name="Recent Startup",
            description="A recent startup",
            funding_date=datetime.now() - timedelta(days=30)
        )
        
        old_startup = StartupData(
            name="Old Startup",
            description="An old startup",
            funding_date=datetime.now() - timedelta(days=120)  # 4 months old
        )
        
        # Save both startups
        self.db_manager.save_startup_data([recent_startup, old_startup])
        
        # Get startups from last 3 months
        recent_startups = self.db_manager.get_startups(months_back=3)
        self.assertEqual(len(recent_startups), 1)
        self.assertEqual(recent_startups[0]["name"], "Recent Startup")
        
        # Get all startups
        all_startups = self.db_manager.get_startups(months_back=0)  # No time filter
        self.assertEqual(len(all_startups), 2)
        
        # Test cleanup of old data
        removed_count = self.db_manager.clean_old_data(months_to_keep=3)
        self.assertEqual(removed_count, 1)  # Should remove the old startup
        
        # Verify old startup is gone
        remaining_startups = self.db_manager.get_startups(months_back=0)
        self.assertEqual(len(remaining_startups), 1)
        self.assertEqual(remaining_startups[0]["name"], "Recent Startup")


if __name__ == "__main__":
    unittest.main()
