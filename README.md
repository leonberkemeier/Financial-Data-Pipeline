# Financial Data Aggregator

A production-ready ETL pipeline that aggregates financial data from multiple sources and loads it into a star schema data warehouse.

## 🌟 Features

- **Multi-Asset Support**: Stocks, Crypto, Bonds, Commodities, and Economic Indicators
- **Multi-Source Extraction**: Yahoo Finance, CoinGecko, FRED, Alpha Vantage
- **Star Schema Design**: Dimensional modeling with fact and dimension tables
- **Unified Pipeline**: Single command to run all data sources
- **Configuration-Driven**: YAML config file for easy customization
- **Rate Limiting**: Built-in API throttling to prevent rate limit errors
- **Data Quality Checks**: Built-in validation for data integrity
- **Production Logging**: Comprehensive logging with rotation and error tracking
- **Batch Processing**: Efficient loading with configurable batch sizes

## 📊 Star Schema

### Fact Tables
- `fact_stock_price`: Daily stock prices with OHLCV data
- `fact_crypto_price`: Cryptocurrency prices and market data
- `fact_bond_price`: Treasury yields and bond prices
- `fact_commodity_price`: Commodity futures and spot prices
- `fact_economic_indicator`: Economic indicators time series
- `fact_company_metrics`: Company fundamental metrics
- `fact_sec_filing`: SEC filings data

### Dimension Tables
- `dim_company`: Stock company information
- `dim_crypto_asset`: Cryptocurrency asset information
- `dim_bond`: Bond/treasury information
- `dim_issuer`: Bond issuer information
- `dim_commodity`: Commodity information (oil, gold, etc.)
- `dim_economic_indicator`: Economic indicator metadata
- `dim_date`: Date dimension with calendar attributes
- `dim_exchange`: Exchange information
- `dim_data_source`: Data source metadata

## 🚀 Setup

### 1. Prerequisites
- Python 3.9+
- PostgreSQL database

### 2. Install Dependencies

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configure Environment

Copy `.env.example` to `.env` and configure:

```bash
cp .env.example .env
```

Edit `.env`:
```env
# Database Configuration
DATABASE_URL=sqlite:///financial_data.db

# API Keys
FRED_API_KEY=your_fred_api_key_here
ALPHA_VANTAGE_API_KEY=your_api_key_here  # Optional

# Pipeline Configuration
LOG_LEVEL=INFO
BATCH_SIZE=100
```

**Get API Keys:**
- FRED API Key (free): https://fred.stlouisfed.org/
- Alpha Vantage (optional): https://www.alphavantage.co/

### 4. Setup Database

The pipeline uses SQLite by default (no setup needed). Tables are created automatically on first run.

To use PostgreSQL instead, update `DATABASE_URL` in `.env`:
```env
DATABASE_URL=postgresql://user:password@localhost:5432/financial_data
```

## 💻 Usage

### Unified Pipeline (Recommended)

**Run all data sources at once:**
```bash
python unified_pipeline.py --all
```

**Run specific sources:**
```bash
# Just crypto and bonds
python unified_pipeline.py --crypto --bonds

# Just commodities
python unified_pipeline.py --commodities

# Just economic indicators
python unified_pipeline.py --economic

# Commodities and crypto
python unified_pipeline.py --commodities --crypto
```

**Configuration:**
Edit `config/pipeline_config.yaml` to customize:
- Which sources to enable
- Tickers/symbols to track
- Date ranges and periods
- API rate limits

### Individual Pipelines

**Stocks:**
```bash
python pipeline.py --tickers AAPL MSFT GOOGL --period 30d
```

**Crypto:**
```bash
python crypto_etl_pipeline.py --symbols BTC ETH ADA --days 30
```

**Bonds:**
```bash
python bond_etl_pipeline.py --periods 3MO 10Y 30Y --source yahoo --days 30
```

**Economic Indicators:**
```bash
python economic_etl_pipeline.py --indicators GDP UNRATE CPIAUCSL --days 365
```

**Commodities:**
```bash
# Yahoo Finance (futures)
python commodity_etl_pipeline.py --symbols CL=F GC=F SI=F --source yahoo --days 30

# FRED (spot prices)
python commodity_etl_pipeline.py --source fred --days 90

# Both sources
python commodity_etl_pipeline.py --source both --days 30
```

### Query Your Data

**View crypto data:**
```bash
python query_crypto.py overview
python query_crypto.py timeseries BTC 30
python query_crypto.py compare BTC ETH ADA
```

### Test All Data Sources

**Quick test to verify all extractors:**
```bash
python test_all_sources.py
```

### View Data with Web Dashboard

After running the pipeline, launch the interactive dashboard:

```bash
./run_dashboard.sh
```

Open your browser to **http://localhost:5000** to:
- View market overview and statistics
- Explore individual stock details with interactive charts
- Compare multiple stocks side-by-side
- Access data via REST API endpoints

See `dashboard/README.md` for more details.

## 📊 Available Data Sources

### Cryptocurrency (CoinGecko)
**Symbols:** BTC, ETH, ADA, BNB, SOL, DOT, MATIC, AVAX, LINK, UNI, and more
**Data:** Price, market cap, volume, 24h change
**Rate Limit:** 1.5s delay (configurable)

### Bonds (FRED & Yahoo Finance)
**Periods:** 3MO, 2Y, 5Y, 10Y, 30Y
**Data:** Treasury yields and bond prices
**Sources:** 
- FRED: Official Federal Reserve data
- Yahoo Finance: Real-time bond prices (tickers: ^IRX, ^FVX, ^TNX, ^TYX)

### Economic Indicators (FRED)
**15 indicators across 8 categories:**
- **GDP & Growth:** GDP, GDPC1
- **Inflation:** CPIAUCSL, CPILFESL, PCEPI
- **Employment:** UNRATE, PAYEMS, CIVPART
- **Interest Rates:** FEDFUNDS, DFF
- **Consumer & Housing:** UMCSENT, HOUST, RSXFS
- **Money Supply:** M1SL, M2SL

### Stocks (Yahoo Finance & Alpha Vantage)
**Tickers:** Any US stock (AAPL, MSFT, GOOGL, etc.)
**Data:** OHLCV, company info, fundamentals

### Commodities (Yahoo Finance & FRED)
**17 commodities across 3 categories:**
- **Energy:** WTI Crude Oil (CL=F), Brent Crude (BZ=F), Natural Gas (NG=F), Gasoline (RB=F), Heating Oil (HO=F)
- **Metals:** Gold (GC=F), Silver (SI=F), Platinum (PL=F), Palladium (PA=F), Copper (HG=F)
- **Agriculture:** Corn (ZC=F), Soybeans (ZS=F), Wheat (ZW=F), Coffee (KC=F), Sugar (SB=F), Cocoa (CC=F), Cotton (CT=F)

**Data:** OHLCV for futures (Yahoo), spot prices (FRED)
**Sources:**
- Yahoo Finance: Real-time futures contracts
- FRED: Official spot/reference prices (DCOILWTICO, GOLDAMGBD228NLBM, etc.)

## 📁 Project Structure

```
financial_data_aggregator/
├── config/
│   ├── config.py              # Configuration management
│   └── pipeline_config.yaml   # Unified pipeline config
├── src/
│   ├── extractors/
│   │   ├── yahoo_finance.py   # Yahoo Finance (stocks)
│   │   ├── crypto_gecko.py    # CoinGecko (crypto)
│   │   ├── fred_bond.py       # FRED (bonds)
│   │   ├── yahoo_bond.py      # Yahoo Finance (bonds)
│   │   ├── yahoo_commodity.py # Yahoo Finance (commodities)
│   │   ├── fred_commodity.py  # FRED (commodities)
│   │   ├── economic_indicators.py  # FRED (economic data)
│   │   └── alpha_vantage.py   # Alpha Vantage (stocks)
│   ├── transformers/
│   │   └── data_transformer.py # All data transformations
│   ├── loaders/
│   │   └── data_loader.py     # Database loading
│   ├── models/
│   │   ├── base.py            # Database configuration
│   │   ├── dimensions.py      # Dimension table models
│   │   └── facts.py           # Fact table models
│   └── utils/
│       ├── logger.py          # Logging
│       └── validators.py      # Data quality
├── pipeline.py                 # Stock ETL pipeline
├── crypto_etl_pipeline.py      # Crypto ETL pipeline
├── bond_etl_pipeline.py        # Bond ETL pipeline  
├── commodity_etl_pipeline.py   # Commodity ETL pipeline
├── economic_etl_pipeline.py    # Economic ETL pipeline
├── unified_pipeline.py         # Orchestrates all pipelines
├── query_crypto.py             # Query crypto data
├── test_all_sources.py         # Test all extractors
├── test_commodity_sources.py   # Test commodity extractors
└── README.md                   # This file
```

## 🔍 Example Queries

After running the pipeline, query your data:

### Stock Queries
```sql
-- Get latest stock prices
SELECT 
    c.ticker,
    c.company_name,
    d.date,
    f.close_price,
    f.volume
FROM fact_stock_price f
JOIN dim_company c ON f.company_id = c.company_id
JOIN dim_date d ON f.date_id = d.date_id
ORDER BY d.date DESC, c.ticker
LIMIT 10;
```

### Crypto Queries
```sql
-- Compare crypto performance
SELECT 
    ca.symbol,
    ca.name,
    f.current_price,
    f.price_change_24h,
    f.price_change_percentage_24h,
    f.market_cap
FROM fact_crypto_price f
JOIN dim_crypto_asset ca ON f.crypto_asset_id = ca.crypto_asset_id
JOIN dim_date d ON f.date_id = d.date_id
ORDER BY f.market_cap DESC
LIMIT 10;
```

### Bond Queries
```sql
-- Track treasury yields over time
SELECT 
    b.bond_type,
    b.maturity_period,
    d.date,
    f.yield
FROM fact_bond_price f
JOIN dim_bond b ON f.bond_id = b.bond_id
JOIN dim_date d ON f.date_id = d.date_id
WHERE b.maturity_period IN ('10Y', '30Y')
ORDER BY d.date DESC
LIMIT 20;
```

### Economic Indicators
```sql
-- Get latest economic indicators
SELECT 
    ei.indicator_code,
    ei.indicator_name,
    ei.category,
    d.date,
    f.value,
    f.year_over_year_change
FROM fact_economic_indicator f
JOIN dim_economic_indicator ei ON f.indicator_id = ei.indicator_id
JOIN dim_date d ON f.date_id = d.date_id
WHERE d.date = (SELECT MAX(date) FROM dim_date)
ORDER BY ei.category, ei.indicator_code;
```

### Commodity Queries
```sql
-- Track commodity prices by category
SELECT 
    c.category,
    c.symbol,
    c.name,
    d.date,
    f.close_price,
    f.price_change_percent
FROM fact_commodity_price f
JOIN dim_commodity c ON f.commodity_id = c.commodity_id
JOIN dim_date d ON f.date_id = d.date_id
WHERE c.category = 'Energy'
ORDER BY d.date DESC, c.symbol
LIMIT 20;

-- Compare commodity performance
SELECT 
    c.name,
    c.symbol,
    AVG(f.close_price) as avg_price,
    MAX(f.close_price) as high_price,
    MIN(f.close_price) as low_price,
    AVG(f.volume) as avg_volume
FROM fact_commodity_price f
JOIN dim_commodity c ON f.commodity_id = c.commodity_id
GROUP BY c.commodity_id, c.name, c.symbol
ORDER BY avg_price DESC;
```

## 📝 Logging

Logs are stored in the `logs/` directory:
- `pipeline_YYYY-MM-DD.log`: All pipeline activity
- `errors_YYYY-MM-DD.log`: Error logs only

## 🧪 Testing

Run tests with pytest:
```bash
pytest tests/
```

## 🔄 Data Quality Checks

The pipeline includes automatic validation:
- Required column presence
- Null value detection
- Price validation (no negatives, OHLC relationships)
- Duplicate detection
- Volume validation

## 🤝 Contributing

This is a portfolio project demonstrating:
- ETL pipeline design
- Star schema implementation
- Data quality practices
- Production-ready Python code
- Financial data engineering

## 📄 License

MIT License

## SEC Filings ETL and Analysis

- The SEC ETL pipeline (sec_etl_pipeline.py) fetches filing metadata and attempts to extract full filing text for forms 10-K/10-Q/8-K.
- Text extraction depends on SEC document structures; if the primary HTML is not detected, the loader falls back to the complete TXT submission or the index page text.
- Analysis uses regex-based section detection (Business, Risk Factors, MD&A, Financials) and simple keyword extraction.

### Prerequisites
- Network access to sec.gov
- Respect SEC rate limits and provide a valid User-Agent with contact info

### Troubleshooting
- If analysis shows 0 sections or very small word counts:
  - Re-run sec_etl_pipeline with a smaller --count and confirm filing_text is populated (check fact_sec_filing.filing_size > 1000)
  - The extractor now prefers the row whose Type matches 10-K/10-Q; if no HTML is available, it falls back to the TXT submission
- For RAG demo (rag_demo.py), ensure Ollama is reachable and ChromaDB path is writable before running embedding initialization.
