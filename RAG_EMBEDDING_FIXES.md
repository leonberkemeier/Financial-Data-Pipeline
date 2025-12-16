# RAG Embedding Issues and Fixes

## Date
December 16, 2025

## Problem Summary
The RAG (Retrieval-Augmented Generation) system was failing to create embeddings for SEC filings, encountering HTTP 500 errors from the Ollama embedding service.

## Root Causes Identified

### 1. Chunk Size Too Large
**Issue**: Chunks were being created with 100 words, resulting in ~1,888 characters of text being sent to the embedding API, which exceeded Ollama's limits.

**Evidence**:
- Original chunk size: 100 words → ~1,888 characters
- Ollama embedding API was rejecting requests with 500 errors
- Testing showed that smaller chunks (<500 chars) worked successfully

**Fix**:
- Reduced chunk size from 100 words to 50 words
- Added character limit check BEFORE normalization (500 chars max)
- This ensures chunks stay within Ollama's processing limits

### 2. Character Limit Applied After Normalization
**Issue**: The 1000 character limit was applied AFTER text normalization, meaning chunks could exceed limits during the actual API call.

**Fix**:
- Moved character limit check to occur BEFORE normalization
- Reduced limit from 1000 to 500 characters for safety margin

### 3. Uninitialized Embedding Variable
**Issue**: When all retry attempts failed, the `embedding` variable was undefined, causing "list index out of range" errors when trying to store it.

**Fix**:
- Initialize `embedding = None` before retry loop
- Check `if embedding is not None` before attempting to store in ChromaDB
- Properly skip failed chunks without crashing

## Configuration Changes

### Before
```python
chunk_size = 100  # words
# Character limit after normalization
if len(chunk_text) > 1000:
    chunk_text = chunk_text[:1000]
```

### After
```python
chunk_size = 50  # words
# Character limit BEFORE normalization
if len(chunk_text) > 500:
    chunk_text = chunk_text[:500]
```

## API Parameter Clarification

### Ollama Embeddings API
The correct parameter for the Ollama embeddings API is `"prompt"`, not `"input"`.

**Correct Usage**:
```python
{
    "model": "nomic-embed-text",
    "prompt": "text to embed"
}
```

**Returns**:
```python
{
    "embedding": [0.123, 0.456, ...]  # 768-dimensional vector
}
```

## Results

### Successful Initialization
- **Filing Processed**: NVDA 10-Q (2025-11-19)
- **Embeddings Created**: 4,671 chunks
- **Storage Location**: `data/chromadb/chroma.sqlite3`
- **Exit Status**: Success (0)

### Test Query Results
**Query**: "What are the main business risks for NVDA?"

**Response**: Successfully retrieved 3 relevant document chunks and generated a comprehensive answer using Mistral LLM, citing:
1. Risks from Item 1A of Annual/Quarterly Reports
2. Manufacturing lead times and supply/demand mismatches
3. Acquisition and strategic investment risks

## Files Modified
- `rag_demo.py`: Updated chunk size, character limits, and embedding initialization logic

## Environment Configuration

### Required Models
- **Embedding Model**: `nomic-embed-text:latest` (768 dimensions)
- **LLM Model**: `mistral:latest` (or any compatible Ollama model)

### .env Configuration
```bash
# Database
DATABASE_URL=sqlite:///financial_data.db

# Ollama Server
OLLAMA_HOST=http://100.102.213.61:11434

# RAG Configuration
RAG_LLM_MODEL=mistral:latest
RAG_EMBEDDING_MODEL=nomic-embed-text
RAG_TOP_K_RESULTS=3
```

## Usage

### Initialize Embeddings
```bash
# Process all filings
python rag_demo.py --init

# Process specific ticker
python rag_demo.py --init --ticker AAPL

# Limit number of filings
python rag_demo.py --init --limit 5
```

### Query System
```bash
# Single query
python rag_demo.py --query "What are Apple's main risks?"

# Interactive mode
python rag_demo.py --interactive
```

## Performance Notes
- Chunk size of 50 words provides good balance between context and API reliability
- Each filing generates approximately 4,000-5,000 embedding chunks
- Processing time: ~2-3 minutes per filing (depending on size and network latency)
- Storage: ~164KB for ChromaDB with 4,671 embeddings

## Debugging Tools
Created `debug_embedding_chars.py` to analyze chunks and identify problematic content:
- Tests chunks against Ollama API
- Identifies non-ASCII characters
- Compares normalized vs. original text
- Reports which chunks fail and why

## Recommendations
1. Keep chunk size at 50 words for stability
2. Ensure character limit (500 chars) is applied before any processing
3. Monitor Ollama server logs for memory/performance issues
4. Consider batch processing for large numbers of filings
5. Implement progress tracking for long-running embedding jobs

## Future Improvements
- Add progress bar for embedding initialization
- Implement chunking strategy that preserves sentence boundaries
- Add embedding quality metrics
- Consider using smaller embedding models for faster processing
- Implement incremental updates (only embed new/changed filings)
