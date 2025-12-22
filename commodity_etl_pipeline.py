"""
Commodity ETL Pipeline

Extracts commodity data from Yahoo Finance and/or FRED,
transforms it into star schema format, and loads into the database.
"""

import argparse
from datetime import datetime
from dotenv import load_dotenv
from loguru import logger

from src.extractors.yahoo_commodity import YahooCommodityExtractor
from src.extractors.fred_commodity import FREDCommodityExtractor
from src.transformers.data_transformer import DataTransformer
from src.loaders.data_loader import DataLoader
from src.models import SessionLocal, init_db

# Load environment variables
load_dotenv()


def run_commodity_pipeline(
    symbols: list = None,
    source: str = 'yahoo',
    days: int = 30,
    start_date: str = None,
    end_date: str = None
):
    """
    Run the complete commodity ETL pipeline.
    
    Args:
        symbols: List of commodity symbols/series IDs
        source: Data source ('yahoo' or 'fred' or 'both')
        days: Number of days to look back (if dates not specified)
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
    """
    logger.info("=" * 60)
    logger.info("COMMODITY ETL PIPELINE")
    logger.info("=" * 60)
    logger.info(f"Source: {source}")
    logger.info(f"Symbols: {symbols if symbols else 'All available'}")
    logger.info(f"Period: {days} days" if not start_date else f"Period: {start_date} to {end_date}")
    
    # Initialize database
    init_db()
    db = SessionLocal()
    
    try:
        loader = DataLoader(db)
        transformer = DataTransformer()
        
        # Track totals across sources
        total_commodities = 0
        total_prices = 0
        
        # ===== YAHOO FINANCE =====
        if source in ['yahoo', 'both']:
            logger.info("\n" + "=" * 60)
            logger.info("YAHOO FINANCE EXTRACTION")
            logger.info("=" * 60)
            
            yahoo_extractor = YahooCommodityExtractor()
            
            # Extract commodity info
            commodity_info_df = yahoo_extractor.extract_commodity_info(symbols)
            logger.info(f"Extracted metadata for {len(commodity_info_df)} commodities")
            
            # Extract prices
            price_df = yahoo_extractor.extract_commodity_prices(
                symbols=symbols,
                start_date=start_date,
                end_date=end_date,
                days=days
            )
            
            if not price_df.empty:
                # TRANSFORM
                logger.info("\n--- Transformation (Yahoo) ---")
                
                # Transform commodity dimension
                commodity_dim_df = transformer.transform_commodity_dimension(commodity_info_df)
                
                # Transform date dimension
                date_dim_df = transformer.transform_date_dimension(price_df['date'])
                
                # LOAD
                logger.info("\n--- Loading (Yahoo) ---")
                
                # Load data source
                yahoo_source_id = loader.load_or_get_data_source('yahoo_finance', 'API')
                
                # Load dates
                date_mapping = loader.load_dates(date_dim_df)
                
                # Load commodities
                commodity_mapping = loader.load_commodities(commodity_dim_df)
                
                # Transform price facts
                price_fact_df = transformer.transform_commodity_price(
                    price_df,
                    commodity_mapping,
                    date_mapping,
                    yahoo_source_id
                )
                
                # Load prices
                yahoo_records = loader.load_commodity_prices(price_fact_df)
                
                total_commodities += len(commodity_mapping)
                total_prices += yahoo_records
                
                logger.info(f"✅ Yahoo Finance: Loaded {yahoo_records} price records for {len(commodity_mapping)} commodities")
            else:
                logger.warning("No price data from Yahoo Finance")
        
        # ===== FRED =====
        if source in ['fred', 'both']:
            logger.info("\n" + "=" * 60)
            logger.info("FRED EXTRACTION")
            logger.info("=" * 60)
            
            try:
                fred_extractor = FREDCommodityExtractor()
                
                # If symbols not specified and source is 'fred', use common FRED series
                fred_symbols = symbols if symbols else ['DCOILWTICO', 'DCOILBRENTEU', 'GOLDAMGBD228NLBM', 'DHHNGSP']
                
                # Extract commodity info
                commodity_info_df = fred_extractor.extract_commodity_info(fred_symbols)
                logger.info(f"Extracted metadata for {len(commodity_info_df)} commodities")
                
                # Extract prices
                price_df = fred_extractor.extract_commodity_prices(
                    series_ids=fred_symbols,
                    start_date=start_date,
                    end_date=end_date,
                    days=days
                )
                
                if not price_df.empty:
                    # TRANSFORM
                    logger.info("\n--- Transformation (FRED) ---")
                    
                    # Transform commodity dimension
                    commodity_dim_df = transformer.transform_commodity_dimension(commodity_info_df)
                    
                    # Transform date dimension
                    date_dim_df = transformer.transform_date_dimension(price_df['date'])
                    
                    # LOAD
                    logger.info("\n--- Loading (FRED) ---")
                    
                    # Load data source
                    fred_source_id = loader.load_or_get_data_source('fred', 'API')
                    
                    # Load dates
                    date_mapping = loader.load_dates(date_dim_df)
                    
                    # Load commodities
                    commodity_mapping = loader.load_commodities(commodity_dim_df)
                    
                    # Transform price facts
                    price_fact_df = transformer.transform_commodity_price(
                        price_df,
                        commodity_mapping,
                        date_mapping,
                        fred_source_id
                    )
                    
                    # Load prices
                    fred_records = loader.load_commodity_prices(price_fact_df)
                    
                    total_commodities += len(commodity_mapping)
                    total_prices += fred_records
                    
                    logger.info(f"✅ FRED: Loaded {fred_records} price records for {len(commodity_mapping)} series")
                else:
                    logger.warning("No price data from FRED")
            
            except Exception as e:
                logger.error(f"Error with FRED extraction: {str(e)}")
                if source == 'fred':
                    raise
        
        # ===== SUMMARY =====
        logger.info("\n" + "=" * 60)
        logger.info("PIPELINE SUMMARY")
        logger.info("=" * 60)
        logger.info(f"✅ Total commodities: {total_commodities}")
        logger.info(f"✅ Total price records loaded: {total_prices}")
        logger.info(f"✅ Date range: {start_date or f'Last {days} days'} to {end_date or 'today'}")
        logger.info("=" * 60)
        
        return total_prices
        
    except Exception as e:
        logger.error(f"Pipeline failed: {str(e)}")
        db.rollback()
        raise
    finally:
        db.close()


def main():
    """Parse command-line arguments and run the pipeline."""
    parser = argparse.ArgumentParser(description="Commodity ETL Pipeline")
    
    parser.add_argument(
        '--symbols',
        nargs='+',
        help='Commodity symbols (Yahoo: CL=F, GC=F, etc. | FRED: DCOILWTICO, etc.)'
    )
    
    parser.add_argument(
        '--source',
        choices=['yahoo', 'fred', 'both'],
        default='yahoo',
        help='Data source (default: yahoo)'
    )
    
    parser.add_argument(
        '--days',
        type=int,
        default=30,
        help='Number of days to look back (default: 30)'
    )
    
    parser.add_argument(
        '--start-date',
        help='Start date (YYYY-MM-DD format)'
    )
    
    parser.add_argument(
        '--end-date',
        help='End date (YYYY-MM-DD format)'
    )
    
    args = parser.parse_args()
    
    # Run the pipeline
    run_commodity_pipeline(
        symbols=args.symbols,
        source=args.source,
        days=args.days,
        start_date=args.start_date,
        end_date=args.end_date
    )


if __name__ == "__main__":
    main()
