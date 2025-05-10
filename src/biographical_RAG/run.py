"""
Runner script for the biographical RAG system.
Provides a command-line interface to scrape content and ask questions.
"""

import argparse
import logging
from typing import Optional, List, Dict
from pathlib import Path
import sys
import os
print("sys.path:", sys.path)
print("Current working directory:", os.getcwd())
print("Contents of sys.path[0]:", os.listdir(sys.path[0]))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Change from relative to absolute imports
from biographical_RAG.scraper import scrape_person_content
from biographical_RAG.rag_qa import setup_rag_system

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

print("PYTHONPATH:", sys.path)

def scrape_mode(person_name: str, output_dir: str = "scraped_content") -> None:
    """Scrape content for a person."""
    try:
        content = scrape_person_content(person_name, output_dir, max_articles=10)
        logger.info(f"Successfully scraped {len(content)} pieces of content for {person_name}")
    except Exception as e:
        logger.error(f"Error scraping content for {person_name}: {str(e)}")
        sys.exit(1)

def qa_mode(person_name: str) -> None:
    """Interactive Q&A mode for a person."""
    try:
        # Set up the RAG system
        rag = setup_rag_system(person_name)
        logger.info(f"RAG system initialized for {person_name}")
        
        print(f"\nAsk questions about {person_name} (type 'exit' to quit):")
        
        while True:
            # Get question from user
            question = input("\nQ: ").strip()
            
            # Check for exit command
            if question.lower() in ['exit', 'quit', 'q']:
                break
            
            if not question:
                continue
            
            # Get answer
            try:
                result = rag.answer_question(question, person_name)
                print("\nA:", result['answer'])
                print("\nSources:")
                for source in result['sources']:
                    print(f"- {source}")
            except Exception as e:
                logger.error(f"Error answering question: {str(e)}")
                print("\nSorry, there was an error processing your question. Please try again.")
                
    except FileNotFoundError:
        logger.error(f"No content found for {person_name}. Please scrape content first using --scrape mode.")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error initializing RAG system: {str(e)}")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="Biographical RAG System Runner")
    parser.add_argument("person", help="Name of the person to scrape/query about")
    parser.add_argument("--scrape", action="store_true", help="Scrape new content for the person")
    parser.add_argument("--qa", action="store_true", help="Enter Q&A mode")
    parser.add_argument("--output-dir", default="scraped_content", help="Directory to store scraped content")
    
    args = parser.parse_args()
    
    # Create output directory if it doesn't exist
    Path(args.output_dir).mkdir(parents=True, exist_ok=True)
    
    # If no mode specified, default to QA mode
    if not (args.scrape or args.qa):
        args.qa = True
    
    # Run in specified mode(s)
    if args.scrape:
        scrape_mode(args.person, args.output_dir)
    
    if args.qa:
        qa_mode(args.person)

if __name__ == "__main__":
    main() 