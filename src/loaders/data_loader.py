"""Load transformed data into the database."""
import pandas as pd
from sqlalchemy.orm import Session
from sqlalchemy import select
from typing import Dict, List
from loguru import logger

from src.models import (
    DimCompany, DimDate, DimExchange, DimDataSource,
    FactStockPrice, FactCompanyMetrics
)


class DataLoader:
    """Load data into star schema database."""

    def __init__(self, db_session: Session):
        self.db = db_session

    def load_or_get_data_source(self, source_name: str, source_type: str = "API") -> int:
        """
        Load or retrieve data source dimension.

        Args:
            source_name: Name of the data source
            source_type: Type of data source

        Returns:
            source_id
        """
        # Check if exists
        source = self.db.execute(
            select(DimDataSource).where(DimDataSource.source_name == source_name)
        ).scalar_one_or_none()
        
        if source:
            logger.debug(f"Found existing data source: {source_name}")
            return source.source_id
        
        # Create new
        source = DimDataSource(
            source_name=source_name,
            source_type=source_type,
            description=f"Data from {source_name}"
        )
        self.db.add(source)
        self.db.commit()
        self.db.refresh(source)
        
        logger.info(f"Created new data source: {source_name} (ID: {source.source_id})")
        return source.source_id

    def load_companies(self, company_df: pd.DataFrame) -> Dict[str, int]:
        """
        Load company dimension data.

        Args:
            company_df: DataFrame with company data

        Returns:
            Dictionary mapping ticker to company_id
        """
        logger.info(f"Loading {len(company_df)} companies")
        
        company_mapping = {}
        
        for _, row in company_df.iterrows():
            # Check if exists
            company = self.db.execute(
                select(DimCompany).where(DimCompany.ticker == row['ticker'])
            ).scalar_one_or_none()
            
            if company:
                # Update existing
                company.company_name = row.get('company_name', company.company_name)
                company.sector = row.get('sector', company.sector)
                company.industry = row.get('industry', company.industry)
                company.country = row.get('country', company.country)
                logger.debug(f"Updated company: {row['ticker']}")
            else:
                # Create new
                company = DimCompany(
                    ticker=row['ticker'],
                    company_name=row.get('company_name', row['ticker']),
                    sector=row.get('sector'),
                    industry=row.get('industry'),
                    country=row.get('country')
                )
                self.db.add(company)
                logger.debug(f"Created company: {row['ticker']}")
            
            self.db.commit()
            self.db.refresh(company)
            company_mapping[row['ticker']] = company.company_id
        
        logger.info(f"Loaded {len(company_mapping)} companies")
        return company_mapping

    def load_dates(self, date_df: pd.DataFrame) -> Dict:
        """
        Load date dimension data.

        Args:
            date_df: DataFrame with date data

        Returns:
            Dictionary mapping date to date_id
        """
        logger.info(f"Loading {len(date_df)} dates")
        
        date_mapping = {}
        
        for _, row in date_df.iterrows():
            # Check if exists
            date_record = self.db.execute(
                select(DimDate).where(DimDate.date == row['date'])
            ).scalar_one_or_none()
            
            if not date_record:
                date_record = DimDate(**row.to_dict())
                self.db.add(date_record)
                self.db.commit()
                self.db.refresh(date_record)
                logger.debug(f"Created date: {row['date']}")
            
            date_mapping[row['date']] = date_record.date_id
        
        logger.info(f"Loaded {len(date_mapping)} dates")
        return date_mapping

    def load_exchanges(self, exchange_df: pd.DataFrame) -> Dict[str, int]:
        """
        Load exchange dimension data.

        Args:
            exchange_df: DataFrame with exchange data

        Returns:
            Dictionary mapping exchange_code to exchange_id
        """
        if exchange_df.empty:
            logger.info("No exchanges to load")
            return {}
        
        logger.info(f"Loading {len(exchange_df)} exchanges")
        
        exchange_mapping = {}
        
        for _, row in exchange_df.iterrows():
            # Check if exists
            exchange = self.db.execute(
                select(DimExchange).where(DimExchange.exchange_code == row['exchange_code'])
            ).scalar_one_or_none()
            
            if not exchange:
                exchange = DimExchange(
                    exchange_code=row['exchange_code'],
                    exchange_name=row.get('exchange_name', row['exchange_code']),
                    country=row.get('country'),
                    timezone=row.get('timezone', 'UTC'),
                    currency=row.get('currency')
                )
                self.db.add(exchange)
                self.db.commit()
                self.db.refresh(exchange)
                logger.debug(f"Created exchange: {row['exchange_code']}")
            
            exchange_mapping[row['exchange_code']] = exchange.exchange_id
        
        logger.info(f"Loaded {len(exchange_mapping)} exchanges")
        return exchange_mapping

    def load_stock_prices(self, price_df: pd.DataFrame, batch_size: int = 1000) -> int:
        """
        Load stock price fact data.

        Args:
            price_df: DataFrame with stock price data
            batch_size: Number of records to insert per batch

        Returns:
            Number of records loaded
        """
        logger.info(f"Loading {len(price_df)} stock price records")
        
        records_loaded = 0
        
        # Process in batches
        for i in range(0, len(price_df), batch_size):
            batch = price_df.iloc[i:i+batch_size]
            
            for _, row in batch.iterrows():
                # Check if exists (to avoid duplicates)
                existing = self.db.execute(
                    select(FactStockPrice).where(
                        FactStockPrice.company_id == row['company_id'],
                        FactStockPrice.date_id == row['date_id'],
                        FactStockPrice.source_id == row['source_id']
                    )
                ).scalar_one_or_none()
                
                if existing:
                    # Update existing record
                    for col in price_df.columns:
                        if col not in ['company_id', 'date_id', 'source_id'] and col in row:
                            setattr(existing, col, row[col])
                    logger.debug(f"Updated stock price record")
                else:
                    # Insert new record
                    price_record = FactStockPrice(**row.to_dict())
                    self.db.add(price_record)
                    records_loaded += 1
            
            self.db.commit()
            logger.debug(f"Committed batch {i//batch_size + 1}")
        
        logger.info(f"Loaded {records_loaded} new stock price records")
        return records_loaded
