# Financial Data Aggregator - Cheat Sheet

## Quick Commands

### Run Pipeline
```bash
# Activate environment
source venv/bin/activate

# Run with default stocks (10 tickers, 1 month)
python pipeline.py

# Run with your own stocks
python pipeline.py --tickers AAPL TSLA NVDA AMZN

# Get more history
python pipeline.py --period 1y --tickers AAPL MSFT

# Specific date range
python pipeline.py --start-date 2024-01-01 --end-date 2024-12-31 --tickers AAPL
```

### View Data in Web Dashboard
```bash
# Start the dashboard
./run_dashboard.sh

# Open in browser
http://localhost:5000
```

### Query the Data
```bash
# Interactive SQL
sqlite3 financial_data.db

# Quick query from command line
sqlite3 financial_data.db "SELECT COUNT(*) FROM fact_stock_price"
```

### Useful Queries

**Latest prices:**
```sql
SELECT 
    c.ticker,
    c.company_name,
    d.date,
    ROUND(f.close_price, 2) as price,
    ROUND(f.price_change_percent, 2) as change_pct
FROM fact_stock_price f
JOIN dim_company c ON f.company_id = c.company_id
JOIN dim_date d ON f.date_id = d.date_id
ORDER BY d.date DESC
LIMIT 20;
```

**Average price by company:**
```sql
SELECT 
    c.ticker,
    COUNT(*) as days,
    ROUND(AVG(f.close_price), 2) as avg_price,
    ROUND(MIN(f.close_price), 2) as min_price,
    ROUND(MAX(f.close_price), 2) as max_price
FROM fact_stock_price f
JOIN dim_company c ON f.company_id = c.company_id
GROUP BY c.ticker
ORDER BY avg_price DESC;
```

**Most volatile stocks:**
```sql
SELECT 
    c.ticker,
    ROUND(AVG(ABS(f.price_change_percent)), 2) as avg_abs_change,
    COUNT(*) as days
FROM fact_stock_price f
JOIN dim_company c ON f.company_id = c.company_id
GROUP BY c.ticker
ORDER BY avg_abs_change DESC;
```

**Trading volume leaders:**
```sql
SELECT 
    c.ticker,
    ROUND(AVG(f.volume) / 1000000.0, 2) as avg_volume_millions
FROM fact_stock_price f
JOIN dim_company c ON f.company_id = c.company_id
GROUP BY c.ticker
ORDER BY avg_volume_millions DESC;
```

## File Locations

- **Database**: `financial_data.db`
- **Logs**: `logs/pipeline_YYYY-MM-DD.log`
- **Config**: `.env` (database URL, API keys)
- **Tickers**: Edit `config/config.py` to change default stocks

## Troubleshooting

**No data extracted?**
```bash
# Check logs
cat logs/pipeline_$(date +%Y-%m-%d).log

# Try with just one stock
python pipeline.py --tickers AAPL --period 5d
```

**Reset database:**
```bash
rm financial_data.db
python pipeline.py
```

**Update packages:**
```bash
source venv/bin/activate
pip install --upgrade -r requirements.txt
```

## Schedule Daily Runs

Add to crontab:
```bash
crontab -e

# Run at 6 PM every day
0 18 * * * cd /home/archy/Desktop/Server/FinancialData/financial_data_aggregator && source venv/bin/activate && python pipeline.py >> logs/cron.log 2>&1
```

## Export Data

```bash
# Export to CSV
sqlite3 -header -csv financial_data.db "
SELECT c.ticker, d.date, f.close_price 
FROM fact_stock_price f
JOIN dim_company c ON f.company_id = c.company_id
JOIN dim_date d ON f.date_id = d.date_id
" > stock_prices.csv

# Backup database
cp financial_data.db backups/financial_data_$(date +%Y%m%d).db
```
