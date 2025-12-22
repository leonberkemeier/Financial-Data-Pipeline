"""Fact tables for the star schema."""
from sqlalchemy import Column, Integer, Numeric, BigInteger, DateTime, ForeignKey, UniqueConstraint, String, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from .base import Base


class FactStockPrice(Base):
    """Stock price fact table - center of the star schema."""
    __tablename__ = "fact_stock_price"

    # Primary key
    price_id = Column(Integer, primary_key=True, autoincrement=True)

    # Foreign keys to dimension tables
    company_id = Column(Integer, ForeignKey("dim_company.company_id"), nullable=False, index=True)
    date_id = Column(Integer, ForeignKey("dim_date.date_id"), nullable=False, index=True)
    exchange_id = Column(Integer, ForeignKey("dim_exchange.exchange_id"), nullable=True, index=True)
    source_id = Column(Integer, ForeignKey("dim_data_source.source_id"), nullable=False, index=True)

    # Metrics - the actual measurements
    open_price = Column(Numeric(18, 4))
    high_price = Column(Numeric(18, 4))
    low_price = Column(Numeric(18, 4))
    close_price = Column(Numeric(18, 4), nullable=False)
    adjusted_close = Column(Numeric(18, 4))
    volume = Column(BigInteger)

    # Derived metrics
    price_change = Column(Numeric(18, 4))  # close - open
    price_change_percent = Column(Numeric(8, 4))  # (close - open) / open * 100
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships (optional, for easier querying)
    company = relationship("DimCompany")
    date = relationship("DimDate")
    exchange = relationship("DimExchange")
    source = relationship("DimDataSource")

    # Ensure uniqueness: one price record per company per date per source
    __table_args__ = (
        UniqueConstraint('company_id', 'date_id', 'source_id', name='uix_company_date_source'),
        {"sqlite_autoincrement": True},
    )

    def __repr__(self):
        return f"<FactStockPrice(company_id={self.company_id}, date_id={self.date_id}, close={self.close_price})>"


class FactCompanyMetrics(Base):
    """Company fundamental metrics fact table."""
    __tablename__ = "fact_company_metrics"

    metric_id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Foreign keys
    company_id = Column(Integer, ForeignKey("dim_company.company_id"), nullable=False, index=True)
    date_id = Column(Integer, ForeignKey("dim_date.date_id"), nullable=False, index=True)
    source_id = Column(Integer, ForeignKey("dim_data_source.source_id"), nullable=False, index=True)

    # Financial metrics
    market_cap = Column(BigInteger)
    pe_ratio = Column(Numeric(10, 2))
    earnings_per_share = Column(Numeric(10, 4))
    dividend_yield = Column(Numeric(6, 4))
    beta = Column(Numeric(6, 4))
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    company = relationship("DimCompany")
    date = relationship("DimDate")
    source = relationship("DimDataSource")

    __table_args__ = (
        UniqueConstraint('company_id', 'date_id', 'source_id', name='uix_metrics_company_date_source'),
        {"sqlite_autoincrement": True},
    )

    def __repr__(self):
        return f"<FactCompanyMetrics(company_id={self.company_id}, date_id={self.date_id})>"


class FactSECFiling(Base):
    """SEC filing fact table."""
    __tablename__ = "fact_sec_filing"

    filing_id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Foreign keys
    company_id = Column(Integer, ForeignKey("dim_company.company_id"), nullable=False, index=True)
    filing_type_id = Column(Integer, ForeignKey("dim_filing_type.filing_type_id"), nullable=False, index=True)
    date_id = Column(Integer, ForeignKey("dim_date.date_id"), nullable=False, index=True)
    source_id = Column(Integer, ForeignKey("dim_data_source.source_id"), nullable=False, index=True)
    
    # Filing metadata
    cik = Column(String(10), nullable=False, index=True)
    accession_number = Column(String(20), unique=True, nullable=False, index=True)
    file_number = Column(String(20))
    accepted_date = Column(DateTime(timezone=True))
    filing_url = Column(String(500))
    
    # Filing content (can be stored as text or reference to file storage)
    filing_text = Column(Text)  # Store extracted text (or NULL for large filings)
    filing_size = Column(Integer)  # Size in bytes
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    company = relationship("DimCompany")
    filing_type = relationship("DimFilingType")
    date = relationship("DimDate")
    source = relationship("DimDataSource")
    
    __table_args__ = (
        UniqueConstraint('company_id', 'filing_type_id', 'date_id', name='uix_filing_company_type_date'),
        {"sqlite_autoincrement": True},
    )

    def __repr__(self):
        return f"<FactSECFiling(company_id={self.company_id}, accession={self.accession_number})>"


class FactFilingAnalysis(Base):
    """Filing analysis results fact table."""
    __tablename__ = "fact_filing_analysis"

    analysis_id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Foreign keys
    filing_id = Column(Integer, ForeignKey("fact_sec_filing.filing_id"), nullable=False, index=True, unique=True)
    company_id = Column(Integer, ForeignKey("dim_company.company_id"), nullable=False, index=True)
    date_id = Column(Integer, ForeignKey("dim_date.date_id"), nullable=False, index=True)
    
    # Section statistics
    sections_found = Column(Integer)  # Number of sections extracted
    business_word_count = Column(Integer)
    risk_factors_word_count = Column(Integer)
    mda_word_count = Column(Integer)
    financials_word_count = Column(Integer)
    
    # Financial mentions extracted (as JSON text)
    revenue_mentions = Column(Text)  # JSON array of revenue mentions
    net_income_mentions = Column(Text)  # JSON array
    earnings_mentions = Column(Text)  # JSON array
    cash_mentions = Column(Text)  # JSON array
    debt_mentions = Column(Text)  # JSON array
    
    # Risk analysis
    risk_keywords = Column(Text)  # JSON array of {'keyword': 'X', 'count': N}
    
    # Overall metrics
    total_word_count = Column(Integer)
    total_char_count = Column(Integer)
    financial_mentions_count = Column(Integer)  # Total mentions found
    
    # Metadata
    analyzed_at = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    filing = relationship("FactSECFiling")
    company = relationship("DimCompany")
    date = relationship("DimDate")
    
    __table_args__ = (
        {"sqlite_autoincrement": True},
    )

    def __repr__(self):
        return f"<FactFilingAnalysis(filing_id={self.filing_id}, sections={self.sections_found})>"


class FactCryptoPrice(Base):
    """Cryptocurrency price fact table - crypto center of star schema."""
    __tablename__ = "fact_crypto_price"

    # Primary key
    crypto_price_id = Column(Integer, primary_key=True, autoincrement=True)

    # Foreign keys to dimension tables
    crypto_id = Column(Integer, ForeignKey("dim_crypto_asset.crypto_id"), nullable=False, index=True)
    date_id = Column(Integer, ForeignKey("dim_date.date_id"), nullable=False, index=True)
    source_id = Column(Integer, ForeignKey("dim_data_source.source_id"), nullable=False, index=True)

    # Metrics
    price = Column(Numeric(18, 8), nullable=False)  # Current price in USD
    market_cap = Column(BigInteger)  # Total market cap in USD
    trading_volume = Column(BigInteger)  # 24h trading volume
    circulating_supply = Column(Numeric(20, 8))  # Number of coins in circulation
    total_supply = Column(Numeric(20, 8))  # Total coins that exist
    price_change_24h = Column(Numeric(8, 4))  # Price change % in 24h
    price_change_7d = Column(Numeric(8, 4))  # Price change % in 7d
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    crypto = relationship("DimCryptoAsset")
    date = relationship("DimDate")
    source = relationship("DimDataSource")

    # Ensure uniqueness: one price record per crypto per date per source
    __table_args__ = (
        UniqueConstraint('crypto_id', 'date_id', 'source_id', name='uix_crypto_date_source'),
        {"sqlite_autoincrement": True},
    )

    def __repr__(self):
        return f"<FactCryptoPrice(crypto_id={self.crypto_id}, date_id={self.date_id}, price={self.price})>"


class FactBondPrice(Base):
    """Bond price and yield fact table."""
    __tablename__ = "fact_bond_price"

    # Primary key
    bond_price_id = Column(Integer, primary_key=True, autoincrement=True)

    # Foreign keys
    bond_id = Column(Integer, ForeignKey("dim_bond.bond_id"), nullable=False, index=True)
    date_id = Column(Integer, ForeignKey("dim_date.date_id"), nullable=False, index=True)
    source_id = Column(Integer, ForeignKey("dim_data_source.source_id"), nullable=False, index=True)

    # Metrics
    price = Column(Numeric(8, 4), nullable=False)  # Bond price (as % of par)
    yield_percent = Column(Numeric(8, 4), nullable=False)  # Yield to maturity
    spread = Column(Numeric(8, 4))  # Spread over benchmark (in basis points)
    duration = Column(Numeric(6, 2))  # Modified duration in years
    convexity = Column(Numeric(8, 4))  # Convexity measure
    bid_ask_spread = Column(Numeric(6, 4))  # Bid-ask spread
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    bond = relationship("DimBond")
    date = relationship("DimDate")
    source = relationship("DimDataSource")

    __table_args__ = (
        UniqueConstraint('bond_id', 'date_id', 'source_id', name='uix_bond_date_source'),
        {"sqlite_autoincrement": True},
    )

    def __repr__(self):
        return f"<FactBondPrice(bond_id={self.bond_id}, date_id={self.date_id}, yield={self.yield_percent})>"


class FactEconomicIndicator(Base):
    """Economic indicator fact table."""
    __tablename__ = "fact_economic_indicator"

    # Primary key
    economic_data_id = Column(Integer, primary_key=True, autoincrement=True)

    # Foreign keys
    indicator_id = Column(Integer, ForeignKey("dim_economic_indicator.indicator_id"), nullable=False, index=True)
    date_id = Column(Integer, ForeignKey("dim_date.date_id"), nullable=False, index=True)
    source_id = Column(Integer, ForeignKey("dim_data_source.source_id"), nullable=False, index=True)

    # Metrics
    value = Column(Numeric(18, 4), nullable=False)  # The actual indicator value
    
    # Derived metrics (optional)
    change_from_previous = Column(Numeric(18, 4))  # Change from previous period
    change_percent = Column(Numeric(8, 4))  # Percentage change from previous
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    indicator = relationship("DimEconomicIndicator")
    date = relationship("DimDate")
    source = relationship("DimDataSource")

    # Ensure uniqueness: one value per indicator per date per source
    __table_args__ = (
        UniqueConstraint('indicator_id', 'date_id', 'source_id', name='uix_indicator_date_source'),
        {"sqlite_autoincrement": True},
    )

    def __repr__(self):
        return f"<FactEconomicIndicator(indicator_id={self.indicator_id}, date_id={self.date_id}, value={self.value})>"
