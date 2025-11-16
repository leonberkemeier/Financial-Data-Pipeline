"""Example script for extracting and loading SEC EDGAR filings."""
import sys
from datetime import datetime, timedelta
from loguru import logger

from config.config import TICKERS
from src.utils import setup_logger
from src.extractors import SECEdgarExtractor
from src.loaders import DataLoader
from src.loaders.sec_loader import SECFilingLoader
from src.models import SessionLocal, init_db
from src.transformers import DataTransformer


def run_sec_filing_pipeline(
    tickers: list = None,
    filing_types: list = None,
    start_date: str = None,
    end_date: str = None,
    count_per_ticker: int = 5
):
    """
    Run SEC filing extraction and loading pipeline.
    
    Args:
        tickers: List of stock tickers
        filing_types: List of filing types (e.g., ['10-K', '10-Q'])
        start_date: Start date in 'YYYY-MM-DD' format
        end_date: End date in 'YYYY-MM-DD' format
        count_per_ticker: Max filings per ticker to retrieve
    """
    try:
        setup_logger()
        
        logger.info("=" * 80)
        logger.info("Starting SEC EDGAR Filing Pipeline")
        logger.info("=" * 80)
        
        # Default parameters
        if tickers is None:
            tickers = TICKERS[:3]  # Use first 3 tickers for demo
        
        if filing_types is None:
            filing_types = ['10-K', '10-Q']
        
        # Default to last year if no date range provided
        if not start_date:
            start_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
        
        logger.info(f"Processing tickers: {tickers}")
        logger.info(f"Filing types: {filing_types}")
        logger.info(f"Date range: {start_date} to {end_date or 'present'}")
        
        # Initialize database
        logger.info("Initializing database...")
        init_db()
        
        # EXTRACT PHASE
        logger.info("=" * 80)
        logger.info("EXTRACT PHASE")
        logger.info("=" * 80)
        
        extractor = SECEdgarExtractor()
        
        filings_df = extractor.extract_filings_batch(
            tickers=tickers,
            filing_types=filing_types,
            start_date=start_date,
            end_date=end_date,
            count_per_ticker=count_per_ticker
        )
        
        if filings_df.empty:
            logger.error("No filings extracted. Aborting pipeline.")
            return False
        
        logger.info(f"Extracted {len(filings_df)} filings")
        logger.info(f"Filings by type:\n{filings_df['filing_type'].value_counts()}")
        
        # TRANSFORM PHASE
        logger.info("=" * 80)
        logger.info("TRANSFORM PHASE")
        logger.info("=" * 80)
        
        transformer = DataTransformer()
        
        # Create date dimension from filing dates
        date_dim = transformer.transform_date_dimension(filings_df['filing_date'])
        
        # Create minimal company dimension if needed
        company_dim = filings_df[['ticker']].drop_duplicates()
        company_dim['company_name'] = company_dim['ticker']
        company_dim['sector'] = 'Unknown'
        company_dim['industry'] = 'Unknown'
        company_dim['country'] = 'US'
        
        # LOAD PHASE
        logger.info("=" * 80)
        logger.info("LOAD PHASE")
        logger.info("=" * 80)
        
        db_session = SessionLocal()
        
        try:
            # Initialize loaders
            data_loader = DataLoader(db_session)
            sec_loader = SECFilingLoader(db_session)
            
            # Load data source
            source_id = data_loader.load_or_get_data_source(
                source_name="sec_edgar",
                source_type="API"
            )
            
            # Load dimensions
            company_mapping = data_loader.load_companies(company_dim)
            date_mapping = data_loader.load_dates(date_dim)
            filing_type_mapping = sec_loader.load_filing_types()
            
            logger.info(f"Loaded {len(company_mapping)} companies")
            logger.info(f"Loaded {len(date_mapping)} dates")
            logger.info(f"Loaded {len(filing_type_mapping)} filing types")
            
            # Load SEC filings
            records_loaded = sec_loader.load_sec_filings(
                filings_df=filings_df,
                company_mapping=company_mapping,
                date_mapping=date_mapping,
                filing_type_mapping=filing_type_mapping,
                source_id=source_id,
                batch_size=50
            )
            
            # Get statistics
            stats = sec_loader.get_filing_statistics()
            
            logger.info("=" * 80)
            logger.info("PIPELINE COMPLETED SUCCESSFULLY")
            logger.info("=" * 80)
            logger.info(f"Loaded {records_loaded} new filing records")
            logger.info(f"Total filings in database: {stats.get('total_filings', 'N/A')}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error during load phase: {str(e)}")
            db_session.rollback()
            raise
        finally:
            db_session.close()
    
    except Exception as e:
        logger.error("=" * 80)
        logger.error(f"PIPELINE FAILED: {str(e)}")
        logger.error("=" * 80)
        logger.exception(e)
        return False


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="SEC EDGAR Filing Pipeline")
    parser.add_argument(
        "--tickers",
        nargs="+",
        help="Stock tickers to process"
    )
    parser.add_argument(
        "--filing-types",
        nargs="+",
        default=['10-K', '10-Q'],
        help="Filing types to extract (e.g., 10-K 10-Q 8-K)"
    )
    parser.add_argument(
        "--start-date",
        help="Start date in YYYY-MM-DD format"
    )
    parser.add_argument(
        "--end-date",
        help="End date in YYYY-MM-DD format"
    )
    parser.add_argument(
        "--count",
        type=int,
        default=5,
        help="Maximum filings per ticker"
    )
    
    args = parser.parse_args()
    
    success = run_sec_filing_pipeline(
        tickers=args.tickers,
        filing_types=args.filing_types,
        start_date=args.start_date,
        end_date=args.end_date,
        count_per_ticker=args.count
    )
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
