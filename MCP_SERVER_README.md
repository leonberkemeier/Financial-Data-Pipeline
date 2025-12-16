# MCP Financial Data Server

A Model Context Protocol (MCP) server that provides LLMs with access to stock price data and SEC filings from the financial database.

## Overview

This MCP server exposes 7 tools for querying financial data:

1. **get_stock_price** - Get OHLCV data for a ticker
2. **get_price_statistics** - Calculate statistics (avg, min, max, volatility, returns)
3. **compare_stocks** - Compare multiple stocks side-by-side
4. **list_available_tickers** - List all companies in the database
5. **get_sec_filings** - Get SEC filing metadata
6. **get_latest_price** - Get the most recent price for a ticker
7. **search_companies** - Search by name, ticker, sector, or industry

## Installation

The MCP server requires the `mcp` Python package:

```bash
pip install mcp
```

## Running the Server

### Standalone Mode
```bash
python mcp_financial_server.py
```

The server runs via stdio and communicates using the MCP protocol.

### Testing the Server

You can test individual tools using a simple test script:

```python
# test_mcp.py
import asyncio
import json

async def test():
    from mcp_financial_server import get_latest_price, list_available_tickers
    
    # Test getting latest price
    result = await get_latest_price("AAPL")
    print(json.loads(result[0].text))
    
    # Test listing tickers
    result = await list_available_tickers()
    data = json.loads(result[0].text)
    print(f"Available tickers: {data['count']}")

asyncio.run(test())
```

## Configuration with MCP Clients

### Claude Desktop

Add to your Claude Desktop config (`~/Library/Application Support/Claude/claude_desktop_config.json` on Mac):

```json
{
  "mcpServers": {
    "financial-data": {
      "command": "python",
      "args": [
        "/home/archy/Desktop/Server/FinancialData/financial_data_aggregator/mcp_financial_server.py"
      ],
      "env": {
        "PYTHONPATH": "/home/archy/Desktop/Server/FinancialData/financial_data_aggregator"
      }
    }
  }
}
```

### VS Code / Cursor

Add to your MCP settings:

```json
{
  "mcp.servers": [
    {
      "name": "financial-data",
      "command": "python",
      "args": ["/home/archy/Desktop/Server/FinancialData/financial_data_aggregator/mcp_financial_server.py"],
      "cwd": "/home/archy/Desktop/Server/FinancialData/financial_data_aggregator"
    }
  ]
}
```

## Tool Documentation

### get_stock_price

Get historical stock price data (OHLCV).

**Parameters:**
- `ticker` (required): Stock ticker symbol (e.g., "AAPL")
- `days` (optional): Number of recent days (default: 30)
- `start_date` (optional): Start date in YYYY-MM-DD format
- `end_date` (optional): End date in YYYY-MM-DD format

**Example:**
```json
{
  "ticker": "AAPL",
  "days": 7
}
```

**Returns:**
```json
{
  "ticker": "AAPL",
  "count": 7,
  "data": [
    {
      "date": "2025-12-16",
      "open_price": 150.25,
      "high_price": 152.10,
      "low_price": 149.80,
      "close_price": 151.50,
      "volume": 75000000,
      "price_change": 1.25,
      "price_change_percent": 0.83
    }
  ]
}
```

### get_price_statistics

Calculate price statistics over a period.

**Parameters:**
- `ticker` (required): Stock ticker symbol
- `days` (optional): Number of days for calculation (default: 30)

**Example:**
```json
{
  "ticker": "AAPL",
  "days": 30
}
```

**Returns:**
```json
{
  "ticker": "AAPL",
  "period_days": 30,
  "statistics": {
    "average_price": 150.25,
    "min_price": 145.00,
    "max_price": 155.50,
    "current_price": 151.50,
    "total_return_percent": 2.50,
    "volatility_percent": 1.25,
    "average_volume": 70000000,
    "trading_days": 21
  }
}
```

### compare_stocks

Compare multiple stocks.

**Parameters:**
- `tickers` (required): Array of ticker symbols
- `days` (optional): Period for comparison (default: 30)

**Example:**
```json
{
  "tickers": ["AAPL", "GOOGL", "MSFT"],
  "days": 30
}
```

### list_available_tickers

List all companies in the database.

**Parameters:** None

**Returns:**
```json
{
  "count": 10,
  "companies": [
    {
      "ticker": "AAPL",
      "company_name": "Apple Inc.",
      "sector": "Technology",
      "industry": "Consumer Electronics",
      "country": "USA"
    }
  ]
}
```

### get_sec_filings

Get SEC filing metadata for a ticker.

**Parameters:**
- `ticker` (required): Stock ticker symbol
- `filing_type` (optional): Filing type (e.g., "10-K", "10-Q")
- `limit` (optional): Maximum number of results (default: 10)

**Example:**
```json
{
  "ticker": "AAPL",
  "filing_type": "10-K",
  "limit": 5
}
```

**Returns:**
```json
{
  "ticker": "AAPL",
  "count": 5,
  "filings": [
    {
      "filing_type": "10-K",
      "filing_date": "2025-10-27",
      "accession_number": "0000320193-25-000123",
      "filing_url": "https://www.sec.gov/...",
      "has_text": "Yes"
    }
  ]
}
```

### get_latest_price

Get the most recent closing price.

**Parameters:**
- `ticker` (required): Stock ticker symbol

**Example:**
```json
{
  "ticker": "AAPL"
}
```

### search_companies

Search for companies.

**Parameters:**
- `query` (required): Search term (matches ticker, name, sector, industry)

**Example:**
```json
{
  "query": "tech"
}
```

## Integration with RAG System

The MCP server can be used alongside the RAG system to provide comprehensive financial analysis:

- **MCP Server**: Provides quantitative data (prices, volumes, statistics)
- **RAG System**: Provides qualitative data (business descriptions, risk factors, MD&A)

### Combined Usage Example

A user could ask: "How has Apple's stock performed recently, and what are their main business risks?"

The LLM would:
1. Call `get_price_statistics("AAPL")` via MCP to get price performance
2. Query the RAG system for risk factors from SEC filings
3. Combine both to provide a comprehensive answer

## Architecture

```
┌─────────────┐
│   LLM/AI    │
│   Client    │
└──────┬──────┘
       │ MCP Protocol
       │
┌──────▼──────────────┐
│  MCP Financial      │
│  Data Server        │
│  (stdio)            │
└──────┬──────────────┘
       │
       │ SQL Queries
       │
┌──────▼──────────────┐
│   SQLite/PostgreSQL │
│   Database          │
│                     │
│ • fact_stock_price  │
│ • fact_sec_filing   │
│ • dim_company       │
└─────────────────────┘
```

## Security Considerations

- The server only provides read-only access to the database
- No write operations are exposed
- SQL injection is prevented through parameterized queries
- Results are limited to prevent overwhelming responses

## Performance

- Average query time: <100ms for price data
- Statistics calculations: <200ms
- Large date ranges are automatically limited for safety
- Connection pooling could be added for high-volume usage

## Extending the Server

To add new tools:

1. Define the tool in `list_tools()`
2. Add handler in `call_tool()`
3. Implement the async function
4. Return `list[TextContent]` with JSON data

Example:
```python
@app.list_tools()
async def list_tools() -> list[Tool]:
    return [
        # ... existing tools ...
        Tool(
            name="my_new_tool",
            description="Description here",
            inputSchema={
                "type": "object",
                "properties": {
                    "param": {"type": "string"}
                },
                "required": ["param"]
            }
        )
    ]

@app.call_tool()
async def call_tool(name: str, arguments: Any) -> list[TextContent]:
    if name == "my_new_tool":
        return await my_new_tool(**arguments)
    # ... existing handlers ...

async def my_new_tool(param: str) -> list[TextContent]:
    # Implementation
    return [TextContent(type="text", text=json.dumps(result))]
```

## Troubleshooting

### Server won't start
- Check that `mcp` package is installed: `pip list | grep mcp`
- Verify DATABASE_URL in `.env` is correct
- Ensure database file exists

### No data returned
- Verify tickers exist: Use `list_available_tickers` tool
- Check date ranges - data may not exist for requested period
- Ensure database has been populated with data

### Connection errors
- Check that PYTHONPATH includes project directory
- Verify config file paths are absolute, not relative
- Check file permissions on database

## Future Enhancements

- [ ] Add caching for frequently requested data
- [ ] Implement connection pooling for PostgreSQL
- [ ] Add technical indicators (RSI, MACD, moving averages)
- [ ] Support for chart generation
- [ ] Real-time price updates (websocket integration)
- [ ] Portfolio analysis tools
- [ ] Correlation analysis between stocks
- [ ] Sector performance comparisons

## Related Files

- `rag_demo.py` - RAG system for SEC filing text analysis
- `config/config.py` - Database configuration
- `RAG_EMBEDDING_FIXES.md` - RAG system documentation
- `.env` - Environment variables
