"""
RAG (Retrieval-Augmented Generation) Demo for SEC Filings.

This script demonstrates a complete RAG system that:
1. Creates embeddings from SEC filing text
2. Performs semantic search over filings
3. Generates answers using Ollama LLM
"""
import sys
import argparse
from loguru import logger
from sqlalchemy import create_engine, text
import pandas as pd
from typing import List, Dict
import ollama
import chromadb
from chromadb.config import Settings

from config.config import (
    DATABASE_URL, 
    OLLAMA_HOST, 
    RAG_LLM_MODEL, 
    RAG_EMBEDDING_MODEL,
    RAG_TOP_K_RESULTS,
    RAG_CHROMA_PATH
)
from src.analyzers import FilingAnalyzer


class RAGSystem:
    """RAG system for SEC filing Q&A."""
    
    def __init__(self):
        """Initialize RAG system with database and vector store."""
        logger.info("Initializing RAG system...")
        
        # Database connection
        self.engine = create_engine(DATABASE_URL)
        
        # Ollama client (via Tailscale)
        self.ollama_client = ollama.Client(host=OLLAMA_HOST)
        logger.info(f"Connected to Ollama at {OLLAMA_HOST}")
        
        # ChromaDB for vector storage
        self.chroma_client = chromadb.PersistentClient(
            path=str(RAG_CHROMA_PATH),
            settings=Settings(anonymized_telemetry=False)
        )
        
        self.collection = self.chroma_client.get_or_create_collection(
            name="sec_filings",
            metadata={"description": "SEC filing sections with embeddings"}
        )
        
        # Filing analyzer
        self.analyzer = FilingAnalyzer()
        
        logger.info("RAG system initialized")
    
    def initialize_embeddings(self, ticker: str = None, limit: int = None):
        """
        Create embeddings for all SEC filings in the database.
        
        Args:
            ticker: Optional ticker to filter by
            limit: Optional limit on number of filings
        """
        logger.info("Fetching SEC filings from database...")
        
        # Build query
        query = """
            SELECT 
                f.filing_id,
                c.ticker,
                ft.filing_type,
                d.date as filing_date,
                f.filing_text,
                f.filing_url
            FROM fact_sec_filing f
            JOIN dim_company c ON f.company_id = c.company_id
            JOIN dim_filing_type ft ON f.filing_type_id = ft.filing_type_id
            JOIN dim_date d ON f.date_id = d.date_id
            WHERE f.filing_text IS NOT NULL
        """
        
        params = {}
        if ticker:
            query += " AND c.ticker = :ticker"
            params['ticker'] = ticker
        
        query += " ORDER BY d.date DESC"
        
        if limit:
            query += f" LIMIT {limit}"
        
        filings_df = pd.read_sql(text(query), self.engine, params=params)
        
        if filings_df.empty:
            logger.warning("No filings found with text. Run sec_etl_pipeline.py first!")
            return
        
        logger.info(f"Found {len(filings_df)} filings. Creating embeddings...")
        
        total_chunks = 0
        
        for idx, filing in filings_df.iterrows():
            logger.info(f"Processing {filing['ticker']} {filing['filing_type']} "
                       f"({idx+1}/{len(filings_df)})...")
            
            # Extract sections
            sections = self.analyzer.extract_all_sections(filing['filing_text'])
            
            if not sections:
                logger.warning(f"  No sections found, skipping")
                continue
            
            # Create chunks from sections
            for section_name, section_text in sections.items():
                # Split long sections into chunks (max ~1000 words)
                words = section_text.split()
                chunk_size = 1000
                
                for i in range(0, len(words), chunk_size):
                    chunk_text = " ".join(words[i:i+chunk_size])
                    
                    if len(chunk_text) < 100:  # Skip very small chunks
                        continue
                    
                    chunk_id = f"{filing['ticker']}_{filing['filing_date']}_{section_name}_{i}"
                    
                    # Generate embedding using Ollama
                    try:
                        response = self.ollama_client.embeddings(
                            model=RAG_EMBEDDING_MODEL,
                            prompt=chunk_text
                        )
                        embedding = response['embedding']
                        
                        # Store in ChromaDB
                        self.collection.add(
                            ids=[chunk_id],
                            embeddings=[embedding],
                            documents=[chunk_text],
                            metadatas=[{
                                'ticker': filing['ticker'],
                                'filing_type': filing['filing_type'],
                                'filing_date': str(filing['filing_date']),
                                'section': section_name,
                                'filing_url': filing['filing_url'],
                                'chunk_index': i // chunk_size
                            }]
                        )
                        
                        total_chunks += 1
                        
                    except Exception as e:
                        logger.error(f"  Error creating embedding: {str(e)}")
                        continue
            
            logger.info(f"  Created {len(sections)} section chunks")
        
        logger.info(f"✓ Successfully created {total_chunks} embeddings")
        logger.info(f"✓ Saved to {RAG_CHROMA_PATH}")
    
    def query(self, question: str, verbose: bool = True) -> Dict:
        """
        Answer a question using RAG.
        
        Args:
            question: User's question
            verbose: Whether to print detailed output
            
        Returns:
            Dictionary with answer and sources
        """
        if verbose:
            print(f"\n🔍 Searching SEC filings for: '{question}'")
        
        # Generate embedding for the question
        try:
            response = self.ollama_client.embeddings(
                model=RAG_EMBEDDING_MODEL,
                prompt=question
            )
            question_embedding = response['embedding']
        except Exception as e:
            logger.error(f"Error generating question embedding: {str(e)}")
            return {'answer': f"Error: Could not connect to Ollama at {OLLAMA_HOST}", 'sources': []}
        
        # Search vector database
        results = self.collection.query(
            query_embeddings=[question_embedding],
            n_results=RAG_TOP_K_RESULTS
        )
        
        if not results['documents'][0]:
            return {
                'answer': "No relevant information found in the database.",
                'sources': []
            }
        
        # Extract context and metadata
        contexts = results['documents'][0]
        metadatas = results['metadatas'][0]
        
        if verbose:
            print(f"✓ Found {len(contexts)} relevant sections")
            for meta in metadatas:
                print(f"  - {meta['ticker']} {meta['filing_type']} "
                      f"({meta['filing_date']}) - {meta['section']}")
        
        # Build prompt with context
        context_text = "\n\n---\n\n".join([
            f"Source: {meta['ticker']} {meta['filing_type']} filed {meta['filing_date']}, "
            f"Section: {meta['section']}\n\n{doc}"
            for doc, meta in zip(contexts, metadatas)
        ])
        
        prompt = f"""Based on the following excerpts from SEC filings, answer the question. 
Be specific and cite which company and filing type the information comes from.

Context from SEC Filings:
{context_text}

Question: {question}

Answer (be concise and specific, citing sources):"""
        
        # Generate answer using Ollama
        if verbose:
            print(f"\n🤖 Generating answer using {RAG_LLM_MODEL}...")
        
        try:
            response = self.ollama_client.generate(
                model=RAG_LLM_MODEL,
                prompt=prompt
            )
            answer = response['response']
        except Exception as e:
            logger.error(f"Error generating answer: {str(e)}")
            return {
                'answer': f"Error generating answer: {str(e)}",
                'sources': metadatas
            }
        
        return {
            'answer': answer,
            'sources': metadatas
        }
    
    def interactive_mode(self):
        """Run interactive Q&A session."""
        print("\n" + "="*60)
        print("🤖 SEC Filing RAG - Interactive Mode")
        print("="*60)
        print("Ask questions about SEC filings in the database.")
        print("Type 'exit' or 'quit' to end the session.\n")
        
        while True:
            try:
                question = input("❓ Your question: ").strip()
                
                if question.lower() in ['exit', 'quit', 'q']:
                    print("\n👋 Goodbye!")
                    break
                
                if not question:
                    continue
                
                result = self.query(question, verbose=True)
                
                print(f"\n💡 Answer:")
                print(result['answer'])
                
                print(f"\n📚 Sources:")
                for source in result['sources']:
                    print(f"  • {source['ticker']} {source['filing_type']} "
                          f"({source['filing_date']}) - {source['section']}")
                    if source.get('filing_url'):
                        print(f"    {source['filing_url']}")
                
                print("\n" + "-"*60 + "\n")
                
            except KeyboardInterrupt:
                print("\n\n👋 Goodbye!")
                break
            except Exception as e:
                logger.error(f"Error: {str(e)}")
                print(f"\n❌ Error: {str(e)}\n")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="RAG Demo for SEC Filings",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Initialize embeddings for all filings
  python rag_demo.py --init
  
  # Initialize for specific ticker
  python rag_demo.py --init --ticker AAPL
  
  # Ask a question
  python rag_demo.py --query "What are Apple's main risks?"
  
  # Interactive mode
  python rag_demo.py --interactive
        """
    )
    
    parser.add_argument(
        '--init',
        action='store_true',
        help='Initialize embeddings (run once before querying)'
    )
    parser.add_argument(
        '--ticker',
        help='Filter by ticker when initializing'
    )
    parser.add_argument(
        '--limit',
        type=int,
        help='Limit number of filings to process'
    )
    parser.add_argument(
        '--query',
        help='Ask a question about SEC filings'
    )
    parser.add_argument(
        '--interactive',
        action='store_true',
        help='Start interactive Q&A session'
    )
    
    args = parser.parse_args()
    
    # Initialize RAG system
    try:
        rag = RAGSystem()
    except Exception as e:
        logger.error(f"Failed to initialize RAG system: {str(e)}")
        logger.error(f"Make sure Ollama is running at {OLLAMA_HOST}")
        sys.exit(1)
    
    # Initialize embeddings
    if args.init:
        rag.initialize_embeddings(ticker=args.ticker, limit=args.limit)
        print("\n✓ Embeddings initialized! You can now query the system.")
        return
    
    # Single query
    if args.query:
        result = rag.query(args.query, verbose=True)
        print(f"\n💡 Answer:")
        print(result['answer'])
        print(f"\n📚 Sources:")
        for source in result['sources']:
            print(f"  • {source['ticker']} {source['filing_type']} "
                  f"({source['filing_date']}) - {source['section']}")
        return
    
    # Interactive mode
    if args.interactive:
        rag.interactive_mode()
        return
    
    # No arguments - show help
    parser.print_help()


if __name__ == "__main__":
    main()
