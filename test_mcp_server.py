#!/usr/bin/env python3
"""Test script for MCP Financial Server."""
import asyncio
import json
import sys

# Import functions directly for testing
from mcp_financial_server import (
    get_latest_price,
    list_available_tickers,
    get_price_statistics,
    get_sec_filings,
    search_companies
)

async def test_all():
    """Run all tests."""
    print("=" * 60)
    print("MCP Financial Server - Test Suite")
    print("=" * 60)
    
    # Test 1: List available tickers
    print("\n1. Testing list_available_tickers...")
    try:
        result = await list_available_tickers()
        data = json.loads(result[0].text)
        print(f"✓ Found {data['count']} companies")
        if data['companies']:
            print(f"  Sample: {data['companies'][0]['ticker']} - {data['companies'][0]['company_name']}")
    except Exception as e:
        print(f"✗ Error: {e}")
        return False
    
    # Get a ticker for remaining tests
    if not data['companies']:
        print("No companies found in database. Please populate data first.")
        return False
    
    test_ticker = data['companies'][0]['ticker']
    print(f"\nUsing '{test_ticker}' for remaining tests...")
    
    # Test 2: Get latest price
    print(f"\n2. Testing get_latest_price for {test_ticker}...")
    try:
        result = await get_latest_price(test_ticker)
        data = json.loads(result[0].text)
        if 'latest_data' in data:
            latest = data['latest_data']
            print(f"✓ Latest price: ${latest['close_price']} on {latest['date']}")
            print(f"  Change: {latest['price_change_percent']}%")
        else:
            print(f"✗ {data}")
    except Exception as e:
        print(f"✗ Error: {e}")
    
    # Test 3: Get price statistics
    print(f"\n3. Testing get_price_statistics for {test_ticker}...")
    try:
        result = await get_price_statistics(test_ticker, days=30)
        data = json.loads(result[0].text)
        if 'statistics' in data:
            stats = data['statistics']
            print(f"✓ 30-day statistics:")
            print(f"  Average: ${stats['average_price']}")
            print(f"  Range: ${stats['min_price']} - ${stats['max_price']}")
            print(f"  Return: {stats['total_return_percent']}%")
            print(f"  Volatility: {stats['volatility_percent']}%")
        else:
            print(f"✗ {data}")
    except Exception as e:
        print(f"✗ Error: {e}")
    
    # Test 4: Get SEC filings
    print(f"\n4. Testing get_sec_filings for {test_ticker}...")
    try:
        result = await get_sec_filings(test_ticker, limit=5)
        data = json.loads(result[0].text)
        if 'filings' in data and data['filings']:
            print(f"✓ Found {data['count']} filings")
            for filing in data['filings'][:3]:
                print(f"  - {filing['filing_type']} on {filing['filing_date']}")
        else:
            print(f"  No filings found for {test_ticker}")
    except Exception as e:
        print(f"✗ Error: {e}")
    
    # Test 5: Search companies
    print(f"\n5. Testing search_companies...")
    try:
        result = await search_companies("tech")
        data = json.loads(result[0].text)
        print(f"✓ Search for 'tech' returned {data['count']} results")
        if data['results']:
            for company in data['results'][:3]:
                print(f"  - {company['ticker']}: {company['company_name']}")
    except Exception as e:
        print(f"✗ Error: {e}")
    
    print("\n" + "=" * 60)
    print("Tests completed!")
    print("=" * 60)
    return True

if __name__ == "__main__":
    try:
        success = asyncio.run(test_all())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nTests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nFatal error: {e}")
        sys.exit(1)
