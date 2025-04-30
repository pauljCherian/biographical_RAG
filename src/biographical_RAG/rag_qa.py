"""
Module for question answering using RAG (Retrieval Augmented Generation) on biographical content.
"""

import json
from pathlib import Path
from typing import List, Dict, Optional
import chromadb
from chromadb.utils import embedding_functions
import openai
from dotenv import load_dotenv
import os
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

class BiographicalRAG:
    def __init__(self, content_dir: str = "scraped_content"):
        """
        Initialize the RAG system.
        
        Args:
            content_dir: Directory containing the scraped content JSON files
        """
        self.content_dir = Path(content_dir)
        
        # Initialize ChromaDB
        self.chroma_client = chromadb.Client()
        
        # Use OpenAI's embedding function
        self.embedding_function = embedding_functions.OpenAIEmbeddingFunction(
            api_key=os.getenv("OPENAI_API_KEY"),
            model_name="text-embedding-3-small"
        )
        
        # Create or get the collection
        self.collection = self.chroma_client.get_or_create_collection(
            name="biographical_content",
            embedding_function=self.embedding_function
        )
        
    def load_content(self, person_name: str) -> None:
        """
        Load content for a person into the vector store.
        
        Args:
            person_name: Name of the person whose content to load
        """
        file_path = self.content_dir / f"{person_name.lower().replace(' ', '_')}_content.json"
        if not file_path.exists():
            raise FileNotFoundError(f"No content file found for {person_name}")
            
        with open(file_path, 'r', encoding='utf-8') as f:
            content = json.load(f)
            
        # Process each content piece into chunks
        for idx, entry in enumerate(content):
            # Split content into chunks of roughly 1000 characters
            text = entry['content']
            chunks = self._split_text(text, chunk_size=1000)
            
            # Add each chunk to the vector store
            for chunk_idx, chunk in enumerate(chunks):
                doc_id = f"{person_name}_{idx}_{chunk_idx}"
                metadata = {
                    'person': person_name,
                    'source_url': entry['source_url'],
                    'content_type': entry['content_type'],
                    'title': entry['title'],
                    'chunk_index': chunk_idx,
                    'total_chunks': len(chunks)
                }
                
                # Add to ChromaDB
                self.collection.add(
                    documents=[chunk],
                    metadatas=[metadata],
                    ids=[doc_id]
                )
                
        logger.info(f"Loaded content for {person_name} into vector store")
        
    def _split_text(self, text: str, chunk_size: int = 1000) -> List[str]:
        """Split text into chunks of approximately chunk_size characters."""
        chunks = []
        current_chunk = []
        current_size = 0
        
        # Split by sentences (roughly)
        sentences = text.split('.')
        
        for sentence in sentences:
            sentence = sentence.strip() + '.'
            sentence_size = len(sentence)
            
            if current_size + sentence_size > chunk_size and current_chunk:
                chunks.append(' '.join(current_chunk))
                current_chunk = []
                current_size = 0
                
            current_chunk.append(sentence)
            current_size += sentence_size
            
        if current_chunk:
            chunks.append(' '.join(current_chunk))
            
        return chunks
        
    def answer_question(self, question: str, person_name: str, n_chunks: int = 3) -> Dict:
        """
        Answer a question about a person using RAG.
        
        Args:
            question: The question to answer
            person_name: The name of the person to answer questions about
            n_chunks: Number of most relevant chunks to use
            
        Returns:
            Dict containing the answer and the sources used
        """
        # Query the vector store
        results = self.collection.query(
            query_texts=[question],
            n_results=n_chunks,
            where={"person": person_name}
        )
        
        if not results['documents'][0]:
            return {
                'answer': f"I don't have enough information about {person_name} to answer this question.",
                'sources': []
            }
            
        # Construct the prompt with context
        context = "\n\n".join(results['documents'][0])
        sources = [result['source_url'] for result in results['metadatas'][0]]
        
        prompt = f"""Based on the following excerpts about {person_name}, please answer the question as if you are {person_name}.
        You are trying to converse with the user and answer their question, trying to base your response on primary source excerpts much as possible.

Excerpts:
{context}

Question: {question}

Answer:"""

        # Get completion from OpenAI
        response = openai.chat.completions.create(
            model="gpt-4-turbo-preview",
            messages=[
                {"role": "system", "content": "You are a helpful AI assistant that answers questions about historical figures based on provided source material. Always be truthful and admit when you don't have enough information to answer a question."},
                {"role": "user", "content": prompt}
            ],
            temperature=0
        )
        
        return {
            'answer': response.choices[0].message.content,
            'sources': sources
        }

def setup_rag_system(person_name: str) -> BiographicalRAG:
    """
    Set up the RAG system for a person.
    
    Args:
        person_name: Name of the person to set up the system for
        
    Returns:
        Configured BiographicalRAG instance
    """
    rag = BiographicalRAG()
    rag.load_content(person_name)
    return rag

if __name__ == "__main__":
    # Example usage
    person = "Marcus Aurelius"
    rag = setup_rag_system(person)
    
    # Example questions
    questions = [
        "What were Marcus Aurelius's main philosophical beliefs?",
        "How did he view the concept of death?",
        "What advice did he give about dealing with difficult people?"
    ]
    
    for question in questions:
        result = rag.answer_question(question, person)
        print(f"\nQ: {question}")
        print(f"A: {result['answer']}")
        print("Sources:", result['sources']) 