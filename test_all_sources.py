"""Unified test script for all data sources."""
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
from loguru import logger

# Load environment variables from .env file
load_dotenv()

from src.extractors.yahoo_finance import YahooFinanceExtractor
from src.extractors.crypto_gecko import CoinGeckoExtractor
from src.extractors.fred_bond import FREDBondExtractor
from src.extractors.yahoo_bond import YahooBondExtractor
from src.extractors.economic_indicators import EconomicIndicatorsExtractor


def print_section_header(title):
    """Print a formatted section header."""
    logger.info("\n" + "=" * 80)
    logger.info(title)
    logger.info("=" * 80)


def test_stocks():
    """Test stock data extraction."""
    print_section_header("TESTING STOCKS (Yahoo Finance)")
    
    try:
        extractor = YahooFinanceExtractor()
        tickers = ['AAPL', 'MSFT']
        
        logger.info(f"Extracting stock data for: {tickers}")
        
        data = extractor.extract_stock_prices(
            tickers=tickers,
            period='5d'
        )
        
        if not data.empty:
            logger.info(f"✅ SUCCESS - Extracted {len(data)} stock price records")
            logger.info(f"   Tickers: {data['ticker'].unique().tolist()}")
            logger.info(f"   Date range: {data['date'].min()} to {data['date'].max()}")
        else:
            logger.warning("⚠️  No stock data extracted")
            
    except Exception as e:
        logger.error(f"❌ FAILED - {str(e)}")


def test_crypto():
    """Test cryptocurrency data extraction."""
    print_section_header("TESTING CRYPTO (CoinGecko)")
    
    try:
        extractor = CoinGeckoExtractor(rate_limit_delay=2.0)  # Conservative delay
        symbols = ['BTC', 'ETH']
        
        logger.info(f"Extracting crypto data for: {symbols}")
        logger.info("Note: Using 2s rate limit delay to avoid 429 errors")
        
        data = extractor.extract_crypto_prices(
            symbols=symbols,
            days=7
        )
        
        if not data.empty:
            logger.info(f"✅ SUCCESS - Extracted {len(data)} crypto price records")
            logger.info(f"   Symbols: {data['symbol'].unique().tolist()}")
            logger.info(f"   Date range: {data['date'].min()} to {data['date'].max()}")
        else:
            logger.warning("⚠️  No crypto data extracted")
            
    except Exception as e:
        logger.error(f"❌ FAILED - {str(e)}")


def test_bonds_fred():
    """Test bond data extraction from FRED."""
    print_section_header("TESTING BONDS - FRED")
    
    fred_api_key = os.getenv('FRED_API_KEY')
    if not fred_api_key:
        logger.warning("⚠️  SKIPPED - FRED_API_KEY not set")
        return
    
    try:
        extractor = FREDBondExtractor(api_key=fred_api_key)
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        
        logger.info("Extracting treasury yields for past 30 days")
        
        data = extractor.extract_treasury_yields(
            periods=['DGS3MO', 'DGS2', 'DGS10'],
            start_date=start_date.strftime('%Y-%m-%d'),
            end_date=end_date.strftime('%Y-%m-%d')
        )
        
        if not data.empty:
            logger.info(f"✅ SUCCESS - Extracted {len(data)} treasury yield records")
            logger.info(f"   Periods: {data['period'].unique().tolist()}")
            logger.info(f"   Date range: {data['date'].min()} to {data['date'].max()}")
        else:
            logger.warning("⚠️  No FRED bond data extracted")
            
    except Exception as e:
        logger.error(f"❌ FAILED - {str(e)}")


def test_bonds_yahoo():
    """Test bond data extraction from Yahoo Finance."""
    print_section_header("TESTING BONDS - Yahoo Finance")
    
    try:
        extractor = YahooBondExtractor()
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        
        logger.info("Extracting treasury yields for past 30 days")
        
        data = extractor.extract_treasury_yields(
            periods=['3MO', '10Y', '30Y'],
            start_date=start_date.strftime('%Y-%m-%d'),
            end_date=end_date.strftime('%Y-%m-%d')
        )
        
        if not data.empty:
            logger.info(f"✅ SUCCESS - Extracted {len(data)} treasury yield records")
            logger.info(f"   Periods: {data['period'].unique().tolist()}")
            logger.info(f"   Date range: {data['date'].min()} to {data['date'].max()}")
        else:
            logger.warning("⚠️  No Yahoo bond data extracted")
            
    except Exception as e:
        logger.error(f"❌ FAILED - {str(e)}")


def test_economic_indicators():
    """Test economic indicators extraction."""
    print_section_header("TESTING ECONOMIC INDICATORS (FRED)")
    
    fred_api_key = os.getenv('FRED_API_KEY')
    if not fred_api_key:
        logger.warning("⚠️  SKIPPED - FRED_API_KEY not set")
        return
    
    try:
        extractor = EconomicIndicatorsExtractor(api_key=fred_api_key)
        
        logger.info("Fetching latest values for key indicators")
        
        indicators = ['GDP', 'UNRATE', 'CPIAUCSL', 'FEDFUNDS']
        data = extractor.get_latest_values(indicators)
        
        if not data.empty:
            logger.info(f"✅ SUCCESS - Retrieved {len(data)} economic indicators")
            logger.info("\nLatest Values:")
            for _, row in data.iterrows():
                logger.info(f"   {row['indicator_name']}: {row['value']:.2f} {row['unit']}")
                logger.info(f"      Date: {row['date'].strftime('%Y-%m-%d')}")
        else:
            logger.warning("⚠️  No economic indicator data extracted")
            
    except Exception as e:
        logger.error(f"❌ FAILED - {str(e)}")


def print_summary(results):
    """Print test summary."""
    print_section_header("TEST SUMMARY")
    
    total = len(results)
    passed = sum(1 for r in results.values() if r == 'PASS')
    failed = sum(1 for r in results.values() if r == 'FAIL')
    skipped = sum(1 for r in results.values() if r == 'SKIP')
    
    logger.info(f"\nTotal Tests: {total}")
    logger.info(f"✅ Passed: {passed}")
    logger.info(f"❌ Failed: {failed}")
    logger.info(f"⚠️  Skipped: {skipped}")
    
    logger.info("\nDetailed Results:")
    for test_name, result in results.items():
        icon = "✅" if result == "PASS" else "❌" if result == "FAIL" else "⚠️ "
        logger.info(f"   {icon} {test_name}: {result}")
    
    if failed == 0:
        logger.info("\n🎉 All tests passed!")
    else:
        logger.warning(f"\n⚠️  {failed} test(s) failed. Check logs above for details.")


def run_all_tests():
    """Run all data source tests."""
    logger.info("=" * 80)
    logger.info("UNIFIED DATA SOURCE TEST")
    logger.info("Testing all extractors: Stocks, Crypto, Bonds, Economic Indicators")
    logger.info("=" * 80)
    
    results = {}
    
    # Test each data source
    tests = [
        ("Stocks (Yahoo Finance)", test_stocks),
        ("Crypto (CoinGecko)", test_crypto),
        ("Bonds - FRED", test_bonds_fred),
        ("Bonds - Yahoo Finance", test_bonds_yahoo),
        ("Economic Indicators", test_economic_indicators)
    ]
    
    for test_name, test_func in tests:
        try:
            test_func()
            results[test_name] = "PASS"
        except Exception as e:
            logger.error(f"Test '{test_name}' encountered an error: {str(e)}")
            results[test_name] = "FAIL"
    
    # Print summary
    print_summary(results)
    
    logger.info("\n" + "=" * 80)
    logger.info("TEST COMPLETE")
    logger.info("=" * 80)


if __name__ == "__main__":
    # Check for API keys
    fred_key = os.getenv('FRED_API_KEY')
    if not fred_key:
        logger.warning("\n⚠️  WARNING: FRED_API_KEY not set in environment")
        logger.warning("Some tests will be skipped. Set it with:")
        logger.warning("export FRED_API_KEY='your_key_here'\n")
    
    run_all_tests()
