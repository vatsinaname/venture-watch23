"""
Web scraping collector for startup funding data.
"""
import logging
import re
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Tuple

import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

from src.data_collection.base import DataCollector, StartupData

logger = logging.getLogger(__name__)


class WebScrapingCollector(DataCollector):
    """Collector that uses web scraping to find startup funding information."""
    
    def __init__(self, sources: List[Dict[str, str]]):
        """
        Initialize the web scraping collector.
        
        Args:
            sources: List of source configurations with 'name' and 'url' keys
        """
        self.sources = sources
        
    def get_source_name(self) -> str:
        """Get the name of the data source."""
        return "Web Scraping"
    
    def collect(
        self, 
        months_back: int = 3,
        use_browser: bool = True,
        **kwargs
    ) -> List[StartupData]:
        """
        Collect startup funding data by scraping configured sources.
        
        Args:
            months_back: Number of months to look back for funding news
            use_browser: Whether to use browser-based scraping (more robust but slower)
            **kwargs: Additional parameters passed to source-specific scrapers
            
        Returns:
            List of StartupData objects
        """
        all_startups = []
        
        # Calculate the date threshold
        date_threshold = datetime.now() - timedelta(days=30 * months_back)
        
        for source in self.sources:
            try:
                logger.info(f"Scraping source: {source['name']} ({source['url']})")
                
                # determine which scraper to use based on the source
                if source['name'].lower() == 'crunchbase':
                    startups = self._scrape_crunchbase(source['url'], date_threshold, use_browser)
                elif source['name'].lower() == 'techcrunch':
                    startups = self._scrape_techcrunch(source['url'], date_threshold, use_browser)
                elif source['name'].lower() == 'venturebeat':
                    startups = self._scrape_venturebeat(source['url'], date_threshold, use_browser)
                else:
                    # generic scraper for other sources
                    startups = self._scrape_generic(source['url'], source['name'], date_threshold, use_browser)
                
                # add source information to each startup
                for startup in startups:
                    startup.source = source['name']
                    startup.source_url = source['url']
                
                all_startups.extend(startups)
                logger.info(f"Found {len(startups)} startups from {source['name']}")
                
            except Exception as e:
                logger.error(f"Error scraping {source['name']}: {e}")
                continue
                
        return all_startups
    
    def _scrape_generic(
        self, 
        url: str, 
        source_name: str,
        date_threshold: datetime,
        use_browser: bool
    ) -> List[StartupData]:
        """
        Generic scraper that attempts to extract funding information from any source.
        
        Args:
            url: URL to scrape
            source_name: Name of the source
            date_threshold: Date threshold for filtering results
            use_browser: Whether to use browser-based scraping
            
        Returns:
            List of StartupData objects
        """
        startups = []
        
        if use_browser:
            html_content = self._get_content_with_browser(url)
        else:
            html_content = self._get_content_with_requests(url)
            
        if not html_content:
            return startups
            
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # look for common patterns in funding news articles
        
        # find article elements
        articles = soup.find_all(['article', 'div', 'section'], class_=lambda c: c and any(
            term in str(c).lower() for term in ['article', 'post', 'news', 'funding', 'startup']
        ))
        
        if not articles:
            # try to find any div that might contain articles
            articles = soup.find_all('div', class_=lambda c: c and 'container' in str(c).lower())
        
        for article in articles:
            try:
                # extrc title/company name
                title_elem = article.find(['h1', 'h2', 'h3', 'h4', 'a'], class_=lambda c: c and any(
                    term in str(c).lower() for term in ['title', 'heading', 'headline']
                ))
                
                if not title_elem:
                    title_elem = article.find(['h1', 'h2', 'h3', 'h4', 'a'])
                    
                if not title_elem:
                    continue
                    
                title = title_elem.get_text().strip()
                
                # check if this is a funding article
                funding_keywords = ['raise', 'raised', 'funding', 'investment', 'seed', 'series', 'venture', 'capital']
                if not any(keyword in title.lower() for keyword in funding_keywords):
                    continue
                
                # ext date
                date_elem = article.find(['time', 'span', 'div', 'p'], class_=lambda c: c and any(
                    term in str(c).lower() for term in ['date', 'time', 'published', 'posted']
                ))
                
                article_date = None
                if date_elem:
                    date_text = date_elem.get_text().strip()
                    article_date = self._parse_date(date_text)
                
                if article_date and article_date < date_threshold:
                    continue
                
                # ext descr/cont
                content_elem = article.find(['p', 'div'], class_=lambda c: c and any(
                    term in str(c).lower() for term in ['excerpt', 'summary', 'content', 'description']
                ))
                
                description = ""
                if content_elem:
                    description = content_elem.get_text().strip()
                
                # ext link for more details
                link_elem = title_elem if title_elem.name == 'a' else article.find('a')
                article_url = None
                if link_elem and link_elem.get('href'):
                    href = link_elem['href']
                    if href.startswith('/'):
                        # rel url
                        base_url = '/'.join(url.split('/')[:3])  # http(s)://domain.com
                        article_url = base_url + href
                    elif href.startswith('http'):
                        # abs url
                        article_url = href
                
                # ext company name from title
                company_name = self._extract_company_name(title)
                
                # ext fund dets from title and descr
                funding_amount = self._extract_funding_amount(title + " " + description)
                funding_round = self._extract_funding_round(title + " " + description)
                
                # create startup data
                startup = StartupData(
                    name=company_name,
                    description=description,
                    funding_amount=funding_amount,
                    funding_round=funding_round,
                    funding_date=article_date,
                    source=source_name,
                    source_url=article_url or url
                )
                
                startups.append(startup)
                
            except Exception as e:
                logger.error(f"Error processing article: {e}")
                continue
        
        return startups
    
    def _scrape_crunchbase(
        self, 
        url: str, 
        date_threshold: datetime,
        use_browser: bool
    ) -> List[StartupData]:
        """
        Scrape funding information from Crunchbase.
        
        Args:
            url: Crunchbase URL to scrape
            date_threshold: Date threshold for filtering results
            use_browser: Whether to use browser-based scraping
            
        Returns:
            List of StartupData objects
        """
        return self._scrape_generic(url, "Crunchbase", date_threshold, use_browser)
    
    def _scrape_techcrunch(
        self, 
        url: str, 
        date_threshold: datetime,
        use_browser: bool
    ) -> List[StartupData]:
        """
        Scrape funding information from TechCrunch.
        
        Args:
            url: TechCrunch URL to scrape
            date_threshold: Date threshold for filtering results
            use_browser: Whether to use browser-based scraping
            
        Returns:
            List of StartupData objects
        """
        return self._scrape_generic(url, "TechCrunch", date_threshold, use_browser)
    
    def _scrape_venturebeat(
        self, 
        url: str, 
        date_threshold: datetime,
        use_browser: bool
    ) -> List[StartupData]:
        """
        Scrape funding information from VentureBeat.
        
        Args:
            url: VentureBeat URL to scrape
            date_threshold: Date threshold for filtering results
            use_browser: Whether to use browser-based scraping
            
        Returns:
            List of StartupData objects
        """
        return self._scrape_generic(url, "VentureBeat", date_threshold, use_browser)
    
    def _get_content_with_requests(self, url: str) -> Optional[str]:
        """
        Get HTML content using requests library.
        
        Args:
            url: URL to fetch
            
        Returns:
            HTML content as string or None if failed
        """
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            return response.text
        except Exception as e:
            logger.error(f"Error fetching URL with requests: {url} - {e}")
            return None
    
    def _get_content_with_browser(self, url: str) -> Optional[str]:
        """
        Get HTML content using Playwright browser.
        
        Args:
            url: URL to fetch
            
        Returns:
            HTML content as string or None if failed
        """
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                page.goto(url, wait_until="networkidle", timeout=60000)
                
                # Wait for content to load
                page.wait_for_selector('body', timeout=10000)
                
                # Scroll down to load lazy content
                page.evaluate("""
                    window.scrollTo(0, document.body.scrollHeight / 2);
                    new Promise(resolve => setTimeout(resolve, 1000));
                    window.scrollTo(0, document.body.scrollHeight);
                """)
                
                # Wait a bit for any lazy-loaded content
                page.wait_for_timeout(2000)
                
                content = page.content()
                browser.close()
                return content
        except Exception as e:
            logger.error(f"Error fetching URL with browser: {url} - {e}")
            return None
    
    def _parse_date(self, date_text: str) -> Optional[datetime]:
        """
        Parse date from text.
        
        Args:
            date_text: Date text to parse
            
        Returns:
            Datetime object or None if parsing fails
        """
        try:
            # try common date formats
            for fmt in ["%Y-%m-%d", "%B %d, %Y", "%b %d, %Y", "%d %B %Y", "%d %b %Y", "%m/%d/%Y"]:
                try:
                    return datetime.strptime(date_text, fmt)
                except ValueError:
                    continue
            
            # try relative dates
            if "today" in date_text.lower():
                return datetime.now()
            elif "yesterday" in date_text.lower():
                return datetime.now() - timedelta(days=1)
            
            # try to ext patterns liek
            relative_match = re.search(r'(\d+)\s+(day|days|week|weeks|month|months|year|years)\s+ago', date_text, re.IGNORECASE)
            if relative_match:
                amount = int(relative_match.group(1))
                unit = relative_match.group(2).lower()
                
                if unit in ["day", "days"]:
                    return datetime.now() - timedelta(days=amount)
                elif unit in ["week", "weeks"]:
                    return datetime.now() - timedelta(weeks=amount)
                elif unit in ["month", "months"]:
                    return datetime.now() - timedelta(days=30 * amount)
                elif unit in ["year", "years"]:
                    return datetime.now() - timedelta(days=365 * amount)
        except Exception as e:
            logger.error(f"Error parsing date: {date_text} - {e}")
            
        return None
    
    def _extract_company_name(self, title: str) -> str:
        """
        Extract company name from article title.
        
        Args:
            title: Article title
            
        Returns:
            Company name
        """
        match = re.search(r'^([^,]+?)\s+raises', title, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        
        match = re.search(r'^([^,]+?)\s+secures', title, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        
        match = re.search(r'^([^,]+?)\s+gets', title, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        
        match = re.search(r'^([^,]+?)\s+closes', title, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        
        # if no pattern matches ret to the first part of the title
        parts = title.split(':')
        if len(parts) > 1:
            return parts[0].strip()
        
        parts = title.split(' - ')
        if len(parts) > 1:
            return parts[0].strip()
        
        # def to first 5 words if nothing works
        words = title.split()
        if len(words) > 5:
            return ' '.join(words[:5]).strip()
        
        return title.strip()
    
    def _extract_funding_amount(self, text: str) -> Optional[str]:
        """
        Extract funding amount from text.
        
        Args:
            text: Text to extract from
            
        Returns:
            Funding amount as string or None if not found
        """
        # look for currency symbols followed by numbers
        match = re.search(r'(\$|€|£)(\d+(?:\.\d+)?)\s*(million|m|billion|b|k|thousand)?', text, re.IGNORECASE)
        if match:
            amount = match.group(2)
            multiplier = match.group(3).lower() if match.group(3) else ''
            
            if multiplier in ['million', 'm']:
                return f"{match.group(1)}{amount} million"
            elif multiplier in ['billion', 'b']:
                return f"{match.group(1)}{amount} billion"
            elif multiplier in ['thousand', 'k']:
                return f"{match.group(1)}{amount} thousand"
            else:
                return f"{match.group(1)}{amount}"
        
        # look for numbers followed by currency words
        match = re.search(r'(\d+(?:\.\d+)?)\s*(million|m|billion|b|k|thousand)?\s*(dollars|euros|pounds)', text, re.IGNORECASE)
        if match:
            amount = match.group(1)
            multiplier = match.group(2).lower() if match.group(2) else ''
            currency = match.group(3).lower()
            
            currency_symbol = '$' if currency == 'dollars' else ('€' if currency == 'euros' else '£')
            
            if multiplier in ['million', 'm']:
                return f"{currency_symbol}{amount} million"
            elif multiplier in ['billion', 'b']:
                return f"{currency_symbol}{amount} billion"
            elif multiplier in ['thousand', 'k']:
                return f"{currency_symbol}{amount} thousand"
            else:
                return f"{currency_symbol}{amount}"
        
        return None
    
    def _extract_funding_round(self, text: str) -> Optional[str]:
        """
        Extract funding round from text.
        
        Args:
            text: Text to extract from
            
        Returns:
            Funding round as string or None if not found
        """
        # look for common funding round terms
        round_patterns = [
            (r'seed\s+round', 'Seed'),
            (r'seed\s+funding', 'Seed'),
            (r'pre-seed', 'Pre-Seed'),
            (r'series\s+a', 'Series A'),
            (r'series\s+b', 'Series B'),
            (r'series\s+c', 'Series C'),
            (r'series\s+d', 'Series D'),
            (r'series\s+e', 'Series E'),
            (r'series\s+f', 'Series F'),
            (r'growth\s+round', 'Growth'),
            (r'late\s+stage', 'Late Stage'),
            (r'angel\s+round', 'Angel'),
            (r'equity\s+round', 'Equity'),
            (r'convertible\s+note', 'Convertible Note'),
            (r'debt\s+financing', 'Debt Financing'),
            (r'initial\s+public\s+offering', 'IPO'),
            (r'ipo', 'IPO')
        ]
        
        for pattern, round_name in round_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return round_name
        
        return None
