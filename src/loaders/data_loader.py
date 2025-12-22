"""Load transformed data into the database."""
import pandas as pd
from sqlalchemy.orm import Session
from sqlalchemy import select
from typing import Dict, List
from loguru import logger

from src.models import (
    DimCompany, DimDate, DimExchange, DimDataSource,
    FactStockPrice, FactCompanyMetrics,
    DimCryptoAsset, FactCryptoPrice,
    DimIssuer, DimBond, FactBondPrice,
    DimEconomicIndicator, FactEconomicIndicator
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

    def load_crypto_assets(self, crypto_df: pd.DataFrame) -> Dict[str, int]:
        """
        Load cryptocurrency asset dimension data.

        Args:
            crypto_df: DataFrame with crypto asset data

        Returns:
            Dictionary mapping symbol to crypto_id
        """
        logger.info(f"Loading {len(crypto_df)} crypto assets")
        
        crypto_mapping = {}
        
        for _, row in crypto_df.iterrows():
            # Check if exists
            crypto = self.db.execute(
                select(DimCryptoAsset).where(DimCryptoAsset.symbol == row['symbol'])
            ).scalar_one_or_none()
            
            if crypto:
                # Update existing
                crypto.name = row.get('name', crypto.name)
                crypto.chain = row.get('chain', crypto.chain)
                crypto.description = row.get('description', crypto.description)
                logger.debug(f"Updated crypto asset: {row['symbol']}")
            else:
                # Create new
                crypto = DimCryptoAsset(
                    symbol=row['symbol'],
                    name=row.get('name', row['symbol']),
                    chain=row.get('chain'),
                    description=row.get('description'),
                    country=row.get('country')
                )
                self.db.add(crypto)
                logger.debug(f"Created crypto asset: {row['symbol']}")
            
            self.db.commit()
            self.db.refresh(crypto)
            crypto_mapping[row['symbol']] = crypto.crypto_id
        
        logger.info(f"Loaded {len(crypto_mapping)} crypto assets")
        return crypto_mapping

    def load_crypto_prices(self, price_df: pd.DataFrame, batch_size: int = 1000) -> int:
        """
        Load cryptocurrency price fact data.

        Args:
            price_df: DataFrame with crypto price data
            batch_size: Number of records to insert per batch

        Returns:
            Number of records loaded
        """
        logger.info(f"Loading {len(price_df)} crypto price records")
        
        records_loaded = 0
        
        for i in range(0, len(price_df), batch_size):
            batch = price_df.iloc[i:i+batch_size]
            
            for _, row in batch.iterrows():
                existing = self.db.execute(
                    select(FactCryptoPrice).where(
                        FactCryptoPrice.crypto_id == row['crypto_id'],
                        FactCryptoPrice.date_id == row['date_id'],
                        FactCryptoPrice.source_id == row['source_id']
                    )
                ).scalar_one_or_none()
                
                if existing:
                    for col in price_df.columns:
                        if col not in ['crypto_id', 'date_id', 'source_id'] and col in row:
                            setattr(existing, col, row[col])
                    logger.debug(f"Updated crypto price record")
                else:
                    price_record = FactCryptoPrice(**row.to_dict())
                    self.db.add(price_record)
                    records_loaded += 1
            
            self.db.commit()
            logger.debug(f"Committed batch {i//batch_size + 1}")
        
        logger.info(f"Loaded {records_loaded} new crypto price records")
        return records_loaded

    def load_issuer(self, issuer_df: pd.DataFrame) -> Dict[str, int]:
        """
        Load bond issuer dimension data.

        Args:
            issuer_df: DataFrame with issuer data

        Returns:
            Dictionary mapping issuer_name to issuer_id
        """
        logger.info(f"Loading {len(issuer_df)} issuers")
        
        issuer_mapping = {}
        
        for _, row in issuer_df.iterrows():
            issuer = self.db.execute(
                select(DimIssuer).where(DimIssuer.issuer_name == row['issuer_name'])
            ).scalar_one_or_none()
            
            if issuer:
                issuer.issuer_type = row.get('issuer_type', issuer.issuer_type)
                issuer.country = row.get('country', issuer.country)
                issuer.credit_rating = row.get('credit_rating', issuer.credit_rating)
                issuer.sector = row.get('sector', issuer.sector)
                logger.debug(f"Updated issuer: {row['issuer_name']}")
            else:
                issuer = DimIssuer(
                    issuer_name=row['issuer_name'],
                    issuer_type=row.get('issuer_type', 'Unknown'),
                    country=row.get('country'),
                    credit_rating=row.get('credit_rating'),
                    sector=row.get('sector')
                )
                self.db.add(issuer)
                logger.debug(f"Created issuer: {row['issuer_name']}")
            
            self.db.commit()
            self.db.refresh(issuer)
            issuer_mapping[row['issuer_name']] = issuer.issuer_id
        
        logger.info(f"Loaded {len(issuer_mapping)} issuers")
        return issuer_mapping

    def load_bonds(self, bond_df: pd.DataFrame) -> Dict[str, int]:
        """
        Load bond dimension data.

        Args:
            bond_df: DataFrame with bond data

        Returns:
            Dictionary mapping ISIN to bond_id
        """
        logger.info(f"Loading {len(bond_df)} bonds")
        
        bond_mapping = {}
        
        for _, row in bond_df.iterrows():
            bond = self.db.execute(
                select(DimBond).where(DimBond.isin == row['isin'])
            ).scalar_one_or_none()
            
            if bond:
                bond.bond_type = row.get('bond_type', bond.bond_type)
                bond.maturity_date = row.get('maturity_date', bond.maturity_date)
                bond.coupon_rate = row.get('coupon_rate', bond.coupon_rate)
                logger.debug(f"Updated bond: {row['isin']}")
            else:
                bond = DimBond(
                    isin=row['isin'],
                    issuer_id=row['issuer_id'],
                    bond_type=row.get('bond_type'),
                    maturity_date=row.get('maturity_date'),
                    coupon_rate=row.get('coupon_rate'),
                    currency=row.get('currency', 'USD'),
                    country=row.get('country'),
                    description=row.get('description')
                )
                self.db.add(bond)
                logger.debug(f"Created bond: {row['isin']}")
            
            self.db.commit()
            self.db.refresh(bond)
            bond_mapping[row['isin']] = bond.bond_id
        
        logger.info(f"Loaded {len(bond_mapping)} bonds")
        return bond_mapping

    def load_bond_prices(self, price_df: pd.DataFrame, batch_size: int = 1000) -> int:
        """
        Load bond price fact data.

        Args:
            price_df: DataFrame with bond price data
            batch_size: Number of records to insert per batch

        Returns:
            Number of records loaded
        """
        logger.info(f"Loading {len(price_df)} bond price records")
        
        records_loaded = 0
        
        for i in range(0, len(price_df), batch_size):
            batch = price_df.iloc[i:i+batch_size]
            
            for _, row in batch.iterrows():
                existing = self.db.execute(
                    select(FactBondPrice).where(
                        FactBondPrice.bond_id == row['bond_id'],
                        FactBondPrice.date_id == row['date_id'],
                        FactBondPrice.source_id == row['source_id']
                    )
                ).scalar_one_or_none()
                
                if existing:
                    for col in price_df.columns:
                        if col not in ['bond_id', 'date_id', 'source_id'] and col in row:
                            setattr(existing, col, row[col])
                    logger.debug(f"Updated bond price record")
                else:
                    price_record = FactBondPrice(**row.to_dict())
                    self.db.add(price_record)
                    records_loaded += 1
            
            self.db.commit()
            logger.debug(f"Committed batch {i//batch_size + 1}")
        
        logger.info(f"Loaded {records_loaded} new bond price records")
        return records_loaded

    def load_economic_indicators(self, indicator_df: pd.DataFrame) -> Dict[str, int]:
        """
        Load economic indicator dimension data.

        Args:
            indicator_df: DataFrame with economic indicator metadata

        Returns:
            Dictionary mapping indicator_code to indicator_id
        """
        logger.info(f"Loading {len(indicator_df)} economic indicators")
        
        indicator_mapping = {}
        
        for _, row in indicator_df.iterrows():
            indicator = self.db.execute(
                select(DimEconomicIndicator).where(
                    DimEconomicIndicator.indicator_code == row['indicator_code']
                )
            ).scalar_one_or_none()
            
            if indicator:
                # Update existing
                indicator.indicator_name = row.get('indicator_name', indicator.indicator_name)
                indicator.category = row.get('category', indicator.category)
                indicator.unit = row.get('unit', indicator.unit)
                indicator.frequency = row.get('frequency', indicator.frequency)
                logger.debug(f"Updated indicator: {row['indicator_code']}")
            else:
                # Create new
                indicator = DimEconomicIndicator(
                    indicator_code=row['indicator_code'],
                    indicator_name=row.get('indicator_name', row['indicator_code']),
                    category=row.get('category', 'General'),
                    unit=row.get('unit', 'Number'),
                    frequency=row.get('frequency', 'Unknown'),
                    source=row.get('source', 'FRED')
                )
                self.db.add(indicator)
                logger.debug(f"Created indicator: {row['indicator_code']}")
            
            self.db.commit()
            self.db.refresh(indicator)
            indicator_mapping[row['indicator_code']] = indicator.indicator_id
        
        logger.info(f"Loaded {len(indicator_mapping)} economic indicators")
        return indicator_mapping

    def load_economic_data(self, data_df: pd.DataFrame, batch_size: int = 1000) -> int:
        """
        Load economic indicator fact data.

        Args:
            data_df: DataFrame with economic indicator values
            batch_size: Number of records to insert per batch

        Returns:
            Number of records loaded
        """
        logger.info(f"Loading {len(data_df)} economic data records")
        
        records_loaded = 0
        
        for i in range(0, len(data_df), batch_size):
            batch = data_df.iloc[i:i+batch_size]
            
            for _, row in batch.iterrows():
                existing = self.db.execute(
                    select(FactEconomicIndicator).where(
                        FactEconomicIndicator.indicator_id == row['indicator_id'],
                        FactEconomicIndicator.date_id == row['date_id'],
                        FactEconomicIndicator.source_id == row['source_id']
                    )
                ).scalar_one_or_none()
                
                if existing:
                    # Update existing record
                    existing.value = row.get('value', existing.value)
                    logger.debug(f"Updated economic data record")
                else:
                    # Insert new record
                    data_record = FactEconomicIndicator(**row.to_dict())
                    self.db.add(data_record)
                    records_loaded += 1
            
            self.db.commit()
            logger.debug(f"Committed batch {i//batch_size + 1}")
        
        logger.info(f"Loaded {records_loaded} new economic data records")
        return records_loaded
