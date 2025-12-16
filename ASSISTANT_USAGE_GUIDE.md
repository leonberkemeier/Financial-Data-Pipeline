# Financial Assistant Usage Guide

Complete guide for using the financial data query tools.

## Overview

This project provides multiple ways to query financial data:

1. **Financial Assistant** - Unified interface (recommended)
2. **Test MCP Client** - Demonstrates LLM tool calling
3. **MCP Server** - Direct tool access via MCP protocol
4. **RAG Demo** - Direct SEC filing queries

## Quick Start

### Recommended: Use Financial Assistant

```bash
# Interactive mode (ask multiple questions)
python financial_assistant.py

# Single question
python financial_assistant.py --query "What's Apple's stock price?"
```

The assistant automatically routes your question to the right backend (MCP or RAG).

---

## 1. Financial Assistant (`financial_assistant.py`)

### Description
Unified interface combining MCP tools (price data) and RAG (SEC filing analysis). The LLM automatically determines which tools to use based on your question.

### Features
- **Automatic routing** - Decides whether to use MCP or RAG
- **Natural language** - Ask questions in plain English
- **Multi-tool support** - Can use multiple tools in one query
- **Interactive mode** - Conversational interface

### Usage

#### Interactive Mode
```bash
python financial_assistant.py
```

Start a conversation and ask multiple questions:

```
❓ Your question: What's Apple's current stock price?
❓ Your question: Compare AAPL and MSFT
❓ Your question: What are NVDA's business risks?
❓ Your question: exit
```

#### Single Query Mode
```bash
# Ask one question and exit
python financial_assistant.py --query "What's Apple's stock price?"

# Or use short form
python financial_assistant.py -q "Compare AAPL and MSFT"
```

### Example Questions

#### Stock Prices (Uses MCP)
```bash
python financial_assistant.py -q "What's Apple's current stock price?"
python financial_assistant.py -q "Show me AAPL price for the last 7 days"
python financial_assistant.py -q "What's the latest price for TSLA?"
```

#### Statistics & Comparisons (Uses MCP)
```bash
python financial_assistant.py -q "Compare AAPL and MSFT performance"
python financial_assistant.py -q "What's NVDA's 30-day return and volatility?"
python financial_assistant.py -q "Compare AAPL, GOOGL, and MSFT over 60 days"
```

#### SEC Filing Analysis (Uses RAG)
```bash
python financial_assistant.py -q "What are Apple's main business risks?"
python financial_assistant.py -q "What does Tesla's 10-K say about revenue?"
python financial_assistant.py -q "Summarize NVDA's risk factors"
```

#### Company Information (Uses MCP)
```bash
python financial_assistant.py -q "List all available tickers"
python financial_assistant.py -q "Search for tech companies"
python financial_assistant.py -q "What SEC filings does AAPL have?"
```

#### Combined Queries (Uses Both!)
```bash
python financial_assistant.py -q "How has NVDA performed, and what are their risks?"
```

### How It Works

1. **Question Analysis**: LLM analyzes your question
2. **Tool Selection**: Decides which tool(s) to use:
   - Price data → MCP tools
   - SEC filing content → RAG
   - Company search → MCP tools
3. **Data Retrieval**: Calls selected tools
4. **Answer Generation**: Synthesizes natural language response

### Configuration

The assistant uses these settings from `.env`:
- `OLLAMA_HOST` - Ollama server address
- `RAG_LLM_MODEL` - LLM model for reasoning and answers
- `DATABASE_URL` - Database connection

### Troubleshooting

**LLM not responding:**
```bash
# Check Ollama is running
curl http://100.102.213.61:11434/api/tags
```

**No price data:**
```bash
# Verify database has data
python test_mcp_server.py
```

**SEC queries failing:**
```bash
# Check RAG embeddings exist
python rag_demo.py --query "test"
```

---

## 2. Test MCP Client (`test_mcp_client.py`)

### Description
Demonstration of how an LLM uses MCP tools. Shows the tool calling process step-by-step. This is educational - shows what happens under the hood.

### Usage

```bash
python test_mcp_client.py
```

Runs predefined demo questions:
1. What is Apple's current stock price?
2. Compare AAPL and MSFT over the last 30 days
3. What SEC filings does NVDA have?

### Output Example

```
============================================================
MCP Financial Server + LLM Demo
============================================================

🤔 Question: What is Apple's current stock price?

🤖 LLM Response:
{"tool": "get_latest_price", "arguments": {"ticker": "AAPL"}}

🔧 Calling tool: get_latest_price({'ticker': 'AAPL'})

📊 Tool Result:
{
  "ticker": "AAPL",
  "latest_data": {
    "date": "2025-12-16",
    "close_price": 274.47,
    "price_change": 1.65,
    "price_change_percent": 0.60,
    "volume": 20386278
  }
}

💬 Final Answer:
Apple's current stock price is $274.47...
```

### Key Features
- Shows LLM reasoning
- Displays tool selection process
- Prints raw tool results
- Demonstrates JSON parsing

### Use Cases
- **Learning**: Understand how LLM tool calling works
- **Debugging**: See exactly what tools return
- **Testing**: Quick verification of MCP tools
- **Development**: Template for building custom clients

### Limitations
- Simplified tool calling (not full MCP protocol)
- Fixed demo questions
- No interactive mode
- Basic error handling

---

## 3. Direct Tool Testing (`test_mcp_server.py`)

### Description
Tests MCP tools directly without LLM. Fast way to verify tools work.

### Usage

```bash
python test_mcp_server.py
```

### Output

```
============================================================
MCP Financial Server - Test Suite
============================================================

1. Testing list_available_tickers...
✓ Found 12 companies
  Sample: AAPL - AAPL

2. Testing get_latest_price for AAPL...
✓ Latest price: $274.47 on 2025-12-16
  Change: 0.60%

3. Testing get_price_statistics for AAPL...
✓ 30-day statistics:
  Average: $276.29
  Range: $266.25 - $286.19
  Return: 2.62%
  Volatility: 0.9%

4. Testing get_sec_filings for AAPL...
✓ Found 4 filings
  - 10-K on 2025-10-31
  - 10-Q on 2025-08-01

5. Testing search_companies...
✓ Search for 'tech' returned 0 results

============================================================
Tests completed!
============================================================
```

### Use Cases
- Quick health check
- Verify database connectivity
- Test after data updates
- Validate tool functionality

---

## Comparison Table

| Feature | Financial Assistant | Test MCP Client | Test MCP Server | RAG Demo |
|---------|-------------------|----------------|----------------|----------|
| **Automatic tool selection** | ✅ Yes | ✅ Yes | ❌ No | ❌ No |
| **Interactive mode** | ✅ Yes | ❌ No | ❌ No | ✅ Yes |
| **Natural language** | ✅ Yes | ✅ Yes | ❌ No | ✅ Yes |
| **MCP tools** | ✅ Yes | ✅ Yes | ✅ Yes | ❌ No |
| **RAG/SEC filings** | ✅ Yes | ❌ No | ❌ No | ✅ Yes |
| **Shows reasoning** | ✅ Yes | ✅ Yes | ❌ No | ❌ No |
| **Best for** | Production use | Learning | Testing | SEC queries only |

---

## Available Tools Reference

### MCP Tools (Price Data)

#### get_latest_price
Get the most recent stock price.
```python
{"ticker": "AAPL"}
```

#### get_price_statistics
Calculate statistics over a period.
```python
{"ticker": "AAPL", "days": 30}
```

#### compare_stocks
Compare multiple stocks side-by-side.
```python
{"tickers": ["AAPL", "MSFT", "GOOGL"], "days": 30}
```

#### list_available_tickers
List all companies in database.
```python
{}  # No parameters
```

#### get_sec_filings
Get SEC filing metadata.
```python
{"ticker": "AAPL", "filing_type": "10-K", "limit": 5}
```

#### search_companies
Search by name, ticker, sector.
```python
{"query": "tech"}
```

### RAG Tool (SEC Filing Content)

#### query_sec_filings
Search SEC filing text content.
```python
{"question": "What are Apple's business risks?"}
```

---

## Architecture

```
┌────────────────────────────────────────────────────┐
│         financial_assistant.py                     │
│  (Unified Interface - Recommended)                 │
└───────────┬────────────────────────┬───────────────┘
            │                        │
            │                        │
     ┌──────▼──────┐          ┌─────▼──────┐
     │  MCP Tools  │          │  RAG System│
     │             │          │            │
     │ • Prices    │          │ • Semantic │
     │ • Stats     │          │   Search   │
     │ • Filings   │          │ • ChromaDB │
     └──────┬──────┘          └─────┬──────┘
            │                        │
            │                        │
     ┌──────▼────────────────────────▼──────┐
     │         SQLite Database               │
     │  • fact_stock_price                   │
     │  • fact_sec_filing                    │
     │  • dim_company                        │
     └───────────────────────────────────────┘
```

---

## Environment Setup

### Required Configuration (`.env`)

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

### Required Python Packages

```bash
pip install mcp requests chromadb sqlalchemy pandas ollama loguru
```

---

## Performance Tips

### Speed Optimization
1. **Use specific tools directly** when you know what you need:
   ```bash
   # Faster
   python test_mcp_server.py
   
   # Slower (requires 2 LLM calls)
   python financial_assistant.py -q "What's AAPL's price?"
   ```

2. **Batch questions** in interactive mode instead of multiple single queries

3. **Cache results** for frequently asked questions

### Resource Usage
- **Financial Assistant**: 2 LLM calls per query (routing + answer)
- **Test MCP Client**: 2 LLM calls per query (tool selection + answer)
- **Direct tools**: No LLM calls (instant)
- **RAG queries**: 1 LLM call + embedding generation

---

## Error Handling

### Common Issues

**"Error: Could not connect to Ollama"**
```bash
# Verify Ollama is running
curl http://100.102.213.61:11434/api/tags

# Check .env has correct OLLAMA_HOST
cat .env | grep OLLAMA_HOST
```

**"No price data found for ticker"**
```bash
# List available tickers
python financial_assistant.py -q "List available tickers"

# Or check database
sqlite3 financial_data.db "SELECT ticker FROM dim_company;"
```

**"No relevant information found in the database" (RAG)**
```bash
# Check embeddings exist
python -c "import chromadb; client = chromadb.PersistentClient(path='data/chromadb'); coll = client.get_collection('sec_filings'); print(f'Embeddings: {coll.count()}')"

# Reinitialize if needed
python rag_demo.py --init --limit 1
```

**"LLM response wasn't valid JSON"**
- The LLM failed to format its response correctly
- Try again - this is usually intermittent
- Consider using a more capable model

---

## Advanced Usage

### Custom Tool Integration

Add new tools to `financial_assistant.py`:

```python
# 1. Define in TOOLS dict
TOOLS['my_custom_tool'] = {
    'function': my_tool_function,
    'description': 'What the tool does',
    'params': ['param1', 'param2']
}

# 2. Implement the function
async def my_tool_function(param1, param2):
    # Your logic here
    result = {"data": "value"}
    return [TextContent(type="text", text=json.dumps(result))]

# 3. Add handler in call_tool()
if tool_name == 'my_custom_tool':
    return await my_tool_function(**kwargs)
```

### Using Different LLMs

Change the model in `.env`:
```bash
# Use a different Ollama model
RAG_LLM_MODEL=llama3.2:latest

# Or use a larger model for better reasoning
RAG_LLM_MODEL=qwen2.5:latest
```

### Extending RAG

Add more SEC filings to embeddings:
```bash
# Initialize all filings
python rag_demo.py --init

# Or specific ticker
python rag_demo.py --init --ticker TSLA
```

---

## Workflow Examples

### Daily Price Check
```bash
#!/bin/bash
# check_prices.sh

python financial_assistant.py -q "What are today's prices for AAPL, MSFT, and GOOGL?"
```

### Weekly Analysis
```bash
#!/bin/bash
# weekly_analysis.sh

python financial_assistant.py -q "Compare AAPL, MSFT, GOOGL performance over 7 days"
python financial_assistant.py -q "What are the latest SEC filings for these companies?"
```

### Research Report
```bash
#!/bin/bash
# research.sh

TICKER=$1
python financial_assistant.py -q "What's ${TICKER}'s 30-day performance?"
python financial_assistant.py -q "What are ${TICKER}'s main business risks?"
python financial_assistant.py -q "What recent SEC filings does ${TICKER} have?"
```

---

## Related Documentation

- `MCP_SERVER_README.md` - MCP server details and configuration
- `RAG_EMBEDDING_FIXES.md` - RAG system troubleshooting
- `README.md` - Project overview
- `QUICKSTART.md` - Initial setup guide

---

## Support & Troubleshooting

### Debug Mode

Enable verbose logging:
```python
# In financial_assistant.py
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Testing Connectivity

```bash
# Test database
sqlite3 financial_data.db "SELECT COUNT(*) FROM fact_stock_price;"

# Test Ollama
curl http://100.102.213.61:11434/api/generate -d '{"model":"mistral:latest","prompt":"test"}'

# Test RAG
python rag_demo.py --query "test"
```

### Performance Profiling

```bash
# Time a query
time python financial_assistant.py -q "What's AAPL's price?"

# Profile with cProfile
python -m cProfile -s cumtime financial_assistant.py -q "test" 2>&1 | head -20
```

---

## Best Practices

1. **Use Financial Assistant** for ad-hoc queries
2. **Use direct tools** for automation/scripts
3. **Cache frequently used data** in your applications
4. **Monitor Ollama resource usage** for heavy workloads
5. **Keep embeddings updated** when adding new SEC filings
6. **Use specific tickers** instead of company names for accuracy
7. **Batch related questions** in interactive mode
8. **Check tool output** if answers seem incorrect

---

## Changelog

### 2025-12-16
- Created unified financial assistant
- Added test MCP client demonstration
- Documented all query interfaces
- Integrated MCP and RAG systems

---

## License

See project LICENSE file.
