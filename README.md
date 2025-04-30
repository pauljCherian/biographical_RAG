# Biographical RAG System

A Retrieval Augmented Generation (RAG) system that allows you to have intelligent conversations about historical figures using their actual writings and biographical content.

## Features

- **Smart Content Scraping**: Automatically collects biographical content from various reliable sources including:
  - Wikisource
  - Project Gutenberg
  - Speeches and transcripts
  - Letters and correspondence
  - Historical writings and essays

- **Intelligent Question Answering**: Uses OpenAI's GPT-4 to provide accurate answers based on retrieved content
  - Sources are cited for every answer
  - Focuses on factual information from reliable sources
  - Admits when information is not available in the source material

- **Efficient Content Storage**: 
  - Uses ChromaDB for vector storage
  - Persistent storage of embeddings to prevent redundant API calls
  - Semantic search for relevant content retrieval

## Setup

1. Clone the repository:
```bash
git clone https://github.com/your-username/biographical_RAG.git
cd biographical_RAG
```

2. Create and activate a virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -e .
```

4. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your OpenAI API key
```

## Usage

The system provides two main modes of operation:

### 1. Content Scraping

Collect biographical content about a historical figure:
```bash
python src/biographical_RAG/run.py "Marcus Aurelius" --scrape
```

### 2. Interactive Q&A

Have a conversation about a historical figure:
```bash
python src/biographical_RAG/run.py "Marcus Aurelius" --qa
```

Example questions you can ask:
- "What were their main philosophical beliefs?"
- "How did they view death?"
- "What advice did they give about dealing with difficult people?"

## Project Structure

```
biographical_RAG/
├── src/
│   └── biographical_RAG/
│       ├── run.py           # CLI interface
│       ├── scraper.py       # Content collection
│       ├── rag_qa.py        # RAG implementation
│       └── __init__.py
├── scraped_content/         # Stored biographical content
├── chroma_db/              # Vector store
├── pyproject.toml          # Project configuration
└── README.md
```

## Dependencies

- OpenAI API for embeddings and question answering
- ChromaDB for vector storage
- BeautifulSoup4 for web scraping
- Other dependencies listed in pyproject.toml

## Contributing

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- OpenAI for their powerful language models
- ChromaDB for vector storage capabilities
- Project Gutenberg and Wikisource for historical content
