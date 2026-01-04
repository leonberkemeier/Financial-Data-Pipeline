"""Populate dim_exchange table and link companies to exchanges."""
from sqlalchemy import create_engine, text
from src.models.base import init_db, SessionLocal
from src.models.dimensions import DimExchange, DimCompany
from config.config import DATABASE_URL
from loguru import logger

# Configure logger
logger.remove()
logger.add(lambda msg: print(msg, end=''))
logger.add("logs/populate_exchanges.log", level="INFO")

# Major exchanges by country/region
EXCHANGES = {
    # US Exchanges
    "NYSE": {
        "name": "New York Stock Exchange",
        "country": "USA",
        "timezone": "US/Eastern",
        "currency": "USD"
    },
    "NASDAQ": {
        "name": "NASDAQ Stock Market",
        "country": "USA",
        "timezone": "US/Eastern",
        "currency": "USD"
    },
    # European Exchanges
    "LSE": {
        "name": "London Stock Exchange",
        "country": "UK",
        "timezone": "Europe/London",
        "currency": "GBP"
    },
    "EURONEXT": {
        "name": "Euronext",
        "country": "Europe",
        "timezone": "Europe/Paris",
        "currency": "EUR"
    },
    "XETRA": {
        "name": "XETRA (Deutsche Börse)",
        "country": "Germany",
        "timezone": "Europe/Berlin",
        "currency": "EUR"
    },
    "SIX": {
        "name": "SIX Swiss Exchange",
        "country": "Switzerland",
        "timezone": "Europe/Zurich",
        "currency": "CHF"
    },
}

# Mapping of tickers to exchanges
TICKER_EXCHANGE_MAP = {
    # US Tech (NYSE/NASDAQ)
    "AAPL": "NASDAQ", "MSFT": "NASDAQ", "GOOGL": "NASDAQ", "AMZN": "NASDAQ", "NVDA": "NASDAQ",
    "META": "NASDAQ", "TSLA": "NASDAQ", "NFLX": "NASDAQ", "ADBE": "NASDAQ", "CRM": "NASDAQ",
    "CSCO": "NASDAQ", "INTC": "NASDAQ", "AVGO": "NASDAQ", "QCOM": "NASDAQ", "AMD": "NASDAQ",
    "MU": "NASDAQ", "ASML": "NASDAQ", "LRCX": "NASDAQ", "CDNS": "NASDAQ", "SNPS": "NASDAQ",
    "AMAT": "NASDAQ", "PYPL": "NASDAQ", "SQ": "NYSE", "RBLX": "NYSE", "CRWD": "NASDAQ",
    
    # US Finance (NYSE/NASDAQ)
    "JPM": "NYSE", "BAC": "NYSE", "WFC": "NYSE", "GS": "NYSE", "MS": "NYSE",
    "BLK": "NYSE", "ICE": "NYSE", "SPGI": "NYSE", "SCHW": "NASDAQ", "TD": "NYSE",
    "BNY": "NYSE", "USB": "NYSE", "PNC": "NYSE", "CME": "NASDAQ", "CBOE": "NASDAQ",
    "COIN": "NASDAQ", "HOOD": "NASDAQ", "IBKR": "NASDAQ", "SYF": "NYSE", "DFS": "NYSE",
    "AXP": "NYSE", "V": "NYSE", "MA": "NYSE", "AMP": "NYSE", "MSTR": "NASDAQ",
    
    # US Chemicals/Materials
    "DD": "NYSE", "DOW": "NYSE", "LYB": "NYSE", "APD": "NYSE", "SHW": "NYSE",
    "ECL": "NYSE", "FMC": "NYSE", "ALB": "NYSE", "PPG": "NYSE", "EMN": "NYSE",
    "MLM": "NYSE", "NEM": "NYSE", "SCCO": "NYSE", "FCX": "NYSE", "ARCH": "NYSE",
    "BTU": "NYSE", "NRG": "NYSE", "AEE": "NYSE", "AES": "NYSE", "CMS": "NYSE",
    "EXC": "NYSE", "NEE": "NYSE", "DUK": "NYSE", "SO": "NYSE", "OKE": "NYSE",
    
    # US Commodities/Energy
    "XOM": "NYSE", "CVX": "NYSE", "COP": "NYSE", "EOG": "NYSE", "MPC": "NYSE",
    "PSX": "NYSE", "VLO": "NYSE", "HES": "NYSE", "OXY": "NYSE", "SLB": "NYSE",
    "HAL": "NYSE", "RIG": "NYSE", "FANG": "NYSE", "PXD": "NYSE", "EQT": "NYSE",
    "MRO": "NYSE", "WMB": "NYSE", "TRGP": "NYSE", "EPD": "NYSE", "KMI": "NYSE",
    "GLD": "NYSE", "USO": "NYSE", "DBC": "NASDAQ", "PDBC": "NYSE", "CORN": "NASDAQ",
    
    # US Crypto-related
    "IBIT": "NYSE", "FBTC": "NYSE", "ETHE": "NYSE", "MARA": "NASDAQ", "CLSK": "NASDAQ",
    "RIOT": "NASDAQ", "MSTR": "NASDAQ", "COIN": "NASDAQ", "GBTC": "NYSE",
    "UPST": "NASDAQ", "SQ": "NYSE", "PYPL": "NASDAQ", "SOFI": "NASDAQ", "LMND": "NYSE",
    "HOOD": "NASDAQ", "UBER": "NYSE", "LYFT": "NASDAQ", "U": "NASDAQ", "DDOG": "NASDAQ",
    "NET": "NYSE", "CRWD": "NASDAQ",
    
    # European stocks (LSE, Euronext, XETRA)
    "SAP": "XETRA", "NOKIA": "EURONEXT", "RMS.L": "LSE", "EOAN": "XETRA",
    "ENXTPA.PA": "EURONEXT", "OR.PA": "EURONEXT", "CASS": "LSE", "CRDA": "LSE",
    "FLDO": "LSE", "JYAFF": "LSE",
    
    # European Finance
    "HSBA": "LSE", "LLOY": "LSE", "BARC": "LSE", "STAN": "LSE", "NWG": "LSE",
    "BNP.PA": "EURONEXT", "SAN.PA": "EURONEXT", "CA.PA": "EURONEXT", "CS": "SIX",
    "UBS": "SIX", "DB1": "XETRA", "CBK": "XETRA", "DAX": "XETRA",
    
    # European Chemicals/Materials
    "BASF": "XETRA", "BAYER": "XETRA", "SXRT.L": "LSE", "RELX.L": "LSE", "ULVR.L": "LSE",
    "SAF.PA": "EURONEXT", "ORLY.PA": "EURONEXT", "VIE.PA": "EURONEXT", "NOKIA.HE": "EURONEXT",
    "LIN": "XETRA", "VOD.L": "LSE", "RDSA.L": "LSE",
    
    # European Commodities/Energy
    "SHELL.L": "LSE", "BP.L": "LSE", "TTE.PA": "EURONEXT", "ENQ.PA": "EURONEXT",
}

def populate_exchanges():
    """Populate dim_exchange table."""
    logger.info("=" * 80)
    logger.info("POPULATING EXCHANGES")
    logger.info("=" * 80)
    
    db = SessionLocal()
    
    try:
        # Add exchanges
        for exchange_code, exchange_info in EXCHANGES.items():
            existing = db.query(DimExchange).filter_by(exchange_code=exchange_code).first()
            
            if not existing:
                exchange = DimExchange(
                    exchange_code=exchange_code,
                    exchange_name=exchange_info["name"],
                    country=exchange_info["country"],
                    timezone=exchange_info["timezone"],
                    currency=exchange_info["currency"]
                )
                db.add(exchange)
                logger.info(f"✓ Added exchange: {exchange_code} ({exchange_info['name']})")
            else:
                logger.info(f"~ Exchange already exists: {exchange_code}")
        
        db.commit()
        logger.info(f"\n✓ Populated {len(EXCHANGES)} exchanges")
        
        # Link companies to exchanges
        logger.info("\nLinking companies to exchanges...")
        
        companies = db.query(DimCompany).all()
        linked_count = 0
        
        for company in companies:
            if company.ticker in TICKER_EXCHANGE_MAP:
                exchange_code = TICKER_EXCHANGE_MAP[company.ticker]
                exchange = db.query(DimExchange).filter_by(exchange_code=exchange_code).first()
                
                if exchange:
                    company.exchange_id = exchange.exchange_id
                    linked_count += 1
                    logger.info(f"✓ Linked {company.ticker} to {exchange_code}")
        
        db.commit()
        logger.info(f"\n✓ Linked {linked_count} companies to exchanges")
        
        logger.info("\n" + "=" * 80)
        logger.info("POPULATION COMPLETE")
        logger.info("=" * 80)
        
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    # Initialize database
    init_db()
    
    # Populate exchanges and link companies
    populate_exchanges()
