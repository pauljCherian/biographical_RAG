"""
Module for scraping biographical content from various sources including speeches,
podcasts transcripts, blog posts, and other primary sources.
"""

import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Optional, Set
import time
import logging
from urllib.parse import quote_plus, urlparse, unquote
import json
from datetime import datetime
from pathlib import Path
import os
import re

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ContentScraper:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        self.rate_limit_delay = 2  # Delay between requests in seconds
        
        # Known reliable sources and their specific scraping methods
        self.reliable_sources = {
            'wikisource.org': self._scrape_wikisource,
            'gutenberg.org': self._scrape_gutenberg,
        }
        
        # Maximum documents to collect per category
        self.max_primary_sources = 5  # More primary sources
        self.max_secondary_sources = 2  # Fewer secondary sources

    def _clean_url(self, url: str) -> Optional[str]:
        """Clean and validate a URL."""
        try:
            # Remove whitespace and newlines
            url = url.strip()
            # Remove any HTML entities
            url = re.sub(r'&amp;', '&', url)
            # Decode URL-encoded characters
            url = unquote(url)
            
            # Validate URL format
            parsed = urlparse(url)
            if not parsed.scheme:
                url = 'https://' + url
            if not parsed.netloc:
                return None
                
            return url
        except Exception as e:
            logger.error(f"Error cleaning URL {url}: {str(e)}")
            return None

    def _make_request(self, url: str) -> Optional[requests.Response]:
        """Make a rate-limited request with error handling."""
        try:
            time.sleep(self.rate_limit_delay)
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            return response
        except requests.RequestException as e:
            logger.error(f"Error fetching {url}: {str(e)}")
            return None

    def _search_duckduckgo(self, query: str, max_results: int = 3) -> List[str]:
        """Search DuckDuckGo for relevant URLs."""
        search_url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
        response = self._make_request(search_url)
        if not response:
            return []
        
        soup = BeautifulSoup(response.text, 'html.parser')
        links = set()
        
        # Extract results from DuckDuckGo HTML response
        for result in soup.select('.result__url'):
            url = result.get_text()
            if url:
                clean_url = self._clean_url(url)
                if clean_url:
                    # Filter out unwanted domains
                    domain = urlparse(clean_url).netloc
                    if not any(excluded in domain for excluded in ['google.com', 'youtube.com', 'facebook.com', 'twitter.com']):
                        links.add(clean_url)
        
        # Also try getting URLs from the actual result links
        for result in soup.select('.result__a'):
            href = result.get('href', '')
            if href:
                clean_url = self._clean_url(href)
                if clean_url:
                    domain = urlparse(clean_url).netloc
                    if not any(excluded in domain for excluded in ['google.com', 'youtube.com', 'facebook.com', 'twitter.com']):
                        links.add(clean_url)
        
        return list(links)[:max_results]

    def _scrape_wikisource(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract content from Wikisource pages."""
        content_div = soup.find('div', {'class': 'mw-parser-output'})
        if not content_div:
            return None
            
        # Remove unwanted elements
        for unwanted in content_div.select('.reference, .mw-editsection'):
            unwanted.decompose()
            
        return content_div.get_text(separator='\n').strip()

    def _scrape_gutenberg(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract content from Project Gutenberg pages."""
        content_div = soup.find('div', {'class': 'text'})
        if not content_div:
            return None
            
        return content_div.get_text(separator='\n').strip()

    def _extract_content(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract content from a webpage using BeautifulSoup."""
        # Remove unwanted elements
        for unwanted in soup(['script', 'style', 'nav', 'header', 'footer', 'iframe', 'aside']):
            unwanted.decompose()

        # Try different content selectors
        selectors = [
            'article',
            'main',
            '.post-content',
            '.entry-content',
            '.article-content',
            '.content',
            '#content',
            '.post',
            'div[role="main"]',
            '.main-content'
        ]

        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                # Clean up the content
                for unwanted in element(['script', 'style', 'nav', 'header', 'footer', 'iframe', 'aside']):
                    unwanted.decompose()
                content = element.get_text(separator='\n').strip()
                if len(content) > 500:  # Only keep substantial content
                    return content

        # Fallback to body content if no suitable content found
        body = soup.find('body')
        if body:
            for unwanted in body(['script', 'style', 'nav', 'header', 'footer', 'iframe', 'aside']):
                unwanted.decompose()
            content = body.get_text(separator='\n').strip()
            if len(content) > 500:
                return content

        return None

    def scrape_content(self, name: str) -> List[Dict]:
        """
        Scrape content related to the given person from various sources.
        
        Args:
            name (str): The name of the person to search for
            
        Returns:
            List[Dict]: List of dictionaries containing scraped content with metadata
        """
        logger.info(f"Starting content scraping for: {name}")
        collected_content = []
        seen_urls = set()
        
        # First priority: Primary sources
        primary_queries = [
            f"site:wikisource.org {name} writings",
            f"site:gutenberg.org {name} works",
            f"{name} original writings",
            f"{name} letters correspondence primary source",
        ]
        
        # Second priority: Secondary sources
        secondary_queries = [
            f"{name} philosophical writings analysis",
            f"{name} historical biography",
        ]

        # Process primary sources first
        primary_count = 0
        for query in primary_queries:
            if primary_count >= self.max_primary_sources:
                break
                
            logger.info(f"Searching primary sources: {query}")
            urls = self._search_duckduckgo(query, max_results=2)  # Limit results per query
            
            for url in urls:
                if url in seen_urls or primary_count >= self.max_primary_sources:
                    continue
                    
                seen_urls.add(url)
                logger.info(f"Processing primary source URL: {url}")

                response = self._make_request(url)
                if not response:
                    continue

                soup = BeautifulSoup(response.text, 'html.parser')
                content = None
                
                # Check if it's a known source
                domain = urlparse(url).netloc
                for known_domain, scraper_func in self.reliable_sources.items():
                    if known_domain in domain:
                        content = scraper_func(soup)
                        if content:
                            entry = {
                                'source_url': url,
                                'content': content,
                                'content_type': 'primary_source',
                                'person': name,
                                'scraped_date': datetime.now().isoformat(),
                                'title': soup.title.string if soup.title else url,
                            }
                            collected_content.append(entry)
                            primary_count += 1
                            logger.info(f"Successfully scraped primary source from: {url}")
                        break

                # If not a known source, try generic extraction
                if not content and 'primary' in query.lower():
                    content = self._extract_content(soup)
                    if content:
                        entry = {
                            'source_url': url,
                            'content': content,
                            'content_type': 'primary_source',
                            'person': name,
                            'scraped_date': datetime.now().isoformat(),
                            'title': soup.title.string if soup.title else url,
                        }
                        collected_content.append(entry)
                        primary_count += 1
                        logger.info(f"Successfully scraped primary source from: {url}")

        # Process secondary sources if we need more content
        secondary_count = 0
        if len(collected_content) < (self.max_primary_sources + self.max_secondary_sources):
            for query in secondary_queries:
                if secondary_count >= self.max_secondary_sources:
                    break
                    
                logger.info(f"Searching secondary sources: {query}")
                urls = self._search_duckduckgo(query, max_results=1)  # Very limited secondary sources
                
                for url in urls:
                    if url in seen_urls or secondary_count >= self.max_secondary_sources:
                        continue
                        
                    seen_urls.add(url)
                    logger.info(f"Processing secondary source URL: {url}")

                    response = self._make_request(url)
                    if not response:
                        continue

                    soup = BeautifulSoup(response.text, 'html.parser')
                    content = self._extract_content(soup)
                    if content:
                        entry = {
                            'source_url': url,
                            'content': content,
                            'content_type': 'secondary_source',
                            'person': name,
                            'scraped_date': datetime.now().isoformat(),
                            'title': soup.title.string if soup.title else url,
                        }
                        collected_content.append(entry)
                        secondary_count += 1
                        logger.info(f"Successfully scraped secondary source from: {url}")

        logger.info(f"Completed scraping. Found {primary_count} primary sources and {secondary_count} secondary sources.")
        return collected_content

def scrape_person_content(name: str, output_dir: Optional[str] = None) -> List[Dict]:
    """
    Main function to scrape content for a person and optionally save to file.
    
    Args:
        name (str): Name of the person to scrape content for
        output_dir (Optional[str]): Directory to save scraped content
        
    Returns:
        List[Dict]: List of scraped content items
    """
    scraper = ContentScraper()
    content = scraper.scrape_content(name)
    
    if output_dir:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Save to JSON file
        output_file = output_dir / f"{name.lower().replace(' ', '_')}_content.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(content, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Saved scraped content to: {output_file}")
    
    return content

if __name__ == "__main__":
    # Example usage
    content = scrape_person_content("Marcus Aurelius", "scraped_content")
    print(f"Found {len(content)} pieces of content")
