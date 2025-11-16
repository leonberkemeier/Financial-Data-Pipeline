"""Loader for SEC EDGAR filing data."""
import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional
from loguru import logger
from sqlalchemy.orm import Session
from sqlalchemy import insert, update
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from src.models import (
    DimCompany, DimFilingType, DimDate, DimDataSource,
    FactSECFiling
)


class SECFilingLoader:
    """Load SEC filing data into the data warehouse."""

    def __init__(self, db_session: Session):
        """
        Initialize the SEC filing loader.
        
        Args:
            db_session: SQLAlchemy database session
        """
        self.session = db_session
        logger.info("Initialized SEC filing loader")

    def load_or_get_filing_type(self, filing_type: str, description: str = None, category: str = None) -> int:
        """
        Load or get filing type dimension.
        
        Args:
            filing_type: Filing type code (e.g., '10-K', '10-Q')
            description: Description of the filing type
            category: Category (Annual, Quarterly, Current, etc.)
            
        Returns:
            filing_type_id
        """
        # Check if exists
        existing = self.session.query(DimFilingType).filter_by(filing_type=filing_type).first()
        
        if existing:
            return existing.filing_type_id
        
        # Create new
        filing_type_obj = DimFilingType(
            filing_type=filing_type,
            description=description,
            category=category
        )
        
        self.session.add(filing_type_obj)
        self.session.flush()
        
        logger.debug(f"Created filing type: {filing_type}")
        return filing_type_obj.filing_type_id

    def load_filing_types(self) -> Dict[str, int]:
        """
        Load standard SEC filing types.
        
        Returns:
            Dictionary mapping filing type to filing_type_id
        """
        filing_types_data = [
            {'type': '10-K', 'description': 'Annual report', 'category': 'Annual'},
            {'type': '10-Q', 'description': 'Quarterly report', 'category': 'Quarterly'},
            {'type': '8-K', 'description': 'Current report', 'category': 'Current'},
            {'type': '10-K/A', 'description': 'Amended annual report', 'category': 'Annual'},
            {'type': '10-Q/A', 'description': 'Amended quarterly report', 'category': 'Quarterly'},
            {'type': 'S-1', 'description': 'Registration statement', 'category': 'Registration'},
            {'type': 'DEF 14A', 'description': 'Proxy statement', 'category': 'Proxy'},
        ]
        
        mapping = {}
        
        for ft in filing_types_data:
            filing_type_id = self.load_or_get_filing_type(
                filing_type=ft['type'],
                description=ft['description'],
                category=ft['category']
            )
            mapping[ft['type']] = filing_type_id
        
        self.session.commit()
        logger.info(f"Loaded {len(mapping)} filing types")
        
        return mapping

    def load_sec_filings(
        self,
        filings_df: pd.DataFrame,
        company_mapping: Dict[str, int],
        date_mapping: Dict[str, int],
        filing_type_mapping: Dict[str, int],
        source_id: int,
        batch_size: int = 100,
        extract_text: bool = False
    ) -> int:
        """
        Load SEC filings into fact table.
        
        Args:
            filings_df: DataFrame with filing data
            company_mapping: Mapping of ticker to company_id
            date_mapping: Mapping of date string to date_id
            filing_type_mapping: Mapping of filing type to filing_type_id
            source_id: Data source ID
            batch_size: Number of records per batch
            extract_text: Whether filing text was extracted
            
        Returns:
            Number of new filings loaded
        """
        if filings_df.empty:
            logger.warning("No filings to load")
            return 0
        
        logger.info(f"Loading {len(filings_df)} SEC filings...")
        
        records_to_insert = []
        
        for _, row in filings_df.iterrows():
            ticker = row['ticker']
            filing_type = row['filing_type']
            filing_date = row['filing_date']
            
            # Get foreign keys
            company_id = company_mapping.get(ticker)
            date_id = date_mapping.get(filing_date)
            filing_type_id = filing_type_mapping.get(filing_type)
            
            if not all([company_id, date_id, filing_type_id]):
                logger.warning(f"Skipping filing: missing foreign key for {ticker}/{filing_type}/{filing_date}")
                continue
            
            # Parse accepted_date if present
            accepted_date = None
            if pd.notna(row.get('accepted_date')):
                try:
                    accepted_date = datetime.fromisoformat(row['accepted_date'].replace('Z', '+00:00'))
                except:
                    pass
            
            record = {
                'company_id': company_id,
                'filing_type_id': filing_type_id,
                'date_id': date_id,
                'source_id': source_id,
                'cik': row.get('cik'),
                'accession_number': row.get('accession_number'),
                'file_number': row.get('file_number'),
                'accepted_date': accepted_date,
                'filing_url': row.get('filing_url'),
                'filing_text': row.get('filing_text') if extract_text else None,
                'filing_size': len(row.get('filing_text', '')) if extract_text and pd.notna(row.get('filing_text')) else None,
            }
            
            records_to_insert.append(record)
        
        if not records_to_insert:
            logger.warning("No valid records to insert")
            return 0
        
        # Batch insert with upsert logic
        new_count = 0
        
        for i in range(0, len(records_to_insert), batch_size):
            batch = records_to_insert[i:i + batch_size]
            
            try:
                # SQLite upsert
                stmt = sqlite_insert(FactSECFiling).values(batch)
                stmt = stmt.on_conflict_do_update(
                    index_elements=['accession_number'],
                    set_={
                        'filing_url': stmt.excluded.filing_url,
                        'filing_text': stmt.excluded.filing_text,
                        'filing_size': stmt.excluded.filing_size,
                    }
                )
                
                result = self.session.execute(stmt)
                new_count += result.rowcount
                
                self.session.commit()
                logger.debug(f"Inserted batch {i//batch_size + 1}: {len(batch)} records")
                
            except Exception as e:
                logger.error(f"Error inserting batch: {str(e)}")
                self.session.rollback()
                continue
        
        logger.info(f"Loaded {new_count} new SEC filings")
        return new_count

    def get_filing_statistics(self) -> Dict:
        """
        Get statistics about loaded filings.
        
        Returns:
            Dictionary with filing statistics
        """
        try:
            total_filings = self.session.query(FactSECFiling).count()
            
            filings_by_type = (
                self.session.query(
                    DimFilingType.filing_type,
                    self.session.query(FactSECFiling)
                    .filter(FactSECFiling.filing_type_id == DimFilingType.filing_type_id)
                    .count()
                    .label('count')
                )
                .all()
            )
            
            stats = {
                'total_filings': total_filings,
                'filings_by_type': {ft: count for ft, count in filings_by_type}
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting filing statistics: {str(e)}")
            return {}
