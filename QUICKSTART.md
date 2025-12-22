# Quick Start Guide

## Setup in 5 Minutes

### 1. Install Dependencies
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure Environment
```bash
cp .env.example .env
```

Edit `.env` and add your FRED API key:
```env
DATABASE_URL=sqlite:///financial_data.db
FRED_API_KEY=your_api_key_here  # Get free key: https://fred.stlouisfed.org/
```

### 3. Test All Data Sources
```bash
python test_all_sources.py
```

### 4. Run the Unified Pipeline
```bash
# Run all data sources at once
python unified_pipeline.py --all

# Or run specific sources
python unified_pipeline.py --crypto --bonds
python unified_pipeline.py --economic
python unified_pipeline.py --stocks
```

## What Gets Created

The unified pipeline will:
1. ✅ Create database tables (star schema)
2. ✅ Extract data from multiple sources:
   - **Stocks:** Yahoo Finance (AAPL, MSFT, etc.)
   - **Crypto:** CoinGecko (BTC, ETH, ADA)
   - **Bonds:** FRED & Yahoo Finance (3MO, 10Y, 30Y)
   - **Economic Indicators:** FRED (GDP, unemployment, CPI, etc.)
3. ✅ Validate data quality
4. ✅ Transform data into dimensional model
5. ✅ Load into SQLite (or PostgreSQL)

## Verify Results

```bash
# Check logs
ls logs/

# Query crypto data
python query_crypto.py overview

# View database (SQLite)
sqlite3 financial_data.db "SELECT COUNT(*) FROM fact_crypto_price;"
```

## Quick Query Examples

**Crypto overview:**
```bash
python query_crypto.py overview
python query_crypto.py compare BTC ETH ADA
```

**SQL - Latest Economic Indicators:**
```sql
SELECT 
    ei.indicator_code,
    ei.indicator_name,
    f.value
FROM fact_economic_indicator f
JOIN dim_economic_indicator ei ON f.indicator_id = ei.indicator_id
JOIN dim_date d ON f.date_id = d.date_id
ORDER BY d.date DESC
LIMIT 10;
```

## Troubleshooting

**Import errors?**
- Make sure you're in the virtual environment
- Try: `export PYTHONPATH="${PYTHONPATH}:$(pwd)"`

**API errors?**
- Check FRED_API_KEY is set in .env
- CoinGecko rate limit: Add delays in config
- Check logs/pipeline_*.log for details

**No data extracted?**
- Check your internet connection
- Run test script: `python test_all_sources.py`
- Verify API keys are valid

## Next Steps

1. Explore README.md for full documentation
2. Customize `config/pipeline_config.yaml` for your needs:
   - Add/remove tickers and symbols
   - Adjust date ranges
   - Enable/disable sources
3. Query data with SQL or Python tools
4. Build analytics on the star schema
5. Set up scheduled runs with cron/Airflow
6. Launch dashboard: `./run_dashboard.sh`
