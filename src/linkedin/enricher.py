"""
LinkedIn company page retrieval and contact enrichment functionality.
"""
import logging
import re
import time
from typing import List, Dict, Any, Optional, Tuple

import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright, Page

from src.data_collection.base import StartupData

logger = logging.getLogger(__name__)


class LinkedInEnricher:
    """
    Enriches startup data with LinkedIn company information and key employee contacts.
    """
    
    def __init__(self, use_browser: bool = True, headless: bool = True):
        """
        Initialize the LinkedIn enricher.
        
        Args:
            use_browser: Whether to use browser-based scraping (more robust but slower)
            headless: Whether to run the browser in headless mode
        """
        self.use_browser = use_browser
        self.headless = headless
        self.browser = None
        self.page = None
    
    def __enter__(self):
        """Context manager entry point."""
        if self.use_browser:
            self._setup_browser()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit point."""
        if self.browser:
            self.browser.close()
            self.browser = None
            self.page = None
    
    def _setup_browser(self):
        """Set up the browser for LinkedIn scraping."""
        playwright = sync_playwright().start()
        self.browser = playwright.chromium.launch(headless=self.headless)
        self.page = self.browser.new_page()
        
        # Set user agent to avoid detection
        self.page.set_extra_http_headers({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
    
    def enrich_startup(self, startup: StartupData) -> StartupData:
        """
        Enrich a startup with LinkedIn information.
        
        Args:
            startup: StartupData object to enrich
            
        Returns:
            Enriched StartupData object
        """
        try:
            # find linkedin company page if not already available
            if not startup.linkedin_url:
                linkedin_url = self.find_company_linkedin_page(startup.name, startup.company_url)
                if linkedin_url:
                    startup.linkedin_url = linkedin_url
                    logger.info(f"Found LinkedIn page for {startup.name}: {linkedin_url}")
            
            # extract key people if linkedin url is available
            if startup.linkedin_url and not startup.key_people:
                key_people = self.extract_key_people(startup.linkedin_url)
                if key_people:
                    startup.key_people = key_people
                    logger.info(f"Found {len(key_people)} key people for {startup.name}")
        
        except Exception as e:
            logger.error(f"Error enriching startup {startup.name}: {e}")
        
        return startup
    
    def enrich_startups(self, startups: List[StartupData]) -> List[StartupData]:
        """
        Enrich multiple startups with LinkedIn information.
        
        Args:
            startups: List of StartupData objects to enrich
            
        Returns:
            List of enriched StartupData objects
        """
        enriched_startups = []
        
        for startup in startups:
            try:
                enriched_startup = self.enrich_startup(startup)
                enriched_startups.append(enriched_startup)
                
                # Add a small delay to avoid rate limiting
                time.sleep(1)
                
            except Exception as e:
                logger.error(f"Error enriching startup {startup.name}: {e}")
                enriched_startups.append(startup)  # Add original startup to maintain list integrity
        
        return enriched_startups
    
    def find_company_linkedin_page(self, company_name: str, company_website: Optional[str] = None) -> Optional[str]:
        """
        Find a company's LinkedIn page URL.
        
        Args:
            company_name: Name of the company
            company_website: Company website URL (optional, improves accuracy)
            
        Returns:
            LinkedIn company page URL or None if not found
        """
        # Strategy 1: Direct search using Google
        linkedin_url = self._find_linkedin_via_google(company_name)
        if linkedin_url:
            return linkedin_url
        
        # Strategy 2: If website is available, check for LinkedIn link on the website
        if company_website:
            linkedin_url = self._find_linkedin_on_website(company_website)
            if linkedin_url:
                return linkedin_url
        
        # Strategy 3: Direct search on LinkedIn
        linkedin_url = self._find_linkedin_via_linkedin_search(company_name)
        if linkedin_url:
            return linkedin_url
        
        return None
    
    def _find_linkedin_via_google(self, company_name: str) -> Optional[str]:
        """
        Find LinkedIn page via Google search.
        
        Args:
            company_name: Company name
            
        Returns:
            LinkedIn URL or None if not found
        """
        try:
            # Construct search query
            query = f"{company_name} linkedin company"
            search_url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
            
            if self.use_browser and self.page:
                # Use browser for more reliable results
                self.page.goto(search_url, wait_until="networkidle")
                content = self.page.content()
            else:
                # Fallback to requests
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                }
                response = requests.get(search_url, headers=headers, timeout=30)
                content = response.text
            
            # Parse the content
            soup = BeautifulSoup(content, 'html.parser')
            
            # Look for LinkedIn links
            for link in soup.find_all('a'):
                href = link.get('href')
                if href and 'linkedin.com/company/' in href:
                    # Extract the actual URL from Google's redirect URL
                    match = re.search(r'https://[^&]+linkedin\.com/company/[^&]+', href)
                    if match:
                        linkedin_url = match.group(0)
                        # Clean up the URL
                        linkedin_url = linkedin_url.split('&')[0]
                        return linkedin_url
            
            return None
            
        except Exception as e:
            logger.error(f"Error finding LinkedIn via Google for {company_name}: {e}")
            return None
    
    def _find_linkedin_on_website(self, website_url: str) -> Optional[str]:
        """
        Find LinkedIn link on company website.
        
        Args:
            website_url: Company website URL
            
        Returns:
            LinkedIn URL or None if not found
        """
        try:
            if not website_url.startswith(('http://', 'https://')):
                website_url = 'https://' + website_url
            
            if self.use_browser and self.page:
                try:
                    self.page.goto(website_url, wait_until="networkidle", timeout=30000)
                    content = self.page.content()
                except Exception:
                    # Try without waiting for networkidle
                    try:
                        self.page.goto(website_url, timeout=30000)
                        content = self.page.content()
                    except Exception as e:
                        logger.error(f"Error accessing website {website_url}: {e}")
                        return None
            else:
                # Fallback to requests
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                }
                response = requests.get(website_url, headers=headers, timeout=30)
                content = response.text
            
            # Parse the content
            soup = BeautifulSoup(content, 'html.parser')
            
            # Look for LinkedIn links in social media sections or footer
            for link in soup.find_all('a'):
                href = link.get('href')
                if href and 'linkedin.com/company/' in href:
                    return href
                
                # Check for icons or classes that might indicate LinkedIn
                classes = link.get('class', [])
                if isinstance(classes, list):
                    classes = ' '.join(classes)
                
                if 'linkedin' in str(classes).lower() or 'linkedin' in str(link).lower():
                    href = link.get('href')
                    if href and ('linkedin.com' in href):
                        return href
            
            return None
            
        except Exception as e:
            logger.error(f"Error finding LinkedIn on website {website_url}: {e}")
            return None
    
    def _find_linkedin_via_linkedin_search(self, company_name: str) -> Optional[str]:
        """
        Find LinkedIn page via LinkedIn search.
        
        Args:
            company_name: Company name
            
        Returns:
            LinkedIn URL or None if not found
        """
        if not self.use_browser or not self.page:
            return None
        
        try:
            # Go to LinkedIn search page
            search_url = f"https://www.linkedin.com/search/results/companies/?keywords={company_name.replace(' ', '%20')}"
            self.page.goto(search_url, wait_until="networkidle")
            
            # Check if we're redirected to login page
            if "login" in self.page.url:
                logger.warning("LinkedIn requires login, cannot search directly")
                return None
            
            # Look for company results
            company_links = self.page.query_selector_all('a[data-control-name="search_srp_result"]')
            
            if company_links:
                # Get the first result
                href = company_links[0].get_attribute('href')
                if href and '/company/' in href:
                    return href
            
            return None
            
        except Exception as e:
            logger.error(f"Error finding LinkedIn via LinkedIn search for {company_name}: {e}")
            return None
    
    def extract_key_people(self, linkedin_url: str) -> List[Dict[str, str]]:
        """
        Extract key people from a LinkedIn company page.
        
        Args:
            linkedin_url: LinkedIn company page URL
            
        Returns:
            List of key people with name, title, and LinkedIn URL
        """
        if not self.use_browser or not self.page:
            return []
        
        key_people = []
        
        try:
            # Navigate to the company page
            self.page.goto(linkedin_url, wait_until="networkidle")
            
            # Check if we're redirected to login page
            if "login" in self.page.url:
                logger.warning("LinkedIn requires login, cannot extract key people")
                return []
            
            # Try to find the "People" tab or section
            people_tab = None
            
            # Look for "People" tab
            tabs = self.page.query_selector_all('a[data-control-name="page_member_main_nav_people_tab"]')
            if tabs:
                people_tab = tabs[0]
            
            # If found, click on it
            if people_tab:
                people_tab.click()
                self.page.wait_for_load_state("networkidle")
            
            # Extract people information
            # This is a simplified approach and may need adjustment based on LinkedIn's actual structure
            people_elements = self.page.query_selector_all('.org-people-profile-card')
            
            for element in people_elements:
                try:
                    name_elem = element.query_selector('.org-people-profile-card__profile-title')
                    title_elem = element.query_selector('.org-people-profile-card__profile-position')
                    link_elem = element.query_selector('a')
                    
                    name = name_elem.text_content().strip() if name_elem else ""
                    title = title_elem.text_content().strip() if title_elem else ""
                    profile_url = link_elem.get_attribute('href') if link_elem else None
                    
                    if name and (title or profile_url):
                        key_people.append({
                            "name": name,
                            "title": title,
                            "linkedin_url": profile_url
                        })
                except Exception as e:
                    logger.error(f"Error extracting person info: {e}")
                    continue
            
            # If no people found via the tab, try to extract from the main page
            if not key_people:
                # Look for employee highlights or featured employees
                employee_elements = self.page.query_selector_all('.artdeco-entity-lockup')
                
                for element in employee_elements:
                    try:
                        name_elem = element.query_selector('.artdeco-entity-lockup__title')
                        title_elem = element.query_selector('.artdeco-entity-lockup__subtitle')
                        link_elem = element.query_selector('a')
                        
                        name = name_elem.text_content().strip() if name_elem else ""
                        title = title_elem.text_content().strip() if title_elem else ""
                        profile_url = link_elem.get_attribute('href') if link_elem else None
                        
                        if name and (title or profile_url):
                            key_people.append({
                                "name": name,
                                "title": title,
                                "linkedin_url": profile_url
                            })
                    except Exception as e:
                        logger.error(f"Error extracting person info: {e}")
                        continue
            
            return key_people
            
        except Exception as e:
            logger.error(f"Error extracting key people from {linkedin_url}: {e}")
            return []
    
    def extract_email_from_profile(self, profile_url: str) -> Optional[str]:
        """
        Extract email from a LinkedIn profile if publicly available.
        
        Args:
            profile_url: LinkedIn profile URL
            
        Returns:
            Email address or None if not found
        """
        if not self.use_browser or not self.page:
            return None
        
        try:
            # Navigate to the profile
            self.page.goto(profile_url, wait_until="networkidle")
            
            # Check if we're redirected to login page
            if "login" in self.page.url:
                logger.warning("LinkedIn requires login, cannot extract email")
                return None
            
            # Look for contact info section
            contact_info_button = self.page.query_selector('a[data-control-name="contact_see_more"]')
            if contact_info_button:
                contact_info_button.click()
                self.page.wait_for_load_state("networkidle")
                
                # Look for email in the modal
                email_elements = self.page.query_selector_all('section.pv-contact-info__contact-type.ci-email')
                
                for element in email_elements:
                    link_elem = element.query_selector('a')
                    if link_elem:
                        href = link_elem.get_attribute('href')
                        if href and href.startswith('mailto:'):
                            return href.replace('mailto:', '')
            
            return None
            
        except Exception as e:
            logger.error(f"Error extracting email from {profile_url}: {e}")
            return None
