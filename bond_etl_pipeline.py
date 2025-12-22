"""Bond ETL Pipeline - Extract, Transform, Load bond/treasury yield data."""
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
from loguru import logger
import pandas as pd

from src.extractors.fred_bond import FREDBondExtractor
from src.extractors.yahoo_bond import YahooBondExtractor
from src.transformers.data_transformer import DataTransformer
from src.loaders.data_loader import DataLoader
from src.models.base import SessionLocal, init_db

# Load environment variables
load_dotenv()


def run_bond_pipeline(
    periods: list = None,
    days: int = 30,
    source: str = "yahoo",  # yahoo or fred
    source_name: str = None
):
    """
    Run the complete bond ETL pipeline.
    
    Args:
        periods: List of bond periods (e.g., ['3MO', '10Y', '30Y'])
        days: Number of days of historical data
        source: Data source to use ('yahoo' or 'fred')
        source_name: Override source name in database
    """
    if periods is None:
        periods = ['3MO', '10Y', '30Y']
    
    if source_name is None:
        source_name = f"{source}_bonds"
    
    logger.info("=" * 80)
    logger.info("BOND ETL PIPELINE")
    logger.info("=" * 80)
    logger.info(f"Periods: {periods}")
    logger.info(f"Days: {days}")
    logger.info(f"Source: {source}")
    
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
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        if source == "fred":
            fred_api_key = os.getenv('FRED_API_KEY')
            if not fred_api_key:
                logger.error("FRED_API_KEY not set. Cannot use FRED source.")
                return
            
            extractor = FREDBondExtractor(api_key=fred_api_key)
            # Map periods to FRED series IDs
            fred_periods = [f'DGS{p}' if p not in ['3MO'] else f'DGS{p}' for p in periods]
            
            logger.info(f"Extracting treasury yields from FRED...")
            yield_data = extractor.extract_treasury_yields(
                periods=fred_periods,
                start_date=start_date.strftime('%Y-%m-%d'),
                end_date=end_date.strftime('%Y-%m-%d')
            )
        else:  # yahoo
            extractor = YahooBondExtractor()
            
            logger.info(f"Extracting treasury yields from Yahoo Finance...")
            yield_data = extractor.extract_treasury_yields(
                periods=periods,
                start_date=start_date.strftime('%Y-%m-%d'),
                end_date=end_date.strftime('%Y-%m-%d')
            )
        
        if yield_data.empty:
            logger.error("No yield data extracted. Aborting pipeline.")
            return
        
        logger.info(f"Extracted {len(yield_data)} yield records")
        logger.info(f"Date range: {yield_data['date'].min()} to {yield_data['date'].max()}")
        logger.info(f"Periods: {yield_data['period'].unique().tolist()}")
        
        # ==================================================================
        # PREPARE BOND METADATA
        # ==================================================================
        logger.info("\nPreparing bond metadata...")
        
        # Create issuer data
        issuer_data = pd.DataFrame([{
            'issuer_name': 'U.S. Department of Treasury',
            'issuer_type': 'Government',
            'country': 'USA',
            'credit_rating': 'AAA',
            'sector': 'Government'
        }])
        
        # Create bond metadata from yields
        bond_metadata = []
        for period in yield_data['period'].unique():
            # Extract maturity info
            if 'MO' in str(period):
                months = int(str(period).replace('MO', '').replace('DGS', ''))
                maturity_days = months * 30
                description = f"US Treasury {months}-Month"
            elif 'Y' in str(period):
                years = int(str(period).replace('Y', '').replace('DGS', ''))
                maturity_days = years * 365
                description = f"US Treasury {years}-Year"
            else:
                maturity_days = 365
                description = f"US Treasury {period}"
            
            bond_metadata.append({
                'isin': f'US_TREASURY_{period}',
                'issuer_name': 'U.S. Department of Treasury',
                'bond_type': 'Government',
                'maturity_date': None,
                'coupon_rate': 0.0,
                'currency': 'USD',
                'country': 'USA',
                'description': description
            })
        
        bond_df = pd.DataFrame(bond_metadata)
        
        # Prepare yield data for loading (add ISIN)
        yield_data['isin'] = yield_data['period'].apply(lambda x: f'US_TREASURY_{x}')
        # Rename yield column to match expected schema
        if 'yield' in yield_data.columns:
            yield_data['yield_value'] = yield_data['yield']
        else:
            yield_data['yield_value'] = yield_data.get('Close', yield_data.get('close', 0))
        
        # For bonds, price is typically 100 (par) for yields
        yield_data['price'] = 100.0
        yield_data['yield'] = yield_data['yield_value']
        
        # ==================================================================
        # TRANSFORM PHASE
        # ==================================================================
        logger.info("\n" + "=" * 80)
        logger.info("TRANSFORM PHASE")
        logger.info("=" * 80)
        
        transformer = DataTransformer()
        
        # Transform date dimension
        logger.info("Transforming date dimension...")
        date_dim = transformer.transform_date_dimension(yield_data['date'])
        logger.info(f"Transformed {len(date_dim)} date records")
        
        # Transform issuer dimension
        logger.info("Transforming issuer dimension...")
        issuer_dim = transformer.transform_issuer_dimension(issuer_data)
        logger.info(f"Transformed {len(issuer_dim)} issuer records")
        
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
        
        logger.info("\nLoading issuer dimension...")
        issuer_mapping = loader.load_issuer(issuer_dim)
        logger.info(f"Loaded {len(issuer_mapping)} issuers")
        logger.info(f"Issuer mapping: {issuer_mapping}")
        
        # Transform and load bond dimension
        logger.info("\nTransforming bond dimension...")
        bond_dim = transformer.transform_bond_dimension(bond_df, issuer_mapping)
        logger.info(f"Transformed {len(bond_dim)} bond records")
        
        logger.info("\nLoading bond dimension...")
        bond_mapping = loader.load_bonds(bond_dim)
        logger.info(f"Loaded {len(bond_mapping)} bonds")
        
        # Transform fact table
        logger.info("\nTransforming bond price facts...")
        price_facts = transformer.transform_bond_prices(
            price_df=yield_data,
            bond_mapping=bond_mapping,
            date_mapping=date_mapping,
            source_id=source_id
        )
        logger.info(f"Transformed {len(price_facts)} price fact records")
        
        # Load fact table
        logger.info("\nLoading bond price facts...")
        records_loaded = loader.load_bond_prices(price_facts)
        logger.info(f"Loaded {records_loaded} new price records")
        
        # ==================================================================
        # VERIFICATION
        # ==================================================================
        logger.info("\n" + "=" * 80)
        logger.info("VERIFICATION")
        logger.info("=" * 80)
        
        from sqlalchemy import select, func
        from src.models import FactBondPrice, DimBond
        
        # Count records
        total_count = db.execute(
            select(func.count()).select_from(FactBondPrice)
        ).scalar()
        logger.info(f"Total bond price records in database: {total_count}")
        
        # Show sample records
        logger.info("\nSample bond price records:")
        sample = db.execute(
            select(
                DimBond.description,
                FactBondPrice.date_id,
                FactBondPrice.yield_percent
            ).join(
                DimBond,
                FactBondPrice.bond_id == DimBond.bond_id
            ).limit(5)
        ).all()
        
        for record in sample:
            logger.info(f"  {record.description}: Yield={record.yield_percent:.2f}% (Date ID: {record.date_id})")
        
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
    
    parser = argparse.ArgumentParser(description="Run bond ETL pipeline")
    parser.add_argument(
        "--periods",
        nargs="+",
        default=["3MO", "10Y", "30Y"],
        help="Bond periods to extract"
    )
    parser.add_argument(
        "--days",
        type=int,
        default=30,
        help="Number of days of historical data"
    )
    parser.add_argument(
        "--source",
        choices=["yahoo", "fred"],
        default="yahoo",
        help="Data source (yahoo or fred)"
    )
    
    args = parser.parse_args()
    
    run_bond_pipeline(
        periods=args.periods,
        days=args.days,
        source=args.source
    )
