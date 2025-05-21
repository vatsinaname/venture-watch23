"""
Perplexity API integration for collecting startup funding data.
"""
import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any

# replace the perplexipy import with direct requests
import requests

from src.data_collection.base import DataCollector, StartupData

logger = logging.getLogger(__name__)


class Perplexity:
    """Simple Perplexity API client using direct requests."""
    
    def __init__(self, api_key: str):
        """
        Initialize the Perplexity API client.
        
        Args:
            api_key: Perplexity API key
        """
        self.api_key = api_key
        self.base_url = "https://api.perplexity.ai/chat/completions"
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
    
    def query(self, query_text: str) -> Dict[str, Any]:
        """
        Send a query to the Perplexity API.
        
        Args:
            query_text: Query text
            
        Returns:
            Response from Perplexity API
        """
        payload = {
            "model": "sonar-medium-online",
            "messages": [
                {"role": "system", "content": "You are a helpful assistant that provides accurate information about startup funding."},
                {"role": "user", "content": query_text}
            ]
        }
        
        try:
            response = requests.post(self.base_url, headers=self.headers, json=payload)
            response.raise_for_status()
            data = response.json()
            
            # Extract the assistant's message content
            if "choices" in data and len(data["choices"]) > 0:
                content = data["choices"][0]["message"]["content"]
                return {"text": content}
            else:
                return {"text": "No response from Perplexity API"}
        except Exception as e:
            logger.error(f"Error querying Perplexity API: {e}")
            return {"text": f"Error: {str(e)}"}


class PerplexityCollector(DataCollector):
    """Collector that uses Perplexity API to find startup funding information."""
    
    def __init__(self, api_key: str):
        """
        Initialize the Perplexity API collector.
        
        Args:
            api_key: Perplexity API key
        """
        self.client = Perplexity(api_key=api_key)
        
    def get_source_name(self) -> str:
        """Get the name of the data source."""
        return "Perplexity API"
    
    def collect(
        self, 
        months_back: int = 3, 
        industries: Optional[List[str]] = None,
        locations: Optional[List[str]] = None,
        funding_rounds: Optional[List[str]] = None,
        limit: int = 50
    ) -> List[StartupData]:
        """
        Collect startup funding data using Perplexity API.
        
        Args:
            months_back: Number of months to look back for funding news
            industries: List of industries to focus on
            locations: List of locations to focus on
            funding_rounds: List of funding rounds to focus on (e.g., "seed", "series a")
            limit: Maximum number of startups to collect
            
        Returns:
            List of StartupData objects
        """
        # Calculate the date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30 * months_back)
        
        # Format date strings
        start_date_str = start_date.strftime("%Y-%m-%d")
        end_date_str = end_date.strftime("%Y-%m-%d")
        
        # Build the query
        query_parts = [
            f"startups that received funding between {start_date_str} and {end_date_str}"
        ]
        
        if industries:
            industry_str = ", ".join(industries)
            query_parts.append(f"in the {industry_str} industries")
            
        if locations:
            location_str = ", ".join(locations)
            query_parts.append(f"located in {location_str}")
            
        if funding_rounds:
            rounds_str = ", ".join(funding_rounds)
            query_parts.append(f"with {rounds_str} funding rounds")
            
        query = " ".join(query_parts)
        query += ". For each startup, provide: company name, description, funding amount, funding round, funding date, investors, industry, location, company size (if available), and company website."
        
        logger.info(f"Querying Perplexity API with: {query}")
        
        # Execute the query
        try:
            response = self.client.query(query)
            return self._parse_response(response, limit)
        except Exception as e:
            logger.error(f"Error querying Perplexity API: {e}")
            return []
    
    def _parse_response(self, response: Dict[str, Any], limit: int) -> List[StartupData]:
        """
        Parse the response from Perplexity API.
        
        Args:
            response: Response from Perplexity API
            limit: Maximum number of startups to return
            
        Returns:
            List of StartupData objects
        """
        startups = []
        
        # Extract the text content from the response
        if not response or "text" not in response:
            logger.warning("Invalid response format from Perplexity API")
            return startups
        
        content = response["text"]
        
        # Process the content to extract startup information
        # This is a simplified implementation and may need refinement based on actual API responses
        
        # Split the content by startup entries (assuming each startup is separated by a clear delimiter)
        # This is a placeholder implementation and will need to be adjusted based on actual response format
        startup_entries = self._extract_startup_entries(content)
        
        for entry in startup_entries[:limit]:
            try:
                startup_data = self._parse_startup_entry(entry)
                if startup_data:
                    startups.append(startup_data)
            except Exception as e:
                logger.error(f"Error parsing startup entry: {e}")
                continue
                
        return startups
    
    def _extract_startup_entries(self, content: str) -> List[str]:
        """
        Extract individual startup entries from the API response content.
        
        Args:
            content: Text content from Perplexity API response
            
        Returns:
            List of startup entry strings
        """
        # This is a placeholder implementation
        # In a real implementation, we would need to analyze the structure of the response
        # and extract each startup's information accordingly
        
        # For now, we'll assume each startup is separated by a numbered list or similar pattern
        import re
        
        # Try to match numbered entries like "1. Company Name" or similar patterns
        entries = re.split(r'\n\s*\d+\.\s+', content)
        
        # Remove empty entries and the potential first split before any numbers
        entries = [entry.strip() for entry in entries if entry.strip()]
        
        # If the above pattern didn't work, try other common separators
        if len(entries) <= 1:
            # Try splitting by company headers (assuming company names might be in bold or headers)
            entries = re.split(r'\n\s*\*\*([^*]+)\*\*|\n\s*#{1,3}\s+([^#\n]+)', content)
            entries = [entry.strip() for entry in entries if entry.strip()]
        
        # If we still don't have multiple entries, return the whole content as one entry
        if len(entries) <= 1:
            return [content]
            
        return entries
    
    def _parse_startup_entry(self, entry: str) -> Optional[StartupData]:
        """
        Parse a single startup entry from the extracted text.
        
        Args:
            entry: Text describing a single startup
            
        Returns:
            StartupData object or None if parsing fails
        """
        # This is a placeholder implementation
        # In a real implementation, we would need to extract structured information
        # from the text using NLP techniques, regex patterns, or other methods
        
        # For demonstration, we'll use a simple regex-based approach
        import re
        
        # Try to extract company name (assuming it's at the beginning or in bold)
        name_match = re.search(r'^([^:]+)|^\*\*([^*]+)\*\*', entry)
        if not name_match:
            # If no clear name pattern, try to find the first sentence or line
            name_match = re.search(r'^([^\.:\n]+)', entry)
            
        if not name_match:
            logger.warning(f"Could not extract company name from entry: {entry[:100]}...")
            return None
            
        name = name_match.group(1) or name_match.group(2)
        name = name.strip() if name else "Unknown Company"
        
        # Extract description (assuming it follows the name or is a separate paragraph)
        description_match = re.search(r'description:?\s*([^\.]+\.(?:[^\.]+\.){0,3})', entry, re.IGNORECASE)
        if not description_match:
            # Try to find any paragraph that's not clearly another field
            description_match = re.search(r'([^:\n]+\.[^:\n]+)', entry)
            
        description = description_match.group(1).strip() if description_match else "No description available"
        
        # Extract funding amount
        funding_amount_match = re.search(r'funding amount:?\s*([^,\.\n]+)', entry, re.IGNORECASE)
        funding_amount = funding_amount_match.group(1).strip() if funding_amount_match else None
        
        # Extract funding round
        funding_round_match = re.search(r'funding round:?\s*([^,\.\n]+)', entry, re.IGNORECASE)
        if not funding_round_match:
            # Try alternative patterns like "seed round" or "series a"
            funding_round_match = re.search(r'(seed round|series [a-z])', entry, re.IGNORECASE)
            
        funding_round = funding_round_match.group(1).strip() if funding_round_match else None
        
        # Extract funding date
        funding_date_match = re.search(r'funding date:?\s*([^,\.\n]+)', entry, re.IGNORECASE)
        if not funding_date_match:
            # Try to find date patterns
            funding_date_match = re.search(r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\w+ \d{1,2},? \d{4})', entry)
            
        funding_date_str = funding_date_match.group(1).strip() if funding_date_match else None
        funding_date = None
        if funding_date_str:
            try:
                # Try different date formats
                for fmt in ["%Y-%m-%d", "%m/%d/%Y", "%B %d, %Y", "%b %d, %Y"]:
                    try:
                        funding_date = datetime.strptime(funding_date_str, fmt)
                        break
                    except ValueError:
                        continue
            except Exception:
                pass
        
        # Extract investors
        investors_match = re.search(r'investors:?\s*([^\.]+)', entry, re.IGNORECASE)
        investors = []
        if investors_match:
            investors_str = investors_match.group(1).strip()
            # Split by common separators
            investors = [inv.strip() for inv in re.split(r',|\band\b', investors_str) if inv.strip()]
        
        # Extract industry
        industry_match = re.search(r'industry:?\s*([^,\.\n]+)', entry, re.IGNORECASE)
        industry = industry_match.group(1).strip() if industry_match else None
        
        # Extract location
        location_match = re.search(r'location:?\s*([^,\.\n]+)', entry, re.IGNORECASE)
        location = location_match.group(1).strip() if location_match else None
        
        # Extract company size
        company_size_match = re.search(r'company size:?\s*([^,\.\n]+)', entry, re.IGNORECASE)
        company_size = company_size_match.group(1).strip() if company_size_match else None
        
        # Extract company website
        website_match = re.search(r'(website|company website|url):?\s*([^,\.\s]+\.[^,\.\s]+)', entry, re.IGNORECASE)
        if not website_match:
            # Try to find URL patterns
            website_match = re.search(r'(https?://[^,\.\s]+\.[^,\.\s]+)', entry)
            
        company_url = website_match.group(2).strip() if website_match and website_match.group(2) else None
        if not company_url and website_match and website_match.group(1):
            company_url = website_match.group(1).strip()
        
        # Create and return the StartupData object
        return StartupData(
            name=name,
            description=description,
            funding_amount=funding_amount,
            funding_round=funding_round,
            funding_date=funding_date,
            investors=investors,
            industry=industry,
            location=location,
            company_size=company_size,
            company_url=company_url,
            source=self.get_source_name()
        )
