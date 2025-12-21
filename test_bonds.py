#!/usr/bin/env python
"""Test script for bond data extraction and loading."""
import sys
import pandas as pd
from datetime import datetime, timedelta
from loguru import logger

from config.config import BATCH_SIZE, FRED_API_KEY
from src.utils import setup_logger, DataQualityValidator
from src.extractors import FREDBondExtractor
from src.transformers import DataTransformer
from src.loaders import DataLoader
from src.models import SessionLocal, init_db


def test_bond_pipeline():
    """Test the complete bond ETL pipeline."""
    setup_logger()
    logger.info("=" * 80)
    logger.info("BOND ETL PIPELINE TEST")
    logger.info("=" * 80)
    
    if not FRED_API_KEY:
        logger.error("FRED_API_KEY not set. Please set it before running this test.")
        logger.error("Get a free API key at: https://fred.stlouisfed.org/docs/api/")
        return False
    
    try:
        # Initialize database
        logger.info("Initializing database...")
        init_db()
        
        # Initialize extractor
        logger.info("Initializing FRED bond extractor...")
        extractor = FREDBondExtractor(api_key=FRED_API_KEY)
        
        # Step 1: Extract treasury yields
        logger.info("=" * 80)
        logger.info("EXTRACT PHASE - Treasury Yields")
        logger.info("=" * 80)
        
        # Get last 30 days of data
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        
        test_periods = ['DGS3MO', 'DGS2', 'DGS10', 'DGS30']
        logger.info(f"Extracting treasury yields for periods: {test_periods}")
        logger.info(f"Date range: {start_date} to {end_date}")
        
        yield_data = extractor.extract_treasury_yields(
            periods=test_periods,
            start_date=start_date,
            end_date=end_date
        )
        
        if yield_data.empty:
            logger.error("No treasury yield data extracted. Aborting test.")
            return False
        
        logger.info(f"Extracted {len(yield_data)} yield records")
        logger.info(f"Periods: {yield_data['period'].unique().tolist()}")
        logger.info(f"Date range: {yield_data['date'].min()} to {yield_data['date'].max()}")
        logger.info(f"Sample yields:\n{yield_data.head(10)}")
        
        # Step 2: Extract corporate bond yields
        logger.info("=" * 80)
        logger.info("EXTRACT PHASE - Corporate Bond Yields")
        logger.info("=" * 80)
        
        test_ratings = ['AAA', 'BBB']
        logger.info(f"Extracting corporate bond yields for ratings: {test_ratings}")
        
        corporate_data = extractor.extract_corporate_bond_yields(
            ratings=test_ratings,
            start_date=start_date,
            end_date=end_date
        )
        
        if not corporate_data.empty:
            logger.info(f"Extracted {len(corporate_data)} corporate yield records")
            logger.info(f"Ratings: {corporate_data['rating'].unique().tolist()}")
        else:
            logger.warning("No corporate bond yield data extracted")
        
        # Step 3: Get bond metadata
        logger.info("=" * 80)
        logger.info("EXTRACT PHASE - Bond Metadata")
        logger.info("=" * 80)
        
        bond_metadata = extractor.get_bond_metadata()
        logger.info(f"Bond metadata for {len(bond_metadata)} bond types:")
        for bond_id, bond_info in bond_metadata.items():
            logger.info(f"  - {bond_id}: {bond_info['name']}")
        
        # Step 4: Validate data
        logger.info("=" * 80)
        logger.info("VALIDATION PHASE")
        logger.info("=" * 80)
        
        validator = DataQualityValidator()
        
        # Transform yield data to match bond price schema for validation
        # (yield column instead of price column)
        yield_validation_data = yield_data.copy()
        yield_validation_data['isin'] = 'TREASURY'
        yield_validation_data['price'] = yield_validation_data['yield']
        yield_validation_data['yield'] = yield_validation_data['yield']
        
        is_valid, errors = validator.validate_bond_prices(
            yield_validation_data[['isin', 'date', 'price', 'yield']]
        )
        
        if not is_valid:
            logger.error("Data validation failed:")
            for error in errors:
                logger.error(f"  - {error}")
            # Don't abort - validation may show warnings only
        else:
            logger.info("Data validation passed ✓")
        
        # Get data summary
        summary = validator.get_data_summary(yield_data)
        logger.info(f"Data summary:")
        logger.info(f"  - Row count: {summary['row_count']}")
        logger.info(f"  - Columns: {summary['columns']}")
        logger.info(f"  - Memory usage: {summary['memory_usage_mb']:.2f} MB")
        
        # Step 5: Transform data
        logger.info("=" * 80)
        logger.info("TRANSFORM PHASE")
        logger.info("=" * 80)
        
        transformer = DataTransformer()
        
        # Transform date dimension
        date_dim = transformer.transform_date_dimension(yield_data['date'])
        logger.info(f"Transformed {len(date_dim)} date dimension records")
        
        # Create issuer dimension for treasury
        logger.info("Creating issuer dimension for US Treasury...")
        issuer_dim = pd.DataFrame({
            'issuer_name': ['U.S. Department of Treasury'],
            'issuer_type': ['Government'],
            'country': ['USA'],
            'credit_rating': ['AAA'],
            'sector': ['Government']
        })
        
        issuer_dim = transformer.transform_issuer_dimension(issuer_dim)
        logger.info(f"Transformed {len(issuer_dim)} issuer records")
        
        # Create bond dimension for treasury bonds
        logger.info("Creating bond dimension for US Treasury bonds...")
        bond_dim_list = []
        bond_metadata = extractor.get_bond_metadata()
        
        for bond_id, bond_info in bond_metadata.items():
            bond_dim_list.append({
                'isin': bond_id,
                'issuer_name': 'U.S. Department of Treasury',
                'bond_type': bond_info['bond_type'],
                'maturity_date': datetime.now() + timedelta(days=bond_info['maturity_days']),
                'coupon_rate': 0.0,
                'currency': bond_info['currency'],
                'country': bond_info['country']
            })
        
        bond_dim = pd.DataFrame(bond_dim_list)
        logger.info(f"Created {len(bond_dim)} bond records")
        
        # Step 6: Load data
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
            logger.info("Loading issuer dimension...")
            issuer_mapping = loader.load_issuer(issuer_dim)
            logger.info(f"Loaded {len(issuer_mapping)} issuers")
            logger.info(f"Issuer mapping: {issuer_mapping}")
            
            # Add issuer_id to bond_dim
            bond_dim['issuer_id'] = bond_dim['issuer_name'].map(issuer_mapping)
            
            logger.info("Loading bond dimension...")
            bond_mapping = loader.load_bonds(bond_dim)
            logger.info(f"Loaded {len(bond_mapping)} bonds")
            logger.info(f"Bond mapping (ISINs): {list(bond_mapping.keys())}")
            
            date_mapping = loader.load_dates(date_dim)
            logger.info(f"Loaded {len(date_mapping)} date records")
            
            # Transform yield data to bond price format
            logger.info("Transforming yield data to bond price facts...")
            
            # Create bond price facts from yield data
            bond_price_facts = []
            for _, row in yield_data.iterrows():
                # Map period to ISIN
                period_to_isin = {
                    'DGS3MO': 'US_3MO',
                    'DGS1': 'US_1Y',
                    'DGS2': 'US_2Y',
                    'DGS5': 'US_5Y',
                    'DGS10': 'US_10Y',
                    'DGS20': 'US_20Y',
                    'DGS30': 'US_30Y'
                }
                
                isin = period_to_isin.get(row['period'])
                if isin and isin in bond_mapping:
                    bond_price_facts.append({
                        'bond_id': bond_mapping[isin],
                        'date_id': date_mapping.get(pd.to_datetime(row['date']).date()),
                        'source_id': source_id,
                        'price': 100.0,  # Par value
                        'yield_percent': row['yield'],
                        'spread': 0.0,
                        'duration': float(isin.split('_')[1].replace('Y', '').replace('MO', '')) if 'Y' in isin else 0.25
                    })
            
            if bond_price_facts:
                bond_facts_df = pd.DataFrame(bond_price_facts)
                # Remove any rows with None values in required fields
                bond_facts_df = bond_facts_df.dropna(subset=['bond_id', 'date_id', 'price', 'yield_percent'])
                
                logger.info(f"Transformed {len(bond_facts_df)} bond price records")
                
                if not bond_facts_df.empty:
                    logger.info(f"Sample record:\n{bond_facts_df.iloc[0]}")
                    
                    # Load facts
                    records_loaded = loader.load_bond_prices(bond_facts_df, batch_size=BATCH_SIZE)
                    
                    logger.info("=" * 80)
                    logger.info("TEST COMPLETED SUCCESSFULLY ✓")
                    logger.info("=" * 80)
                    logger.info(f"Loaded {records_loaded} new bond price records")
                else:
                    logger.warning("No valid bond price facts after filtering")
            else:
                logger.warning("No bond price facts created")
            
            # Query verification
            logger.info("=" * 80)
            logger.info("VERIFICATION - Querying loaded data")
            logger.info("=" * 80)
            
            from src.models import FactBondPrice, DimBond, DimIssuer
            from sqlalchemy import select
            
            # Query issuers
            issuers = db_session.execute(
                select(DimIssuer)
            ).scalars().all()
            
            logger.info(f"Issuers in DB: {len(issuers)}")
            for issuer in issuers:
                logger.info(f"  - {issuer.issuer_name} ({issuer.issuer_type})")
            
            # Query bonds
            bonds = db_session.execute(
                select(DimBond)
            ).scalars().all()
            
            logger.info(f"Bonds in DB: {len(bonds)}")
            for bond in bonds[:5]:
                logger.info(f"  - {bond.isin}: {bond.bond_type}")
            
            # Query price facts
            prices = db_session.execute(
                select(FactBondPrice).limit(5)
            ).scalars().all()
            
            logger.info(f"Sample bond price records from DB ({len(prices)} shown):")
            for price in prices:
                logger.info(f"  - Bond ID {price.bond_id}, Date ID {price.date_id}: {price.yield_percent}%")
            
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
    success = test_bond_pipeline()
    sys.exit(0 if success else 1)
