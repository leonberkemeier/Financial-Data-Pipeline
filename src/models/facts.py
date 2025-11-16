"""Fact tables for the star schema."""
from sqlalchemy import Column, Integer, Numeric, BigInteger, DateTime, ForeignKey, UniqueConstraint
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
    filing_text = Column(String)  # Store extracted text (or NULL for large filings)
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
