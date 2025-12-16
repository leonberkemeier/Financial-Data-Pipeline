#!/usr/bin/env python3
"""
Simplified RAG System - Works without embeddings
Uses keyword search to find relevant filing sections, then asks LLM.
"""
import requests
from sqlalchemy import create_engine, text
from config.config import OLLAMA_HOST, RAG_LLM_MODEL, DATABASE_URL
import re

engine = create_engine(DATABASE_URL)

def search_filings(keywords, limit=3):
    """Search filings for keywords."""
    # Build search query
    where_clauses = []
    for keyword in keywords.split():
        where_clauses.append(f"LOWER(f.filing_text) LIKE '%{keyword.lower()}%'")
    
    where_condition = " OR ".join(where_clauses) if where_clauses else "1=1"
    
    query = f"""
        SELECT f.filing_id, c.ticker, ft.filing_type, d.date, 
               SUBSTR(f.filing_text, 1, 2000) as excerpt, f.filing_size
        FROM fact_sec_filing f
        JOIN dim_company c ON f.company_id = c.company_id
        JOIN dim_filing_type ft ON f.filing_type_id = ft.filing_type_id
        JOIN dim_date d ON f.date_id = d.date_id
        WHERE ({where_condition}) AND f.filing_size > 0
        LIMIT {limit}
    """
    
    with engine.connect() as conn:
        result = conn.execute(text(query))
        return result.fetchall()

def get_full_filing(filing_id):
    """Get full filing text."""
    with engine.connect() as conn:
        result = conn.execute(text(f"""
            SELECT filing_text FROM fact_sec_filing WHERE filing_id = {filing_id}
        """))
        row = result.first()
        return row[0] if row else None

def query_llm(context, question):
    """Ask LLM a question based on context."""
    prompt = f"""Based on this SEC filing context, answer the question accurately and concisely.

CONTEXT:
{context[:4000]}

QUESTION: {question}

ANSWER:"""
    
    try:
        response = requests.post(
            f"{OLLAMA_HOST}/api/generate",
            json={"model": RAG_LLM_MODEL, "prompt": prompt, "stream": False},
            timeout=180
        )
        response.raise_for_status()
        return response.json()['response']
    except Exception as e:
        return f"Error: {str(e)}"

def main():
    print("\n" + "="*70)
    print("🚀 RAG System - Keyword Search Mode")
    print("="*70)
    print(f"LLM: {RAG_LLM_MODEL}")
    print(f"Server: {OLLAMA_HOST}")
    print("\nAsk questions about SEC filings. Keywords will be searched.")
    print("Type 'quit' to exit.\n")
    print("-"*70 + "\n")
    
    while True:
        try:
            question = input("❓ Your question: ").strip()
            
            if question.lower() in ['quit', 'exit', 'q']:
                print("\n👋 Goodbye!")
                break
            
            if not question:
                continue
            
            # Extract keywords (simple approach)
            keywords = " ".join([w for w in question.split() if len(w) > 3])
            
            print(f"\n🔍 Searching for: {keywords}")
            results = search_filings(keywords, limit=3)
            
            if not results:
                print("❌ No matching filings found.\n")
                continue
            
            print(f"✓ Found {len(results)} matching filing(s)")
            
            # Combine context from all results
            context_parts = []
            for filing_id, ticker, filing_type, date, excerpt, size in results:
                context_parts.append(f"[{ticker} {filing_type} ({date})]:\n{excerpt}\n")
            
            combined_context = "\n---\n".join(context_parts)
            
            print("🤖 Asking LLM...\n")
            answer = query_llm(combined_context, question)
            
            print("💡 Answer:")
            print("-" * 70)
            print(answer)
            print("-" * 70 + "\n")
        
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"\n❌ Error: {str(e)}\n")

if __name__ == "__main__":
    main()
