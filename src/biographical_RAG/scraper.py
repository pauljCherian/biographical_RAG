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

    def _search_duckduckgo(self, query: str) -> List[str]:
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
        
        # Prioritize primary sources: allow more results for them
        primary_sources = ["wikisource", "gutenberg"]
        if any(ps in query.lower() for ps in primary_sources):
            return list(links)[:10]  # Up to 10 for primary sources
        else:
            return list(links)[:4]  # Only 4 for others

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

    def scrape_content(self, name: str, max_articles: int = 10) -> List[Dict]:
        """
        Scrape content related to the given person from various sources.
        Args:
            name (str): The name of the person to search for
            max_articles (int): Maximum number of articles to scrape
        Returns:
            List[Dict]: List of dictionaries containing scraped content with metadata
        """
        logger.info(f"Starting content scraping for: {name}")
        collected_content = []
        seen_urls = set()

        # Search queries for different content types
        search_queries = [
            f"{name} speech transcript",
            f"{name} writings",
            f"{name} letters correspondence",
            f"{name} interview transcript",
            f"{name} essays",
            f"site:wikisource.org {name}",
            f"site:gutenberg.org {name}",
        ]

        for query in search_queries:
            logger.info(f"Searching for: {query}")
            urls = self._search_duckduckgo(query)
            for url in urls:
                if url in seen_urls:
                    continue
                if len(collected_content) >= max_articles:
                    logger.info(f"Reached max_articles limit ({max_articles}). Stopping scrape.")
                    return collected_content
                seen_urls.add(url)
                logger.info(f"Processing URL: {url}")

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
                            logger.info(f"Successfully scraped content from known source: {url}")
                        break
                # If not a known source or known source failed, try generic extraction
                if not content:
                    content = self._extract_content(soup)
                    if content:
                        entry = {
                            'source_url': url,
                            'content': content,
                            'content_type': self._determine_content_type(query),
                            'person': name,
                            'scraped_date': datetime.now().isoformat(),
                            'title': soup.title.string if soup.title else url,
                        }
                        collected_content.append(entry)
                        logger.info(f"Successfully scraped content from: {url}")
                if len(collected_content) >= max_articles:
                    logger.info(f"Reached max_articles limit ({max_articles}). Stopping scrape.")
                    return collected_content
        return collected_content

    def _determine_content_type(self, query: str) -> str:
        """Determine content type based on search query."""
        if 'speech' in query:
            return 'speech'
        elif 'writings' in query or 'essays' in query:
            return 'writing'
        elif 'letters' in query or 'correspondence' in query:
            return 'correspondence'
        elif 'interview' in query:
            return 'interview'
        elif 'wikisource' in query or 'gutenberg' in query:
            return 'primary_source'
        else:
            return 'other'

def scrape_person_content(name: str, output_dir: Optional[str] = None, max_articles: int = 10) -> List[Dict]:
    """
    Main function to scrape content for a person and optionally save to file.
    Args:
        name (str): Name of the person to scrape content for
        output_dir (Optional[str]): Directory to save scraped content
        max_articles (int): Maximum number of articles to scrape
    Returns:
        List[Dict]: List of scraped content items
    """
    scraper = ContentScraper()
    content = scraper.scrape_content(name, max_articles=max_articles)
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
