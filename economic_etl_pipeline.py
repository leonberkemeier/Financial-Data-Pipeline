"""Economic Indicators ETL Pipeline - Extract, Transform, Load economic data."""
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
from loguru import logger

from src.extractors.economic_indicators import EconomicIndicatorsExtractor
from src.transformers.data_transformer import DataTransformer
from src.loaders.data_loader import DataLoader
from src.models.base import SessionLocal, init_db

# Load environment variables
load_dotenv()


def run_economic_pipeline(
    indicators: list = None,
    days: int = 365,
    source_name: str = "fred_economic"
):
    """
    Run the complete economic indicators ETL pipeline.
    
    Args:
        indicators: List of indicator codes (e.g., ['GDP', 'UNRATE', 'CPIAUCSL'])
        days: Number of days of historical data
        source_name: Name of the data source
    """
    if indicators is None:
        indicators = ['GDP', 'UNRATE', 'CPIAUCSL', 'FEDFUNDS']
    
    logger.info("=" * 80)
    logger.info("ECONOMIC INDICATORS ETL PIPELINE")
    logger.info("=" * 80)
    logger.info(f"Indicators: {indicators}")
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
        
        fred_api_key = os.getenv('FRED_API_KEY')
        if not fred_api_key:
            logger.error("FRED_API_KEY not set. Cannot extract economic indicators.")
            return
        
        extractor = EconomicIndicatorsExtractor(api_key=fred_api_key)
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        # Extract economic data
        logger.info(f"Extracting economic indicators...")
        economic_data = extractor.extract_indicators(
            indicators=indicators,
            start_date=start_date.strftime('%Y-%m-%d'),
            end_date=end_date.strftime('%Y-%m-%d')
        )
        
        if economic_data.empty:
            logger.error("No economic data extracted. Aborting pipeline.")
            return
        
        logger.info(f"Extracted {len(economic_data)} economic data records")
        logger.info(f"Date range: {economic_data['date'].min()} to {economic_data['date'].max()}")
        logger.info(f"Indicators: {economic_data['indicator'].unique().tolist()}")
        
        # ==================================================================
        # TRANSFORM PHASE
        # ==================================================================
        logger.info("\n" + "=" * 80)
        logger.info("TRANSFORM PHASE")
        logger.info("=" * 80)
        
        transformer = DataTransformer()
        
        # Transform date dimension
        logger.info("Transforming date dimension...")
        date_dim = transformer.transform_date_dimension(economic_data['date'])
        logger.info(f"Transformed {len(date_dim)} date records")
        
        # Transform economic indicator dimension
        logger.info("Transforming economic indicator dimension...")
        indicator_dim = transformer.transform_economic_indicator_dimension(economic_data)
        logger.info(f"Transformed {len(indicator_dim)} indicator records")
        
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
        
        logger.info("\nLoading economic indicator dimension...")
        indicator_mapping = loader.load_economic_indicators(indicator_dim)
        logger.info(f"Loaded {len(indicator_mapping)} indicators")
        logger.info(f"Indicator mapping: {indicator_mapping}")
        
        # Transform fact table
        logger.info("\nTransforming economic data facts...")
        data_facts = transformer.transform_economic_data(
            data_df=economic_data,
            indicator_mapping=indicator_mapping,
            date_mapping=date_mapping,
            source_id=source_id
        )
        logger.info(f"Transformed {len(data_facts)} data fact records")
        
        # Load fact table
        logger.info("\nLoading economic data facts...")
        records_loaded = loader.load_economic_data(data_facts)
        logger.info(f"Loaded {records_loaded} new data records")
        
        # ==================================================================
        # VERIFICATION
        # ==================================================================
        logger.info("\n" + "=" * 80)
        logger.info("VERIFICATION")
        logger.info("=" * 80)
        
        from sqlalchemy import select, func
        from src.models import FactEconomicIndicator, DimEconomicIndicator
        
        # Count records
        total_count = db.execute(
            select(func.count()).select_from(FactEconomicIndicator)
        ).scalar()
        logger.info(f"Total economic data records in database: {total_count}")
        
        # Show sample records
        logger.info("\nSample economic data records:")
        sample = db.execute(
            select(
                DimEconomicIndicator.indicator_code,
                DimEconomicIndicator.indicator_name,
                FactEconomicIndicator.date_id,
                FactEconomicIndicator.value
            ).join(
                DimEconomicIndicator,
                FactEconomicIndicator.indicator_id == DimEconomicIndicator.indicator_id
            ).limit(5)
        ).all()
        
        for record in sample:
            logger.info(f"  {record.indicator_code} ({record.indicator_name}): {record.value:.2f} (Date ID: {record.date_id})")
        
        # Show latest values for each indicator
        logger.info("\nLatest values per indicator:")
        for indicator in indicators:
            latest = db.execute(
                select(
                    DimEconomicIndicator.indicator_name,
                    FactEconomicIndicator.value,
                    FactEconomicIndicator.date_id
                ).join(
                    DimEconomicIndicator,
                    FactEconomicIndicator.indicator_id == DimEconomicIndicator.indicator_id
                ).where(
                    DimEconomicIndicator.indicator_code == indicator
                ).order_by(
                    FactEconomicIndicator.date_id.desc()
                ).limit(1)
            ).first()
            
            if latest:
                logger.info(f"  {latest.indicator_name}: {latest.value:.2f}")
        
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
    
    parser = argparse.ArgumentParser(description="Run economic indicators ETL pipeline")
    parser.add_argument(
        "--indicators",
        nargs="+",
        default=["GDP", "UNRATE", "CPIAUCSL", "FEDFUNDS"],
        help="Economic indicator codes to extract"
    )
    parser.add_argument(
        "--days",
        type=int,
        default=365,
        help="Number of days of historical data"
    )
    
    args = parser.parse_args()
    
    run_economic_pipeline(
        indicators=args.indicators,
        days=args.days
    )
