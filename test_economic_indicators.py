"""Demo script for economic indicators."""
import os
from datetime import datetime, timedelta
from loguru import logger

from src.extractors.economic_indicators import EconomicIndicatorsExtractor


def test_economic_indicators():
    """Test and demonstrate economic indicators extraction."""
    
    logger.info("=" * 80)
    logger.info("ECONOMIC INDICATORS DEMO")
    logger.info("=" * 80)
    
    # Initialize extractor
    fred_api_key = os.getenv('FRED_API_KEY')
    if not fred_api_key:
        logger.error("FRED_API_KEY not set. Cannot proceed.")
        return
    
    extractor = EconomicIndicatorsExtractor(api_key=fred_api_key)
    
    # =========================================================================
    # 1. Show available indicators
    # =========================================================================
    logger.info("\n" + "=" * 80)
    logger.info("AVAILABLE INDICATORS")
    logger.info("=" * 80)
    
    available = extractor.list_available_indicators()
    logger.info(f"\n{available.to_string()}")
    
    # =========================================================================
    # 2. Get latest values for key indicators
    # =========================================================================
    logger.info("\n" + "=" * 80)
    logger.info("LATEST VALUES - KEY INDICATORS")
    logger.info("=" * 80)
    
    key_indicators = ['GDP', 'UNRATE', 'CPIAUCSL', 'FEDFUNDS']
    latest = extractor.get_latest_values(key_indicators)
    
    if not latest.empty:
        logger.info("\n")
        for _, row in latest.iterrows():
            logger.info(f"{row['indicator_name']}")
            logger.info(f"  Latest: {row['value']:.2f} {row['unit']}")
            logger.info(f"  Date: {row['date'].strftime('%Y-%m-%d')}")
            logger.info(f"  Category: {row['category']}")
            logger.info("")
    
    # =========================================================================
    # 3. Extract inflation data (last 12 months)
    # =========================================================================
    logger.info("=" * 80)
    logger.info("INFLATION INDICATORS - LAST 12 MONTHS")
    logger.info("=" * 80)
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365)
    
    inflation_data = extractor.extract_by_category(
        category='Inflation',
        start_date=start_date.strftime('%Y-%m-%d'),
        end_date=end_date.strftime('%Y-%m-%d')
    )
    
    if not inflation_data.empty:
        logger.info(f"\nExtracted {len(inflation_data)} inflation records")
        logger.info(f"Date range: {inflation_data['date'].min()} to {inflation_data['date'].max()}")
        logger.info(f"\nSample data:")
        logger.info(f"\n{inflation_data.tail(10).to_string()}")
    
    # =========================================================================
    # 4. Extract employment data
    # =========================================================================
    logger.info("\n" + "=" * 80)
    logger.info("EMPLOYMENT INDICATORS - LAST 6 MONTHS")
    logger.info("=" * 80)
    
    start_date = end_date - timedelta(days=180)
    
    employment_data = extractor.extract_by_category(
        category='Employment',
        start_date=start_date.strftime('%Y-%m-%d'),
        end_date=end_date.strftime('%Y-%m-%d')
    )
    
    if not employment_data.empty:
        logger.info(f"\nExtracted {len(employment_data)} employment records")
        logger.info(f"\nLatest unemployment rate:")
        unrate = employment_data[employment_data['indicator'] == 'UNRATE'].tail(1)
        if not unrate.empty:
            logger.info(f"  {unrate.iloc[0]['value']:.1f}% as of {unrate.iloc[0]['date'].strftime('%Y-%m-%d')}")
        
        logger.info(f"\nSample data:")
        logger.info(f"\n{employment_data.tail(5).to_string()}")
    
    # =========================================================================
    # 5. Historical comparison
    # =========================================================================
    logger.info("\n" + "=" * 80)
    logger.info("YEAR-OVER-YEAR COMPARISON")
    logger.info("=" * 80)
    
    # Get data from last 2 years
    start_date = end_date - timedelta(days=730)
    
    comparison_indicators = ['UNRATE', 'CPIAUCSL', 'FEDFUNDS']
    comparison_data = extractor.extract_indicators(
        indicators=comparison_indicators,
        start_date=start_date.strftime('%Y-%m-%d'),
        end_date=end_date.strftime('%Y-%m-%d')
    )
    
    if not comparison_data.empty:
        logger.info("\nComparing latest vs 1 year ago:\n")
        
        for indicator in comparison_indicators:
            ind_data = comparison_data[comparison_data['indicator'] == indicator].sort_values('date')
            
            if len(ind_data) >= 2:
                latest_val = ind_data.iloc[-1]
                year_ago = ind_data[ind_data['date'] <= (end_date - timedelta(days=365))].iloc[-1] if len(ind_data[ind_data['date'] <= (end_date - timedelta(days=365))]) > 0 else None
                
                logger.info(f"{latest_val['indicator_name']}:")
                logger.info(f"  Latest: {latest_val['value']:.2f} ({latest_val['date'].strftime('%Y-%m-%d')})")
                
                if year_ago is not None:
                    change = latest_val['value'] - year_ago['value']
                    change_pct = (change / year_ago['value'] * 100) if year_ago['value'] != 0 else 0
                    logger.info(f"  1 Year Ago: {year_ago['value']:.2f} ({year_ago['date'].strftime('%Y-%m-%d')})")
                    logger.info(f"  Change: {change:+.2f} ({change_pct:+.1f}%)")
                
                logger.info("")
    
    logger.info("=" * 80)
    logger.info("DEMO COMPLETE")
    logger.info("=" * 80)


if __name__ == "__main__":
    test_economic_indicators()
