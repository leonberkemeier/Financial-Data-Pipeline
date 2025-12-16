"""Debug script to find problematic characters causing 500 errors in embeddings."""
import sys
import requests
from sqlalchemy import create_engine, text
import pandas as pd
from config.config import DATABASE_URL, OLLAMA_HOST, RAG_EMBEDDING_MODEL
from src.analyzers import FilingAnalyzer
import unicodedata

def analyze_chunk(chunk_text):
    """Analyze a chunk for special characters."""
    non_ascii = []
    for i, char in enumerate(chunk_text):
        if ord(char) > 127:  # Non-ASCII
            non_ascii.append({
                'pos': i,
                'char': char,
                'code': ord(char),
                'hex': hex(ord(char)),
                'name': unicodedata.name(char, 'UNKNOWN')
            })
    return non_ascii

def test_embedding(text, ollama_host):
    """Test if a text chunk can be embedded successfully."""
    try:
        response = requests.post(
            f"{ollama_host}/api/embeddings",
            json={"model": RAG_EMBEDDING_MODEL, "prompt": text},
            timeout=10
        )
        return response.status_code, response.text
    except Exception as e:
        return -1, str(e)

def main():
    print("Fetching filing from database...")
    engine = create_engine(DATABASE_URL)
    
    query = """
        SELECT 
            f.filing_id,
            c.ticker,
            ft.filing_type,
            f.filing_text
        FROM fact_sec_filing f
        JOIN dim_company c ON f.company_id = c.company_id
        JOIN dim_filing_type ft ON f.filing_type_id = ft.filing_type_id
        WHERE f.filing_text IS NOT NULL
        LIMIT 1
    """
    
    filing = engine.connect().execute(text(query)).fetchone()
    
    if not filing:
        print("No filing found")
        return
    
    print(f"Processing {filing.ticker} {filing.filing_type}...")
    
    analyzer = FilingAnalyzer()
    sections = analyzer.extract_all_sections(filing.filing_text)
    
    if not sections or all(len(text) < 100 for text in sections.values()):
        sections = {'full_document': filing.filing_text}
    
    ollama_host = OLLAMA_HOST.rstrip('/')
    chunk_num = 0
    failed_chunks = []
    
    for section_name, section_text in sections.items():
        words = section_text.split()
        chunk_size = 100
        
        for i in range(0, min(len(words), 2000), chunk_size):  # Test first 2000 words
            chunk_text = " ".join(words[i:i+chunk_size])
            
            if len(chunk_text) < 50:
                continue
            
            # Test without normalization first
            chunk_num += 1
            status, response = test_embedding(chunk_text, ollama_host)
            
            if status != 200:
                print(f"\n❌ Chunk {chunk_num} FAILED (status: {status})")
                print(f"   Section: {section_name}, words {i}-{i+chunk_size}")
                print(f"   Chunk length: {len(chunk_text)}")
                
                # Analyze characters
                non_ascii = analyze_chunk(chunk_text)
                if non_ascii:
                    print(f"   Non-ASCII characters found: {len(non_ascii)}")
                    for char_info in non_ascii[:10]:  # Show first 10
                        print(f"      {char_info}")
                
                # Test with normalization
                normalized = analyzer._normalize(chunk_text)
                status2, _ = test_embedding(normalized, ollama_host)
                print(f"   After normalization: status {status2}")
                
                failed_chunks.append({
                    'chunk_num': chunk_num,
                    'section': section_name,
                    'original_status': status,
                    'normalized_status': status2,
                    'non_ascii_count': len(non_ascii),
                    'chunk_preview': chunk_text[:200]
                })
                
                if len(failed_chunks) >= 5:  # Stop after 5 failures
                    print(f"\n✋ Stopping after {len(failed_chunks)} failures")
                    break
            elif chunk_num % 50 == 0:
                print(f"✓ Chunk {chunk_num} OK")
        
        if len(failed_chunks) >= 5:
            break
    
    print(f"\n\n=== SUMMARY ===")
    print(f"Total chunks tested: {chunk_num}")
    print(f"Failed chunks: {len(failed_chunks)}")
    
    if failed_chunks:
        print("\n=== FAILED CHUNKS ===")
        for fc in failed_chunks:
            print(f"\nChunk #{fc['chunk_num']} - {fc['section']}")
            print(f"  Original status: {fc['original_status']}")
            print(f"  Normalized status: {fc['normalized_status']}")
            print(f"  Non-ASCII chars: {fc['non_ascii_count']}")
            print(f"  Preview: {fc['chunk_preview'][:150]}...")

if __name__ == "__main__":
    main()
