#!/usr/bin/env python3
"""
MCP Server for Financial Data Aggregator

Provides tools for querying stock prices, SEC filings, and financial metrics
through the Model Context Protocol (MCP).
"""
import asyncio
import json
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import sqlite3

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from config.config import DATABASE_URL

# Initialize MCP server
app = Server("financial-data-server")

def get_db_connection():
    """Get database connection."""
    # Extract path from sqlite URL
    db_path = DATABASE_URL.replace("sqlite:///", "")
    return sqlite3.connect(db_path)

def dict_factory(cursor, row):
    """Convert sqlite row to dict."""
    fields = [column[0] for column in cursor.description]
    return dict(zip(fields, row))

@app.list_tools()
async def list_tools() -> list[Tool]:
    """List available tools."""
    return [
        Tool(
            name="get_stock_price",
            description="Get stock price data for a specific ticker and date range. Returns OHLCV (Open, High, Low, Close, Volume) data.",
            inputSchema={
                "type": "object",
                "properties": {
                    "ticker": {
                        "type": "string",
                        "description": "Stock ticker symbol (e.g., AAPL, GOOGL)"
                    },
                    "days": {
                        "type": "integer",
                        "description": "Number of recent days to retrieve (default: 30)",
                        "default": 30
                    },
                    "start_date": {
                        "type": "string",
                        "description": "Start date in YYYY-MM-DD format (optional, overrides days parameter)"
                    },
                    "end_date": {
                        "type": "string",
                        "description": "End date in YYYY-MM-DD format (optional)"
                    }
                },
                "required": ["ticker"]
            }
        ),
        Tool(
            name="get_price_statistics",
            description="Calculate price statistics (average, min, max, volatility, returns) for a ticker over a period.",
            inputSchema={
                "type": "object",
                "properties": {
                    "ticker": {
                        "type": "string",
                        "description": "Stock ticker symbol"
                    },
                    "days": {
                        "type": "integer",
                        "description": "Number of days for calculation (default: 30)",
                        "default": 30
                    }
                },
                "required": ["ticker"]
            }
        ),
        Tool(
            name="compare_stocks",
            description="Compare multiple stocks side-by-side with their latest prices and returns.",
            inputSchema={
                "type": "object",
                "properties": {
                    "tickers": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of ticker symbols to compare (e.g., ['AAPL', 'GOOGL', 'MSFT'])"
                    },
                    "days": {
                        "type": "integer",
                        "description": "Period for return calculation (default: 30)",
                        "default": 30
                    }
                },
                "required": ["tickers"]
            }
        ),
        Tool(
            name="list_available_tickers",
            description="List all available stock tickers in the database with company names and sectors.",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="get_sec_filings",
            description="Get SEC filings for a specific ticker (10-K, 10-Q, 8-K, etc.).",
            inputSchema={
                "type": "object",
                "properties": {
                    "ticker": {
                        "type": "string",
                        "description": "Stock ticker symbol"
                    },
                    "filing_type": {
                        "type": "string",
                        "description": "Type of filing (e.g., '10-K', '10-Q', '8-K'). Leave empty for all types."
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of filings to return (default: 10)",
                        "default": 10
                    }
                },
                "required": ["ticker"]
            }
        ),
        Tool(
            name="get_latest_price",
            description="Get the most recent closing price for a ticker.",
            inputSchema={
                "type": "object",
                "properties": {
                    "ticker": {
                        "type": "string",
                        "description": "Stock ticker symbol"
                    }
                },
                "required": ["ticker"]
            }
        ),
        Tool(
            name="search_companies",
            description="Search for companies by name, ticker, sector, or industry.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query (matches ticker, company name, sector, or industry)"
                    }
                },
                "required": ["query"]
            }
        )
    ]

@app.call_tool()
async def call_tool(name: str, arguments: Any) -> list[TextContent]:
    """Handle tool calls."""
    
    if name == "get_stock_price":
        return await get_stock_price(**arguments)
    elif name == "get_price_statistics":
        return await get_price_statistics(**arguments)
    elif name == "compare_stocks":
        return await compare_stocks(**arguments)
    elif name == "list_available_tickers":
        return await list_available_tickers()
    elif name == "get_sec_filings":
        return await get_sec_filings(**arguments)
    elif name == "get_latest_price":
        return await get_latest_price(**arguments)
    elif name == "search_companies":
        return await search_companies(**arguments)
    else:
        raise ValueError(f"Unknown tool: {name}")

async def get_stock_price(ticker: str, days: int = 30, start_date: Optional[str] = None, end_date: Optional[str] = None) -> list[TextContent]:
    """Get stock price data."""
    conn = get_db_connection()
    conn.row_factory = dict_factory
    cursor = conn.cursor()
    
    # Build date filter
    if start_date and end_date:
        date_filter = f"AND d.date BETWEEN '{start_date}' AND '{end_date}'"
    elif start_date:
        date_filter = f"AND d.date >= '{start_date}'"
    else:
        date_filter = f"AND d.date >= date('now', '-{days} days')"
    
    query = f"""
        SELECT 
            d.date,
            f.open_price,
            f.high_price,
            f.low_price,
            f.close_price,
            f.adjusted_close,
            f.volume,
            f.price_change,
            f.price_change_percent
        FROM fact_stock_price f
        JOIN dim_company c ON f.company_id = c.company_id
        JOIN dim_date d ON f.date_id = d.date_id
        WHERE c.ticker = ?
        {date_filter}
        ORDER BY d.date DESC
    """
    
    cursor.execute(query, (ticker.upper(),))
    results = cursor.fetchall()
    conn.close()
    
    if not results:
        return [TextContent(
            type="text",
            text=f"No price data found for ticker: {ticker}"
        )]
    
    return [TextContent(
        type="text",
        text=json.dumps({
            "ticker": ticker.upper(),
            "count": len(results),
            "data": results
        }, indent=2, default=str)
    )]

async def get_price_statistics(ticker: str, days: int = 30) -> list[TextContent]:
    """Calculate price statistics."""
    conn = get_db_connection()
    conn.row_factory = dict_factory
    cursor = conn.cursor()
    
    query = """
        SELECT 
            AVG(f.close_price) as avg_price,
            MIN(f.close_price) as min_price,
            MAX(f.close_price) as max_price,
            AVG(f.volume) as avg_volume,
            COUNT(*) as trading_days
        FROM fact_stock_price f
        JOIN dim_company c ON f.company_id = c.company_id
        JOIN dim_date d ON f.date_id = d.date_id
        WHERE c.ticker = ?
        AND d.date >= date('now', '-' || ? || ' days')
    """
    
    cursor.execute(query, (ticker.upper(), days))
    stats = cursor.fetchone()
    
    # Get first and last prices for return calculation
    query_returns = """
        SELECT close_price, date
        FROM fact_stock_price f
        JOIN dim_company c ON f.company_id = c.company_id
        JOIN dim_date d ON f.date_id = d.date_id
        WHERE c.ticker = ?
        AND d.date >= date('now', '-' || ? || ' days')
        ORDER BY d.date
    """
    
    cursor.execute(query_returns, (ticker.upper(), days))
    prices = cursor.fetchall()
    conn.close()
    
    if not prices or not stats:
        return [TextContent(
            type="text",
            text=f"No data found for ticker: {ticker}"
        )]
    
    # Calculate returns
    first_price = prices[0]['close_price']
    last_price = prices[-1]['close_price']
    total_return = ((last_price - first_price) / first_price) * 100 if first_price else 0
    
    # Calculate volatility (standard deviation of returns)
    if len(prices) > 1:
        returns = []
        for i in range(1, len(prices)):
            daily_return = ((prices[i]['close_price'] - prices[i-1]['close_price']) / prices[i-1]['close_price']) * 100
            returns.append(daily_return)
        
        avg_return = sum(returns) / len(returns)
        variance = sum((r - avg_return) ** 2 for r in returns) / len(returns)
        volatility = variance ** 0.5
    else:
        volatility = 0
    
    result = {
        "ticker": ticker.upper(),
        "period_days": days,
        "statistics": {
            "average_price": round(stats['avg_price'], 2) if stats['avg_price'] else None,
            "min_price": round(stats['min_price'], 2) if stats['min_price'] else None,
            "max_price": round(stats['max_price'], 2) if stats['max_price'] else None,
            "current_price": round(last_price, 2) if last_price else None,
            "total_return_percent": round(total_return, 2),
            "volatility_percent": round(volatility, 2),
            "average_volume": int(stats['avg_volume']) if stats['avg_volume'] else None,
            "trading_days": stats['trading_days']
        }
    }
    
    return [TextContent(
        type="text",
        text=json.dumps(result, indent=2)
    )]

async def compare_stocks(tickers: List[str], days: int = 30) -> list[TextContent]:
    """Compare multiple stocks."""
    results = []
    
    for ticker in tickers:
        stats = await get_price_statistics(ticker, days)
        if stats:
            results.append(json.loads(stats[0].text))
    
    return [TextContent(
        type="text",
        text=json.dumps({
            "comparison": results,
            "period_days": days
        }, indent=2)
    )]

async def list_available_tickers() -> list[TextContent]:
    """List all available tickers."""
    conn = get_db_connection()
    conn.row_factory = dict_factory
    cursor = conn.cursor()
    
    query = """
        SELECT 
            ticker,
            company_name,
            sector,
            industry,
            country
        FROM dim_company
        ORDER BY ticker
    """
    
    cursor.execute(query)
    results = cursor.fetchall()
    conn.close()
    
    return [TextContent(
        type="text",
        text=json.dumps({
            "count": len(results),
            "companies": results
        }, indent=2)
    )]

async def get_sec_filings(ticker: str, filing_type: Optional[str] = None, limit: int = 10) -> list[TextContent]:
    """Get SEC filings for a ticker."""
    conn = get_db_connection()
    conn.row_factory = dict_factory
    cursor = conn.cursor()
    
    filing_filter = "AND ft.filing_type = ?" if filing_type else ""
    params = [ticker.upper(), filing_type.upper()] if filing_type else [ticker.upper()]
    params.append(limit)
    
    query = f"""
        SELECT 
            ft.filing_type,
            d.date as filing_date,
            f.accession_number,
            f.filing_url,
            CASE WHEN f.filing_text IS NOT NULL THEN 'Yes' ELSE 'No' END as has_text
        FROM fact_sec_filing f
        JOIN dim_company c ON f.company_id = c.company_id
        JOIN dim_filing_type ft ON f.filing_type_id = ft.filing_type_id
        JOIN dim_date d ON f.date_id = d.date_id
        WHERE c.ticker = ?
        {filing_filter}
        ORDER BY d.date DESC
        LIMIT ?
    """
    
    cursor.execute(query, params)
    results = cursor.fetchall()
    conn.close()
    
    if not results:
        return [TextContent(
            type="text",
            text=f"No filings found for ticker: {ticker}"
        )]
    
    return [TextContent(
        type="text",
        text=json.dumps({
            "ticker": ticker.upper(),
            "count": len(results),
            "filings": results
        }, indent=2, default=str)
    )]

async def get_latest_price(ticker: str) -> list[TextContent]:
    """Get latest closing price."""
    conn = get_db_connection()
    conn.row_factory = dict_factory
    cursor = conn.cursor()
    
    query = """
        SELECT 
            d.date,
            f.close_price,
            f.price_change,
            f.price_change_percent,
            f.volume
        FROM fact_stock_price f
        JOIN dim_company c ON f.company_id = c.company_id
        JOIN dim_date d ON f.date_id = d.date_id
        WHERE c.ticker = ?
        ORDER BY d.date DESC
        LIMIT 1
    """
    
    cursor.execute(query, (ticker.upper(),))
    result = cursor.fetchone()
    conn.close()
    
    if not result:
        return [TextContent(
            type="text",
            text=f"No price data found for ticker: {ticker}"
        )]
    
    return [TextContent(
        type="text",
        text=json.dumps({
            "ticker": ticker.upper(),
            "latest_data": result
        }, indent=2, default=str)
    )]

async def search_companies(query: str) -> list[TextContent]:
    """Search for companies."""
    conn = get_db_connection()
    conn.row_factory = dict_factory
    cursor = conn.cursor()
    
    sql = """
        SELECT 
            ticker,
            company_name,
            sector,
            industry,
            country
        FROM dim_company
        WHERE ticker LIKE ? 
        OR company_name LIKE ?
        OR sector LIKE ?
        OR industry LIKE ?
        ORDER BY ticker
        LIMIT 20
    """
    
    search_term = f"%{query}%"
    cursor.execute(sql, (search_term, search_term, search_term, search_term))
    results = cursor.fetchall()
    conn.close()
    
    return [TextContent(
        type="text",
        text=json.dumps({
            "query": query,
            "count": len(results),
            "results": results
        }, indent=2)
    )]

async def main():
    """Run the MCP server."""
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )

if __name__ == "__main__":
    asyncio.run(main())
