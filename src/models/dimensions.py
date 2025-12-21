"""Dimension tables for the star schema."""
from sqlalchemy import Column, Integer, String, Date, DateTime, ForeignKey, Numeric
from sqlalchemy.sql import func
from .base import Base


class DimCompany(Base):
    """Company dimension table."""
    __tablename__ = "dim_company"

    company_id = Column(Integer, primary_key=True, autoincrement=True)
    ticker = Column(String(10), unique=True, nullable=False, index=True)
    company_name = Column(String(255))
    sector = Column(String(100))
    industry = Column(String(100))
    country = Column(String(50))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return f"<DimCompany(ticker={self.ticker}, name={self.company_name})>"


class DimDate(Base):
    """Date dimension table."""
    __tablename__ = "dim_date"

    date_id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(Date, unique=True, nullable=False, index=True)
    year = Column(Integer, nullable=False)
    quarter = Column(Integer, nullable=False)
    month = Column(Integer, nullable=False)
    week = Column(Integer, nullable=False)
    day = Column(Integer, nullable=False)
    day_of_week = Column(Integer, nullable=False)  # 0=Monday, 6=Sunday
    day_name = Column(String(10), nullable=False)
    is_weekend = Column(Integer, nullable=False)  # 0=weekday, 1=weekend
    is_quarter_end = Column(Integer, nullable=False)
    is_year_end = Column(Integer, nullable=False)

    def __repr__(self):
        return f"<DimDate(date={self.date})>"


class DimExchange(Base):
    """Exchange dimension table."""
    __tablename__ = "dim_exchange"

    exchange_id = Column(Integer, primary_key=True, autoincrement=True)
    exchange_code = Column(String(10), unique=True, nullable=False, index=True)
    exchange_name = Column(String(100))
    country = Column(String(50))
    timezone = Column(String(50))
    currency = Column(String(3))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<DimExchange(code={self.exchange_code}, name={self.exchange_name})>"


class DimDataSource(Base):
    """Data source dimension table."""
    __tablename__ = "dim_data_source"

    source_id = Column(Integer, primary_key=True, autoincrement=True)
    source_name = Column(String(50), unique=True, nullable=False, index=True)
    source_type = Column(String(50))  # API, Database, File, etc.
    description = Column(String(255))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<DimDataSource(name={self.source_name})>"


class DimFilingType(Base):
    """SEC filing type dimension table."""
    __tablename__ = "dim_filing_type"

    filing_type_id = Column(Integer, primary_key=True, autoincrement=True)
    filing_type = Column(String(20), unique=True, nullable=False, index=True)
    description = Column(String(255))
    category = Column(String(50))  # Annual, Quarterly, Current, etc.
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<DimFilingType(type={self.filing_type})>"


class DimCryptoAsset(Base):
    """Cryptocurrency asset dimension table."""
    __tablename__ = "dim_crypto_asset"

    crypto_id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(20), unique=True, nullable=False, index=True)  # BTC, ETH, etc.
    name = Column(String(255), nullable=False)  # Bitcoin, Ethereum, etc.
    chain = Column(String(100))  # Blockchain (Ethereum, Bitcoin, Polygon, etc.)
    description = Column(String(500))
    country = Column(String(50))  # Country of origin if applicable
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return f"<DimCryptoAsset(symbol={self.symbol}, name={self.name})>"


class DimIssuer(Base):
    """Bond issuer dimension table."""
    __tablename__ = "dim_issuer"

    issuer_id = Column(Integer, primary_key=True, autoincrement=True)
    issuer_name = Column(String(255), nullable=False, unique=True, index=True)
    issuer_type = Column(String(50), nullable=False)  # Government, Corporate, Municipal, etc.
    country = Column(String(50))
    credit_rating = Column(String(20))  # AAA, AA, A, BBB, etc.
    sector = Column(String(100))  # For corporate issuers
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return f"<DimIssuer(name={self.issuer_name}, type={self.issuer_type})>"


class DimBond(Base):
    """Bond dimension table."""
    __tablename__ = "dim_bond"

    bond_id = Column(Integer, primary_key=True, autoincrement=True)
    isin = Column(String(20), unique=True, nullable=False, index=True)  # International Securities ID
    issuer_id = Column(Integer, ForeignKey("dim_issuer.issuer_id"), nullable=False, index=True)
    bond_type = Column(String(50), nullable=False)  # Government, Corporate, Treasury, etc.
    maturity_date = Column(DateTime(timezone=True))  # When bond matures
    coupon_rate = Column(Numeric(6, 4))  # Annual coupon as percentage
    currency = Column(String(3), default='USD')  # Currency of the bond
    country = Column(String(50))  # Issuing country
    description = Column(String(500))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return f"<DimBond(isin={self.isin}, type={self.bond_type})>"
