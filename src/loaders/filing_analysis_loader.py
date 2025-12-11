"""Loader for SEC filing analysis results."""
import json
from typing import Dict
from loguru import logger
from sqlalchemy.orm import Session
from sqlalchemy import func
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from src.models import FactFilingAnalysis, FactSECFiling


class FilingAnalysisLoader:
    """Load filing analysis results into the database."""
    
    def __init__(self, db_session: Session):
        """
        Initialize the loader.
        
        Args:
            db_session: SQLAlchemy database session
        """
        self.session = db_session
        logger.info("Initialized FilingAnalysisLoader")
    
    def load_analysis(
        self,
        analysis_result: Dict,
        filing_id: int,
        company_id: int,
        date_id: int
    ) -> int:
        """
        Load analysis results for a single filing.
        
        Args:
            analysis_result: Dictionary from FilingAnalyzer.analyze_filing()
            filing_id: ID of the filing being analyzed
            company_id: Company ID
            date_id: Date ID
            
        Returns:
            analysis_id of the inserted/updated record
        """
        logger.info(f"Loading analysis for filing_id={filing_id}")
        
        # Extract section word counts
        sections = analysis_result.get('sections', {})
        
        # Serialize financial mentions to JSON
        financial_mentions = analysis_result.get('financial_mentions', {})
        
        # Prepare record
        record = {
            'filing_id': filing_id,
            'company_id': company_id,
            'date_id': date_id,
            'sections_found': analysis_result['metadata']['sections_found'],
            'business_word_count': sections.get('business', {}).get('stats', {}).get('word_count'),
            'risk_factors_word_count': sections.get('risk_factors', {}).get('stats', {}).get('word_count'),
            'mda_word_count': sections.get('mda', {}).get('stats', {}).get('word_count'),
            'financials_word_count': sections.get('financials', {}).get('stats', {}).get('word_count'),
            'revenue_mentions': json.dumps(financial_mentions.get('revenue', [])),
            'net_income_mentions': json.dumps(financial_mentions.get('net_income', [])),
            'earnings_mentions': json.dumps(financial_mentions.get('earnings', [])),
            'cash_mentions': json.dumps(financial_mentions.get('cash', [])),
            'debt_mentions': json.dumps(financial_mentions.get('debt', [])),
            'risk_keywords': json.dumps(analysis_result.get('risk_keywords', [])),
            'total_word_count': analysis_result['metadata']['total_word_count'],
            'total_char_count': analysis_result['metadata']['total_char_count'],
            'financial_mentions_count': analysis_result['metadata']['total_mentions']
        }
        
        try:
            # Upsert: update if exists, insert if not
            stmt = sqlite_insert(FactFilingAnalysis).values(record)
            stmt = stmt.on_conflict_do_update(
                index_elements=['filing_id'],
                set_={
                    'sections_found': stmt.excluded.sections_found,
                    'business_word_count': stmt.excluded.business_word_count,
                    'risk_factors_word_count': stmt.excluded.risk_factors_word_count,
                    'mda_word_count': stmt.excluded.mda_word_count,
                    'financials_word_count': stmt.excluded.financials_word_count,
                    'revenue_mentions': stmt.excluded.revenue_mentions,
                    'net_income_mentions': stmt.excluded.net_income_mentions,
                    'earnings_mentions': stmt.excluded.earnings_mentions,
                    'cash_mentions': stmt.excluded.cash_mentions,
                    'debt_mentions': stmt.excluded.debt_mentions,
                    'risk_keywords': stmt.excluded.risk_keywords,
                    'total_word_count': stmt.excluded.total_word_count,
                    'total_char_count': stmt.excluded.total_char_count,
                    'financial_mentions_count': stmt.excluded.financial_mentions_count,
                }
            )
            
            result = self.session.execute(stmt)
            self.session.commit()
            
            # Get the analysis_id
            analysis = self.session.query(FactFilingAnalysis).filter_by(filing_id=filing_id).first()
            
            logger.info(f"Loaded analysis for filing_id={filing_id}, analysis_id={analysis.analysis_id}")
            return analysis.analysis_id
            
        except Exception as e:
            logger.error(f"Error loading analysis: {str(e)}")
            self.session.rollback()
            raise
    
    def get_analysis_stats(self) -> Dict:
        """
        Get statistics about loaded analyses.
        
        Returns:
            Dictionary with statistics
        """
        try:
            total_analyses = self.session.query(FactFilingAnalysis).count()
            
            avg_sections = self.session.query(
                func.avg(FactFilingAnalysis.sections_found)
            ).scalar()
            
            avg_word_count = self.session.query(
                func.avg(FactFilingAnalysis.total_word_count)
            ).scalar()
            
            stats = {
                'total_analyses': total_analyses,
                'avg_sections_found': round(avg_sections, 1) if avg_sections else 0,
                'avg_word_count': int(avg_word_count) if avg_word_count else 0
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting analysis statistics: {str(e)}")
            return {}
