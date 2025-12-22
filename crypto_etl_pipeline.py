"""Cryptocurrency ETL Pipeline - Extract, Transform, Load crypto data."""
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
from loguru import logger

from src.extractors.crypto_gecko import CoinGeckoExtractor
from src.transformers.data_transformer import DataTransformer
from src.loaders.data_loader import DataLoader
from src.models.base import SessionLocal, init_db

# Load environment variables
load_dotenv()


def run_crypto_pipeline(
    symbols: list = None,
    days: int = 30,
    source_name: str = "coingecko"
):
    """
    Run the complete crypto ETL pipeline.
    
    Args:
        symbols: List of crypto symbols (default: BTC, ETH, ADA)
        days: Number of days of historical data
        source_name: Name of the data source
    """
    if symbols is None:
        symbols = ['BTC', 'ETH', 'ADA']
    
    logger.info("=" * 80)
    logger.info("CRYPTOCURRENCY ETL PIPELINE")
    logger.info("=" * 80)
    logger.info(f"Symbols: {symbols}")
    logger.info(f"Days: {days}")
    logger.info(f"Source: {source_name}")
    
    # Initialize database
    logger.info("\nInitializing database...")
    init_db()
    
    db = SessionLocal()
    
    try:
        # ==================================================================
        # EXTRACT PHASE
        # ==================================================================
        logger.info("\n" + "=" * 80)
        logger.info("EXTRACT PHASE")
        logger.info("=" * 80)
        
        extractor = CoinGeckoExtractor(rate_limit_delay=2.0)
        
        # Extract price data
        logger.info(f"Extracting crypto prices for {len(symbols)} symbols...")
        price_data = extractor.extract_crypto_prices(
            symbols=symbols,
            days=days
        )
        
        if price_data.empty:
            logger.error("No price data extracted. Aborting pipeline.")
            return
        
        logger.info(f"Extracted {len(price_data)} price records")
        logger.info(f"Date range: {price_data['date'].min()} to {price_data['date'].max()}")
        
        # Extract crypto info
        logger.info(f"\nExtracting crypto metadata...")
        info_data = extractor.extract_crypto_info(symbols=symbols)
        
        if info_data.empty:
            logger.warning("No crypto info extracted. Creating minimal crypto dimension.")
            # Create minimal info from price data
            info_data = price_data[['symbol']].drop_duplicates()
            info_data['name'] = info_data['symbol']
            info_data['chain'] = 'Unknown'
            info_data['description'] = ''
        else:
            logger.info(f"Extracted info for {len(info_data)} cryptocurrencies")
        
        # ==================================================================
        # TRANSFORM PHASE
        # ==================================================================
        logger.info("\n" + "=" * 80)
        logger.info("TRANSFORM PHASE")
        logger.info("=" * 80)
        
        transformer = DataTransformer()
        
        # Transform date dimension
        logger.info("Transforming date dimension...")
        date_dim = transformer.transform_date_dimension(price_data['date'])
        logger.info(f"Transformed {len(date_dim)} date records")
        
        # Transform crypto dimension
        logger.info("Transforming crypto asset dimension...")
        crypto_dim = transformer.transform_crypto_dimension(info_data)
        logger.info(f"Transformed {len(crypto_dim)} crypto asset records")
        
        # ==================================================================
        # LOAD PHASE
        # ==================================================================
        logger.info("\n" + "=" * 80)
        logger.info("LOAD PHASE")
        logger.info("=" * 80)
        
        loader = DataLoader(db)
        
        # Load data source
        logger.info(f"Loading data source: {source_name}")
        source_id = loader.load_or_get_data_source(source_name, "API")
        logger.info(f"Data source ID: {source_id}")
        
        # Load dimensions
        logger.info("\nLoading date dimension...")
        date_mapping = loader.load_dates(date_dim)
        logger.info(f"Loaded {len(date_mapping)} dates")
        
        logger.info("\nLoading crypto asset dimension...")
        crypto_mapping = loader.load_crypto_assets(crypto_dim)
        logger.info(f"Loaded {len(crypto_mapping)} crypto assets")
        logger.info(f"Crypto mapping: {crypto_mapping}")
        
        # Transform fact table
        logger.info("\nTransforming crypto price facts...")
        price_facts = transformer.transform_crypto_prices(
            price_df=price_data,
            crypto_mapping=crypto_mapping,
            date_mapping=date_mapping,
            source_id=source_id
        )
        logger.info(f"Transformed {len(price_facts)} price fact records")
        
        # Load fact table
        logger.info("\nLoading crypto price facts...")
        records_loaded = loader.load_crypto_prices(price_facts)
        logger.info(f"Loaded {records_loaded} new price records")
        
        # ==================================================================
        # VERIFICATION
        # ==================================================================
        logger.info("\n" + "=" * 80)
        logger.info("VERIFICATION")
        logger.info("=" * 80)
        
        from sqlalchemy import select, func
        from src.models import FactCryptoPrice, DimCryptoAsset
        
        # Count records
        total_count = db.execute(
            select(func.count()).select_from(FactCryptoPrice)
        ).scalar()
        logger.info(f"Total crypto price records in database: {total_count}")
        
        # Show sample records
        logger.info("\nSample crypto price records:")
        sample = db.execute(
            select(
                DimCryptoAsset.symbol,
                FactCryptoPrice.date_id,
                FactCryptoPrice.price,
                FactCryptoPrice.market_cap
            ).join(
                DimCryptoAsset,
                FactCryptoPrice.crypto_id == DimCryptoAsset.crypto_id
            ).limit(5)
        ).all()
        
        for record in sample:
            logger.info(f"  {record.symbol}: Price=${record.price:,.2f}, Market Cap=${record.market_cap:,.0f} (Date ID: {record.date_id})")
        
        logger.info("\n" + "=" * 80)
        logger.info("PIPELINE COMPLETED SUCCESSFULLY")
        logger.info("=" * 80)
        
    except Exception as e:
        logger.error(f"Pipeline failed: {str(e)}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Run crypto ETL pipeline")
    parser.add_argument(
        "--symbols",
        nargs="+",
        default=["BTC", "ETH", "ADA"],
        help="Crypto symbols to extract"
    )
    parser.add_argument(
        "--days",
        type=int,
        default=30,
        help="Number of days of historical data"
    )
    
    args = parser.parse_args()
    
    run_crypto_pipeline(
        symbols=args.symbols,
        days=args.days
    )
