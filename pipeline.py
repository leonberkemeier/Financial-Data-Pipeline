"""Main ETL pipeline orchestrator."""
import sys
from datetime import datetime, timedelta
from loguru import logger

from config.config import TICKERS, BATCH_SIZE
from src.utils import setup_logger, DataQualityValidator
from src.extractors import YahooFinanceExtractor, AlphaVantageExtractor
from src.transformers import DataTransformer
from src.loaders import DataLoader
from src.models import SessionLocal, init_db


class FinancialDataPipeline:
    """Main ETL pipeline for financial data aggregation."""

    def __init__(self, data_source: str = "yahoo"):
        """
        Initialize the pipeline.

        Args:
            data_source: Data source to use ('yahoo' or 'alpha_vantage')
        """
        setup_logger()
        self.data_source = data_source
        
        # Initialize extractors
        if data_source == "yahoo":
            self.extractor = YahooFinanceExtractor()
        elif data_source == "alpha_vantage":
            self.extractor = AlphaVantageExtractor()
        else:
            raise ValueError(f"Unknown data source: {data_source}")
        
        self.transformer = DataTransformer()
        self.validator = DataQualityValidator()
        
        logger.info(f"Initialized pipeline with {data_source} data source")

    def run(self, tickers: list = None, period: str = "1mo", start_date: str = None, end_date: str = None):
        """
        Run the complete ETL pipeline.

        Args:
            tickers: List of stock tickers (default: from config)
            period: Period to fetch data for (e.g., '1mo', '1y')
            start_date: Start date in 'YYYY-MM-DD' format
            end_date: End date in 'YYYY-MM-DD' format
        """
        try:
            logger.info("=" * 80)
            logger.info("Starting Financial Data ETL Pipeline")
            logger.info("=" * 80)
            
            # Use default tickers if not provided
            if tickers is None:
                tickers = TICKERS
            
            logger.info(f"Processing {len(tickers)} tickers: {tickers}")
            
            # Initialize database
            logger.info("Initializing database...")
            init_db()
            
            # Extract data
            logger.info("=" * 80)
            logger.info("EXTRACT PHASE")
            logger.info("=" * 80)
            
            if self.data_source == "yahoo":
                price_data = self.extractor.extract_stock_prices(
                    tickers=tickers,
                    start_date=start_date,
                    end_date=end_date,
                    period=period
                )
                company_data = self.extractor.extract_company_info(tickers)
            elif self.data_source == "alpha_vantage":
                price_data = self.extractor.extract_daily_prices(tickers)
                # Alpha Vantage company info would require separate calls per ticker
                company_data = None
            
            if price_data.empty:
                logger.error("No price data extracted. Aborting pipeline.")
                return False
            
            logger.info(f"Extracted {len(price_data)} price records")
            
            # Validate extracted data
            is_valid, errors = self.validator.validate_stock_prices(price_data)
            if not is_valid:
                logger.error("Data quality validation failed. Aborting pipeline.")
                return False
            
            # Get data summary
            summary = self.validator.get_data_summary(price_data)
            logger.info(f"Data summary: {summary}")
            
            # Transform data
            logger.info("=" * 80)
            logger.info("TRANSFORM PHASE")
            logger.info("=" * 80)
            
            # Transform dimensions
            date_dim = self.transformer.transform_date_dimension(price_data['date'])
            
            if company_data is not None and not company_data.empty:
                company_dim = self.transformer.transform_company_dimension(company_data)
                exchange_dim = self.transformer.transform_exchange_dimension(company_data)
            else:
                # Create minimal company dimension from price data
                logger.warning("No company data available. Creating minimal company dimension.")
                company_dim = price_data[['ticker']].drop_duplicates()
                company_dim['company_name'] = company_dim['ticker']
                company_dim['sector'] = 'Unknown'
                company_dim['industry'] = 'Unknown'
                company_dim['country'] = 'Unknown'
                exchange_dim = None
            
            # Load data
            logger.info("=" * 80)
            logger.info("LOAD PHASE")
            logger.info("=" * 80)
            
            db_session = SessionLocal()
            try:
                loader = DataLoader(db_session)
                
                # Load data source
                source_id = loader.load_or_get_data_source(
                    source_name=self.extractor.source_name,
                    source_type="API"
                )
                
                # Load dimensions
                company_mapping = loader.load_companies(company_dim)
                date_mapping = loader.load_dates(date_dim)
                
                if exchange_dim is not None and not exchange_dim.empty:
                    exchange_mapping = loader.load_exchanges(exchange_dim)
                
                # Transform facts with mappings
                price_facts = self.transformer.transform_stock_prices(
                    price_df=price_data,
                    company_mapping=company_mapping,
                    date_mapping=date_mapping,
                    source_id=source_id
                )
                
                # Load facts
                records_loaded = loader.load_stock_prices(price_facts, batch_size=BATCH_SIZE)
                
                logger.info("=" * 80)
                logger.info("PIPELINE COMPLETED SUCCESSFULLY")
                logger.info("=" * 80)
                logger.info(f"Loaded {records_loaded} new stock price records")
                logger.info(f"Total records in price_facts: {len(price_facts)}")
                
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
    
    parser = argparse.ArgumentParser(description="Financial Data ETL Pipeline")
    parser.add_argument(
        "--source",
        choices=["yahoo", "alpha_vantage"],
        default="yahoo",
        help="Data source to use"
    )
    parser.add_argument(
        "--tickers",
        nargs="+",
        help="Stock tickers to process (default: from config)"
    )
    parser.add_argument(
        "--period",
        default="max",
        help="Period to fetch (e.g., 1d, 5d, 1mo, 1y, max)"
    )
    parser.add_argument(
        "--start-date",
        help="Start date in YYYY-MM-DD format"
    )
    parser.add_argument(
        "--end-date",
        help="End date in YYYY-MM-DD format"
    )
    
    args = parser.parse_args()
    
    # Create and run pipeline
    pipeline = FinancialDataPipeline(data_source=args.source)
    success = pipeline.run(
        tickers=args.tickers,
        period=args.period,
        start_date=args.start_date,
        end_date=args.end_date
    )
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
