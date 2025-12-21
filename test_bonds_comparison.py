"""Test script to compare bond data from FRED and Yahoo Finance."""
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
from loguru import logger

# Load environment variables from .env file
load_dotenv()

from src.extractors.fred_bond import FREDBondExtractor
from src.extractors.yahoo_bond import YahooBondExtractor


def test_bond_comparison():
    """Compare treasury yield data from FRED vs Yahoo Finance."""
    
    logger.info("=" * 80)
    logger.info("BOND DATA COMPARISON TEST - FRED vs Yahoo Finance")
    logger.info("=" * 80)
    
    # Date range
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    
    start_str = start_date.strftime('%Y-%m-%d')
    end_str = end_date.strftime('%Y-%m-%d')
    
    logger.info(f"Date range: {start_str} to {end_str}")
    
    # Common periods to compare
    periods = ['3MO', '5Y', '10Y', '30Y']
    
    # =========================================================================
    # FRED EXTRACTION
    # =========================================================================
    logger.info("\n" + "=" * 80)
    logger.info("EXTRACTING FROM FRED")
    logger.info("=" * 80)
    
    fred_api_key = os.getenv('FRED_API_KEY')
    if not fred_api_key:
        logger.error("FRED_API_KEY not set. Skipping FRED extraction.")
        fred_data = None
    else:
        fred_extractor = FREDBondExtractor(api_key=fred_api_key)
        
        # Map periods to FRED series IDs
        fred_periods = [f'DGS{p}' if p != '3MO' else 'DGS3MO' for p in periods]
        
        fred_data = fred_extractor.extract_treasury_yields(
            periods=fred_periods,
            start_date=start_str,
            end_date=end_str
        )
        
        if not fred_data.empty:
            logger.info(f"\nFRED Data Summary:")
            logger.info(f"  Total records: {len(fred_data)}")
            logger.info(f"  Date range: {fred_data['date'].min()} to {fred_data['date'].max()}")
            logger.info(f"  Periods: {fred_data['period'].unique().tolist()}")
            logger.info(f"\nSample FRED data:")
            logger.info(f"\n{fred_data.head(10)}")
    
    # =========================================================================
    # YAHOO FINANCE EXTRACTION
    # =========================================================================
    logger.info("\n" + "=" * 80)
    logger.info("EXTRACTING FROM YAHOO FINANCE")
    logger.info("=" * 80)
    
    yahoo_extractor = YahooBondExtractor()
    yahoo_data = yahoo_extractor.extract_treasury_yields(
        periods=periods,
        start_date=start_str,
        end_date=end_str
    )
    
    if not yahoo_data.empty:
        logger.info(f"\nYahoo Finance Data Summary:")
        logger.info(f"  Total records: {len(yahoo_data)}")
        logger.info(f"  Date range: {yahoo_data['date'].min()} to {yahoo_data['date'].max()}")
        logger.info(f"  Periods: {yahoo_data['period'].unique().tolist()}")
        logger.info(f"\nSample Yahoo data:")
        logger.info(f"\n{yahoo_data.head(10)}")
    
    # =========================================================================
    # COMPARISON
    # =========================================================================
    if fred_data is not None and not fred_data.empty and not yahoo_data.empty:
        logger.info("\n" + "=" * 80)
        logger.info("COMPARISON ANALYSIS")
        logger.info("=" * 80)
        
        # Compare latest values for each period
        latest_date = min(fred_data['date'].max(), yahoo_data['date'].max())
        
        logger.info(f"\nComparing latest values as of {latest_date.date()}:")
        logger.info(f"\n{'Period':<10} {'FRED':<10} {'Yahoo':<10} {'Difference':<15}")
        logger.info("-" * 50)
        
        for period in periods:
            # Get FRED value
            fred_period = f'DGS{period}' if period != '3MO' else 'DGS3MO'
            fred_value = fred_data[
                (fred_data['period'] == fred_period) & 
                (fred_data['date'] == fred_data['date'].max())
            ]['yield'].values
            
            # Get Yahoo value
            yahoo_value = yahoo_data[
                (yahoo_data['period'] == period) & 
                (yahoo_data['date'] == yahoo_data['date'].max())
            ]['yield'].values
            
            if len(fred_value) > 0 and len(yahoo_value) > 0:
                fred_val = fred_value[0]
                yahoo_val = yahoo_value[0]
                diff = yahoo_val - fred_val
                diff_pct = (diff / fred_val * 100) if fred_val != 0 else 0
                
                logger.info(
                    f"{period:<10} {fred_val:<10.3f} {yahoo_val:<10.3f} "
                    f"{diff:>+7.3f} ({diff_pct:>+6.2f}%)"
                )
    
    logger.info("\n" + "=" * 80)
    logger.info("TEST COMPLETE")
    logger.info("=" * 80)


if __name__ == "__main__":
    test_bond_comparison()
