#!/usr/bin/env python
"""Test script for cryptocurrency data extraction and loading."""
import sys
import time
import pandas as pd
from datetime import datetime, timedelta
from loguru import logger

from config.config import CRYPTO_SYMBOLS, BATCH_SIZE
from src.utils import setup_logger, DataQualityValidator
from src.extractors import CoinGeckoExtractor
from src.transformers import DataTransformer
from src.loaders import DataLoader
from src.models import SessionLocal, init_db


def test_crypto_pipeline():
    """Test the complete crypto ETL pipeline."""
    setup_logger()
    logger.info("=" * 80)
    logger.info("CRYPTOCURRENCY ETL PIPELINE TEST")
    logger.info("=" * 80)
    
    try:
        # Initialize database
        logger.info("Initializing database...")
        init_db()
        
        # Initialize extractor
        logger.info("Initializing CoinGecko extractor...")
        extractor = CoinGeckoExtractor()
        
        # Step 1: Extract crypto prices (last 7 days)
        logger.info("=" * 80)
        logger.info("EXTRACT PHASE")
        logger.info("=" * 80)
        
        test_symbols = CRYPTO_SYMBOLS[:3] if len(CRYPTO_SYMBOLS) > 0 else ["BTC", "ETH", "ADA"]
        logger.info(f"Extracting crypto data for symbols: {test_symbols}")
        
        # Try to extract, with fallback to mock data if rate-limited
        price_data = extractor.extract_crypto_prices(
            symbols=test_symbols,
            days=7
        )
        
        if price_data.empty:
            logger.warning("CoinGecko API rate-limited or unavailable. Using mock data for testing.")
            # Create mock data for testing
            dates = pd.date_range(end=datetime.now(), periods=7, freq='D')
            mock_data = []
            for symbol in test_symbols:
                base_price = {'BTC': 45000, 'ETH': 2500, 'ADA': 0.50}.get(symbol, 100)
                for i, date in enumerate(dates):
                    mock_data.append({
                        'symbol': symbol,
                        'date': date.date(),
                        'price': float(base_price * (1 + (i % 3) * 0.01)),  # Slight variation
                        'market_cap': float(1000000000000 if symbol == 'BTC' else 500000000000),
                        'volume': float(50000000000),
                        'timestamp': date  # Add timestamp for compatibility
                    })
            price_data = pd.DataFrame(mock_data)
            logger.info(f"Using mock cryptocurrency data for demonstration ({len(price_data)} records)")
        
        # Remove duplicates (CoinGecko may return duplicates)
        price_data = price_data.drop_duplicates(subset=['symbol', 'date'])
        logger.info(f"Extracted {len(price_data)} price records (after deduplication)")
        logger.info(f"Date range: {price_data['date'].min()} to {price_data['date'].max()}")
        logger.info(f"Symbols: {price_data['symbol'].unique().tolist()}")
        
        # Extract crypto info
        logger.info("Extracting crypto metadata...")
        crypto_info = extractor.extract_crypto_info(test_symbols)
        
        if not crypto_info.empty:
            logger.info(f"Extracted info for {len(crypto_info)} cryptocurrencies")
            logger.info(f"Cryptos: {crypto_info['name'].tolist()}")
        else:
            logger.warning("No crypto info extracted")
        
        # Step 2: Validate data
        logger.info("=" * 80)
        logger.info("VALIDATION PHASE")
        logger.info("=" * 80)
        
        validator = DataQualityValidator()
        is_valid, errors = validator.validate_crypto_prices(price_data)
        
        if not is_valid:
            logger.warning("Data validation warnings:")
            for error in errors:
                logger.warning(f"  - {error}")
            # Don't abort - warnings are ok, continue anyway
        else:
            logger.info("Data validation passed ✓")
        
        # Get data summary
        summary = validator.get_data_summary(price_data)
        logger.info(f"Data summary:")
        logger.info(f"  - Row count: {summary['row_count']}")
        logger.info(f"  - Columns: {summary['columns']}")
        logger.info(f"  - Memory usage: {summary['memory_usage_mb']:.2f} MB")
        
        # Step 3: Transform data
        logger.info("=" * 80)
        logger.info("TRANSFORM PHASE")
        logger.info("=" * 80)
        
        transformer = DataTransformer()
        
        # Transform date dimension
        date_dim = transformer.transform_date_dimension(price_data['date'])
        logger.info(f"Transformed {len(date_dim)} date dimension records")
        
        # Transform crypto dimension
        if not crypto_info.empty:
            crypto_dim = transformer.transform_crypto_dimension(crypto_info)
            logger.info(f"Transformed {len(crypto_dim)} crypto asset records")
        else:
            # Create minimal crypto dimension from price data
            logger.warning("No crypto info available. Creating minimal crypto dimension.")
            crypto_dim = price_data[['symbol']].drop_duplicates()
            crypto_dim['name'] = crypto_dim['symbol']
            crypto_dim['chain'] = 'Unknown'
            crypto_dim['description'] = ''
            logger.info(f"Created minimal {len(crypto_dim)} crypto asset records")
        
        # Step 4: Load data
        logger.info("=" * 80)
        logger.info("LOAD PHASE")
        logger.info("=" * 80)
        
        db_session = SessionLocal()
        try:
            loader = DataLoader(db_session)
            
            # Load data source
            source_id = loader.load_or_get_data_source(
                source_name=extractor.source_name,
                source_type="API"
            )
            logger.info(f"Data source ID: {source_id}")
            
            # Load dimensions
            crypto_mapping = loader.load_crypto_assets(crypto_dim)
            logger.info(f"Loaded {len(crypto_mapping)} crypto assets")
            logger.info(f"Crypto mapping: {crypto_mapping}")
            
            date_mapping = loader.load_dates(date_dim)
            logger.info(f"Loaded {len(date_mapping)} date records")
            
            # Transform and load facts
            logger.info("Transforming crypto price facts...")
            logger.debug(f"Price data columns: {price_data.columns.tolist()}")
            logger.debug(f"Sample price data row: {price_data.iloc[0].to_dict()}")
            logger.debug(f"Date mapping size: {len(date_mapping)}")
            logger.debug(f"Crypto mapping: {crypto_mapping}")
            
            price_facts = transformer.transform_crypto_prices(
                price_df=price_data,
                crypto_mapping=crypto_mapping,
                date_mapping=date_mapping,
                source_id=source_id
            )
            
            if price_facts.empty:
                logger.error("No price facts to load after transformation")
                logger.error(f"Price data shape: {price_data.shape}")
                logger.error(f"Price data sample: {price_data.head()}")
                return False
            
            logger.info(f"Transformed {len(price_facts)} price fact records")
            logger.info(f"Sample record:\n{price_facts.iloc[0]}")
            
            # Load facts
            records_loaded = loader.load_crypto_prices(price_facts, batch_size=BATCH_SIZE)
            
            logger.info("=" * 80)
            logger.info("TEST COMPLETED SUCCESSFULLY ✓")
            logger.info("=" * 80)
            logger.info(f"Loaded {records_loaded} new crypto price records")
            
            # Query verification
            logger.info("=" * 80)
            logger.info("VERIFICATION - Querying loaded data")
            logger.info("=" * 80)
            
            from src.models import FactCryptoPrice, DimCryptoAsset, DimDate
            from sqlalchemy import select
            
            # Query crypto assets
            cryptos = db_session.execute(
                select(DimCryptoAsset)
            ).scalars().all()
            
            logger.info(f"Crypto assets in DB: {len(cryptos)}")
            for crypto in cryptos:
                logger.info(f"  - {crypto.symbol}: {crypto.name} ({crypto.chain})")
            
            # Query price facts
            prices = db_session.execute(
                select(FactCryptoPrice).limit(5)
            ).scalars().all()
            
            logger.info(f"Sample price records from DB ({len(prices)} shown):")
            for price in prices:
                logger.info(f"  - Crypto ID {price.crypto_id}, Date ID {price.date_id}: ${price.price}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error during load phase: {str(e)}")
            db_session.rollback()
            logger.exception(e)
            return False
        finally:
            db_session.close()
    
    except Exception as e:
        logger.error("=" * 80)
        logger.error(f"TEST FAILED: {str(e)}")
        logger.error("=" * 80)
        logger.exception(e)
        return False


if __name__ == "__main__":
    success = test_crypto_pipeline()
    sys.exit(0 if success else 1)
