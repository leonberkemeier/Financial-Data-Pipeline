"""
Complete ETL Pipeline for SEC Filings with Text Extraction and Analysis.

This pipeline demonstrates:
1. EXTRACT: Fetch SEC filings from SEC EDGAR API
2. TRANSFORM: Extract text, analyze sections, extract financial metrics
3. LOAD: Store filings, text, and analysis results in star schema database
"""
import sys
from datetime import datetime, timedelta
from loguru import logger

from config.config import TICKERS
from src.utils import setup_logger
from src.extractors import SECEdgarExtractor
from src.analyzers import FilingAnalyzer
from src.loaders import DataLoader
from src.loaders.sec_loader import SECFilingLoader
from src.loaders.filing_analysis_loader import FilingAnalysisLoader
from src.models import SessionLocal, init_db
from src.transformers import DataTransformer


def run_sec_etl_pipeline(
    tickers: list = None,
    filing_types: list = None,
    start_date: str = None,
    end_date: str = None,
    count_per_ticker: int = 3,
    analyze: bool = True
):
    """
    Run complete SEC filing ETL pipeline with analysis.
    
    Args:
        tickers: List of stock tickers
        filing_types: List of filing types (e.g., ['10-K', '10-Q'])
        start_date: Start date in 'YYYY-MM-DD' format
        end_date: End date in 'YYYY-MM-DD' format
        count_per_ticker: Max filings per ticker to retrieve
        analyze: Whether to analyze filing text
    """
    try:
        setup_logger()
        
        logger.info("=" * 80)
        logger.info("SEC FILING ETL PIPELINE - Full Text Extraction & Analysis")
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
        logger.info(f"Analysis enabled: {analyze}")
        
        # Initialize database
        logger.info("Initializing database...")
        init_db()
        
        # =====================================================================
        # PHASE 1: EXTRACT - Fetch filings from SEC EDGAR
        # =====================================================================
        logger.info("=" * 80)
        logger.info("PHASE 1: EXTRACT - Fetching SEC Filings")
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
        
        logger.info(f"Extracted {len(filings_df)} filing metadata records")
        logger.info(f"Filings by type:\n{filings_df['filing_type'].value_counts()}")
        
        # Extract full text for each filing
        logger.info("Extracting filing text content...")
        filing_texts = []
        
        for idx, row in filings_df.iterrows():
            try:
                logger.info(f"Extracting text for {row['ticker']} {row['filing_type']} ({idx+1}/{len(filings_df)})")
                text = extractor.extract_filing_text(row['filing_url'])
                
                if text:
                    filing_texts.append(text)
                    filings_df.at[idx, 'filing_text'] = text
                    filings_df.at[idx, 'filing_size'] = len(text)
                    logger.info(f"  Extracted {len(text):,} characters")
                else:
                    filing_texts.append(None)
                    logger.warning(f"  Failed to extract text")
                    
            except Exception as e:
                logger.error(f"Error extracting text for {row['ticker']}: {str(e)}")
                filing_texts.append(None)
        
        successful_extractions = sum(1 for t in filing_texts if t)
        logger.info(f"Successfully extracted text from {successful_extractions}/{len(filings_df)} filings")
        
        # =====================================================================
        # PHASE 2: TRANSFORM - Analyze filing content
        # =====================================================================
        logger.info("=" * 80)
        logger.info("PHASE 2: TRANSFORM - Analyzing Filings")
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
        
        # Analyze filings if enabled
        analysis_results = []
        
        if analyze and successful_extractions > 0:
            logger.info("Starting filing analysis...")
            analyzer = FilingAnalyzer()
            
            for idx, row in filings_df.iterrows():
                if row.get('filing_text'):
                    try:
                        logger.info(f"Analyzing {row['ticker']} {row['filing_type']} ({idx+1}/{len(filings_df)})")
                        
                        analysis = analyzer.analyze_filing(
                            filing_text=row['filing_text'],
                            ticker=row['ticker'],
                            filing_type=row['filing_type'],
                            filing_date=row['filing_date']
                        )
                        
                        # Extract risk keywords if risk factors section exists
                        sections = analyzer.extract_all_sections(row['filing_text'])
                        if 'risk_factors' in sections:
                            risk_keywords = analyzer.extract_risk_keywords(sections['risk_factors'])
                            analysis['risk_keywords'] = risk_keywords
                        
                        analysis_results.append({
                            'ticker': row['ticker'],
                            'filing_date': row['filing_date'],
                            'filing_type': row['filing_type'],
                            'analysis': analysis
                        })
                        
                        logger.info(f"  Found {analysis['metadata']['sections_found']} sections")
                        logger.info(f"  Extracted {analysis['metadata']['total_mentions']} financial mentions")
                        
                    except Exception as e:
                        logger.error(f"Error analyzing {row['ticker']}: {str(e)}")
                        continue
            
            logger.info(f"Completed analysis of {len(analysis_results)} filings")
        
        # =====================================================================
        # PHASE 3: LOAD - Store in database
        # =====================================================================
        logger.info("=" * 80)
        logger.info("PHASE 3: LOAD - Storing in Database")
        logger.info("=" * 80)
        
        db_session = SessionLocal()
        
        try:
            # Initialize loaders
            data_loader = DataLoader(db_session)
            sec_loader = SECFilingLoader(db_session)
            analysis_loader = FilingAnalysisLoader(db_session) if analyze else None
            
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
            
            # Load SEC filings (with text)
            filings_loaded = sec_loader.load_sec_filings(
                filings_df=filings_df,
                company_mapping=company_mapping,
                date_mapping=date_mapping,
                filing_type_mapping=filing_type_mapping,
                source_id=source_id,
                batch_size=50,
                extract_text=True  # Text is already extracted
            )
            
            logger.info(f"Loaded {filings_loaded} filing records with text")
            
            # Load analysis results
            if analyze and analysis_results:
                logger.info("Loading analysis results...")
                analyses_loaded = 0
                
                for result in analysis_results:
                    try:
                        # Get filing_id from database
                        from src.models import FactSECFiling
                        
                        # Convert filing_date string to date object for lookup
                        filing_date_obj = datetime.strptime(result['filing_date'], '%Y-%m-%d').date()
                        
                        filing = db_session.query(FactSECFiling).filter(
                            FactSECFiling.company_id == company_mapping[result['ticker']],
                            FactSECFiling.date_id == date_mapping[filing_date_obj]
                        ).first()
                        
                        if filing:
                            analysis_loader.load_analysis(
                                analysis_result=result['analysis'],
                                filing_id=filing.filing_id,
                                company_id=company_mapping[result['ticker']],
                                date_id=date_mapping[filing_date_obj]
                            )
                            analyses_loaded += 1
                        else:
                            logger.warning(f"Could not find filing for {result['ticker']} {result['filing_date']}")
                            
                    except Exception as e:
                        logger.error(f"Error loading analysis for {result['ticker']}: {str(e)}")
                        continue
                
                logger.info(f"Loaded {analyses_loaded} analysis records")
                
                # Get analysis statistics
                if analyses_loaded > 0:
                    analysis_stats = analysis_loader.get_analysis_stats()
                    logger.info(f"Analysis statistics: {analysis_stats}")
            
            # Get filing statistics
            filing_stats = sec_loader.get_filing_statistics()
            
            logger.info("=" * 80)
            logger.info("PIPELINE COMPLETED SUCCESSFULLY")
            logger.info("=" * 80)
            logger.info(f"Filings loaded: {filings_loaded}")
            logger.info(f"Text extracted: {successful_extractions}")
            if analyze:
                logger.info(f"Analyses loaded: {analyses_loaded}")
            logger.info(f"Total filings in database: {filing_stats.get('total_filings', 'N/A')}")
            
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
    
    parser = argparse.ArgumentParser(description="SEC Filing ETL Pipeline with Analysis")
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
        default=3,
        help="Maximum filings per ticker (default: 3 for demo)"
    )
    parser.add_argument(
        "--no-analyze",
        action="store_true",
        help="Skip analysis step (only extract and store text)"
    )
    
    args = parser.parse_args()
    
    success = run_sec_etl_pipeline(
        tickers=args.tickers,
        filing_types=args.filing_types,
        start_date=args.start_date,
        end_date=args.end_date,
        count_per_ticker=args.count,
        analyze=not args.no_analyze
    )
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
