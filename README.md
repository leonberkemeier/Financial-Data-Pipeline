# Financial Data Aggregator

A production-ready ETL pipeline that aggregates financial data from multiple sources (Yahoo Finance, Alpha Vantage) and loads it into a star schema data warehouse.

## 🌟 Features

- **Multi-Source Data Extraction**: Pull data from Yahoo Finance and Alpha Vantage APIs
- **Star Schema Design**: Dimensional modeling with fact and dimension tables
- **Data Quality Checks**: Built-in validation for data integrity
- **Configurable Pipeline**: Easy to customize tickers, date ranges, and sources
- **Production Logging**: Comprehensive logging with rotation and error tracking
- **Batch Processing**: Efficient loading with configurable batch sizes

## 📊 Star Schema

### Fact Tables
- `fact_stock_price`: Daily stock prices with OHLCV data
- `fact_company_metrics`: Company fundamental metrics (PE ratio, market cap, etc.)

### Dimension Tables
- `dim_company`: Company information (ticker, name, sector, industry)
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
DATABASE_URL=postgresql://user:password@localhost:5432/financial_data

# API Keys (optional - Yahoo Finance doesn't require a key)
ALPHA_VANTAGE_API_KEY=your_api_key_here

# Pipeline Configuration
LOG_LEVEL=INFO
BATCH_SIZE=100
```

### 4. Setup Database

Create a PostgreSQL database:
```bash
createdb financial_data
```

The pipeline will automatically create tables on first run.

## 💻 Usage

### Run the Pipeline

**Basic usage (Yahoo Finance, default tickers, last month):**
```bash
python pipeline.py
```

**Specify tickers:**
```bash
python pipeline.py --tickers AAPL GOOGL MSFT
```

**Specify date range:**
```bash
python pipeline.py --start-date 2024-01-01 --end-date 2024-12-31
```

**Use Alpha Vantage (requires API key):**
```bash
python pipeline.py --source alpha_vantage --tickers AAPL
```

**Fetch longer period:**
```bash
python pipeline.py --period 1y  # Options: 1d, 5d, 1mo, 1y, max
```

### Command Line Arguments

- `--source`: Data source to use (`yahoo` or `alpha_vantage`)
- `--tickers`: Space-separated list of stock tickers
- `--period`: Time period to fetch (1d, 5d, 1mo, 1y, max)
- `--start-date`: Start date (YYYY-MM-DD format)
- `--end-date`: End date (YYYY-MM-DD format)

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

## 📁 Project Structure

```
financial_data_aggregator/
├── config/
│   ├── __init__.py
│   └── config.py              # Configuration management
├── src/
│   ├── extractors/
│   │   ├── yahoo_finance.py   # Yahoo Finance API client
│   │   └── alpha_vantage.py   # Alpha Vantage API client
│   ├── transformers/
│   │   └── data_transformer.py # Data transformation logic
│   ├── loaders/
│   │   └── data_loader.py     # Database loading logic
│   ├── models/
│   │   ├── base.py            # Database configuration
│   │   ├── dimensions.py      # Dimension table models
│   │   └── facts.py           # Fact table models
│   └── utils/
│       ├── logger.py          # Logging configuration
│       └── validators.py      # Data quality validators
├── tests/                      # Unit tests
├── logs/                       # Log files
├── data/                       # Temporary data storage
├── pipeline.py                 # Main pipeline orchestrator
├── requirements.txt            # Python dependencies
├── .env.example               # Environment template
└── README.md                  # This file
```

## 🔍 Example Queries

After running the pipeline, query your data:

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

-- Calculate average price by sector
SELECT 
    c.sector,
    AVG(f.close_price) as avg_price,
    COUNT(*) as record_count
FROM fact_stock_price f
JOIN dim_company c ON f.company_id = c.company_id
GROUP BY c.sector
ORDER BY avg_price DESC;

-- Find stocks with highest volatility
SELECT 
    c.ticker,
    c.company_name,
    AVG(f.price_change_percent) as avg_change_pct,
    STDDEV(f.price_change_percent) as volatility
FROM fact_stock_price f
JOIN dim_company c ON f.company_id = c.company_id
GROUP BY c.ticker, c.company_name
ORDER BY volatility DESC
LIMIT 10;
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
