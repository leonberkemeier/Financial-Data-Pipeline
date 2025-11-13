# Quick Start Guide

## Setup in 5 Minutes

### 1. Install Dependencies
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure Database
```bash
# Create PostgreSQL database
createdb financial_data

# Or use SQLite for testing (update .env)
# DATABASE_URL=sqlite:///./financial_data.db
```

### 3. Create .env file
```bash
cp .env.example .env
# Edit .env with your database connection
```

### 4. Run the Pipeline
```bash
# Default: Yahoo Finance, 10 stocks, last month
python pipeline.py

# Or specify your own tickers
python pipeline.py --tickers AAPL TSLA NVDA
```

## What Gets Created

The pipeline will:
1. ✅ Create database tables (star schema)
2. ✅ Extract stock data from Yahoo Finance
3. ✅ Validate data quality
4. ✅ Transform data into dimensional model
5. ✅ Load into PostgreSQL

## Verify Results

```bash
# Check logs
ls logs/

# Query the database
psql financial_data -c "SELECT COUNT(*) FROM fact_stock_price;"
```

## Example SQL Query

```sql
SELECT 
    c.ticker,
    c.company_name,
    d.date,
    f.close_price,
    f.price_change_percent
FROM fact_stock_price f
JOIN dim_company c ON f.company_id = c.company_id
JOIN dim_date d ON f.date_id = d.date_id
ORDER BY d.date DESC
LIMIT 10;
```

## Troubleshooting

**Import errors?**
- Make sure you're in the virtual environment
- Try: `export PYTHONPATH="${PYTHONPATH}:$(pwd)"`

**Database connection error?**
- Check your DATABASE_URL in .env
- Ensure PostgreSQL is running

**No data extracted?**
- Check your internet connection
- Try with fewer tickers first
- Check logs/pipeline_*.log for details

## Next Steps

1. Explore the README.md for full documentation
2. Customize tickers in config/config.py
3. Add more data sources
4. Build analytics on top of the star schema
5. Set up scheduled runs with cron/Airflow
