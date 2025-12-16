#!/usr/bin/env python3
"""
Interactive SEC Filing Query Tool
Query your SEC filing database with the LLM directly from the terminal.
"""
import requests
from sqlalchemy import create_engine, text
from config.config import OLLAMA_HOST, RAG_LLM_MODEL, DATABASE_URL
import sys

engine = create_engine(DATABASE_URL)

def get_filings():
    """Get list of available filings."""
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT f.filing_id, c.ticker, ft.filing_type, d.date, f.filing_size
            FROM fact_sec_filing f
            JOIN dim_company c ON f.company_id = c.company_id
            JOIN dim_filing_type ft ON f.filing_type_id = ft.filing_type_id
            JOIN dim_date d ON f.date_id = d.date_id
            WHERE f.filing_size > 0
            ORDER BY d.date DESC
        """))
        return result.fetchall()

def get_filing_text(filing_id):
    """Get text for a specific filing."""
    with engine.connect() as conn:
        result = conn.execute(text(f"""
            SELECT filing_text FROM fact_sec_filing WHERE filing_id = {filing_id}
        """))
        row = result.first()
        return row[0] if row else None

def query_llm(text, question):
    """Query LLM about filing text."""
    prompt = f"""Based on this SEC filing, answer the following question. Be concise and specific.

Filing excerpt:
{text[:3000]}

Question: {question}

Answer:"""
    
    try:
        response = requests.post(
            f"{OLLAMA_HOST}/api/generate",
            json={"model": RAG_LLM_MODEL, "prompt": prompt, "stream": False},
            timeout=120
        )
        response.raise_for_status()
        return response.json()['response']
    except Exception as e:
        return f"Error: {str(e)}"

def main():
    print("\n" + "="*70)
    print("🔍 SEC Filing Query Tool")
    print("="*70)
    print(f"Connected to: {DATABASE_URL}")
    print(f"LLM: {RAG_LLM_MODEL} at {OLLAMA_HOST}\n")
    
    # List available filings
    filings = get_filings()
    if not filings:
        print("❌ No SEC filings with text found in database.")
        sys.exit(1)
    
    print(f"Available filings ({len(filings)} total):\n")
    for i, filing in enumerate(filings, 1):
        filing_id, ticker, filing_type, date, size = filing
        print(f"{i:2d}. {ticker} {filing_type:6s} ({date}) - {size/1024:.0f}KB")
    
    # Interactive loop
    print("\n" + "-"*70)
    print("Select a filing by number, or type 'quit' to exit.\n")
    
    while True:
        try:
            user_input = input("📋 Select filing (1-{}): ".format(len(filings))).strip()
            
            if user_input.lower() in ['quit', 'exit', 'q']:
                print("\n👋 Goodbye!")
                break
            
            filing_idx = int(user_input) - 1
            if filing_idx < 0 or filing_idx >= len(filings):
                print("❌ Invalid selection. Try again.\n")
                continue
            
            filing = filings[filing_idx]
            filing_id, ticker, filing_type, date, size = filing
            
            print(f"\n📄 Selected: {ticker} {filing_type} ({date}) - {size/1024:.0f}KB")
            print("\nLoading filing text...")
            
            filing_text = get_filing_text(filing_id)
            if not filing_text:
                print("❌ Could not load filing text.\n")
                continue
            
            print("✓ Loaded\n")
            print("-"*70)
            print("Ask questions about this filing. Type 'back' to select another.\n")
            
            while True:
                question = input("❓ Your question: ").strip()
                
                if question.lower() in ['back', 'exit', 'quit', 'q']:
                    print()
                    break
                
                if not question:
                    continue
                
                print("\n🤖 Thinking...")
                answer = query_llm(filing_text, question)
                print(f"\n💡 Answer:\n{answer}\n")
                print("-"*70 + "\n")
        
        except ValueError:
            print("❌ Please enter a valid number.\n")
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"\n❌ Error: {str(e)}\n")

if __name__ == "__main__":
    main()
