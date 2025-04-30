"""Biographical RAG system package."""

from .scraper import scrape_person_content
from .rag_qa import setup_rag_system, BiographicalRAG

__all__ = ['scrape_person_content', 'setup_rag_system', 'BiographicalRAG']

# Version information
__version__ = '0.1.0'
