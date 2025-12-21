# Quick Test Guide

## One-Line Quick Start

### Test Cryptocurrency (no setup needed)
```bash
python test_crypto.py
```

### Test Bonds (with FRED API key)
```bash
export FRED_API_KEY="your_api_key_here"
python test_bonds.py
```

### Run Both Tests
```bash
chmod +x run_tests.sh
./run_tests.sh
```

---

## Step-by-Step Testing

### 1. Cryptocurrency Test (5-10 seconds)

```bash
# Activate virtual environment
source venv/bin/activate

# Run crypto test
python test_crypto.py
```

**What happens:**
- Downloads Bitcoin, Ethereum, Cardano prices from CoinGecko (free API)
- Validates data quality
- Transforms to star schema
- Loads into database
- Shows 5 sample records

**Success = "TEST COMPLETED SUCCESSFULLY ✓" and exit code 0**

---

### 2. Bond Test (10-15 seconds)

**Prerequisites:**
1. Get free FRED API key: https://fred.stlouisfed.org/docs/api/
2. Set environment variable:
   ```bash
   export FRED_API_KEY="e9d1234567890abcdef1234567890abcd"
   ```

**Run test:**
```bash
python test_bonds.py
```

**What happens:**
- Downloads US Treasury yields (3MO, 2Y, 10Y, 30Y) from FRED
- Validates data quality  
- Transforms to star schema
- Loads into database
- Shows 5 sample records

**Success = "TEST COMPLETED SUCCESSFULLY ✓" and exit code 0**

---

## Common Issues & Fixes

| Issue | Solution |
|-------|----------|
| `ModuleNotFoundError: No module named 'requests'` | `pip install -r requirements.txt` |
| `ModuleNotFoundError: No module named 'src'` | Run from project root: `pwd` should show `financial_data_aggregator` |
| `FRED_API_KEY not set` (bonds) | `export FRED_API_KEY="your_key"` |
| `No database configured` | Check `.env` file has `DATABASE_URL` |
| `Connection refused (database)` | Start PostgreSQL: `pg_isready` |
| `CoinGecko API timeout` | Wait 60 seconds, retry (rate limit) |

---

## Verify Data in Database

After tests pass, verify data was actually loaded:

```bash
# Connect to database
psql -d financial_data

# Check crypto assets (should show BTC, ETH, ADA)
\d dim_crypto_asset
SELECT symbol, name, chain FROM dim_crypto_asset;

# Check crypto prices (should show 7+ days of data)
SELECT COUNT(*) FROM fact_crypto_price;

# Check treasury yields (should show 4 periods × ~20 days)
\d dim_bond
SELECT isin, bond_type FROM dim_bond;

# Check bond prices
SELECT COUNT(*) FROM fact_bond_price;

# Exit
\q
```

---

## Test Output Files

All test logs saved to: `logs/pipeline_YYYY-MM-DD.log`

View in real-time:
```bash
tail -f logs/pipeline_*.log
```

---

## Performance Expectations

| Test | Time | Records |
|------|------|---------|
| Crypto extract | 3-5s | 21 (3 symbols × 7 days) |
| Crypto validate | <1s | - |
| Crypto transform | <1s | 21 |
| Crypto load | <1s | ~20 new records |
| **Crypto Total** | **5-10s** | **21 price records** |
| Bond extract | 5-8s | 16 (4 periods × ~4 days) |
| Bond validate | <1s | - |
| Bond transform | <1s | 16 |
| Bond load | <1s | ~15 new records |
| **Bond Total** | **10-15s** | **~15 price records** |

---

## Automated Testing Script

Run both tests with one command:

```bash
./run_tests.sh
```

Script will:
- ✓ Check virtual environment
- ✓ Check database configuration
- ✓ Check Python dependencies
- ✓ Run crypto test
- ✓ Run bond test (if FRED_API_KEY set)
- ✓ Show summary with pass/fail

---

## Next Steps After Passing Tests

1. **Run full example:**
   ```bash
   python pipeline.py --source yahoo --tickers AAPL MSFT
   ```

2. **View dashboard:**
   ```bash
   ./run_dashboard.sh
   # Open http://localhost:5000
   ```

3. **Configure for continuous runs:**
   - Edit `config/config.py` to customize:
     - `CRYPTO_SYMBOLS` (add/remove cryptocurrencies)
     - `BOND_TYPES` (add/remove bond instruments)
   
4. **Schedule with cron:**
   ```bash
   # Run daily at 9 AM
   0 9 * * * cd /path/to/financial_data_aggregator && python test_crypto.py
   ```

---

## Query Examples

After loading data, try these queries:

```sql
-- Latest crypto prices
SELECT ca.symbol, ca.name, fp.price, fd.date
FROM fact_crypto_price fp
JOIN dim_crypto_asset ca ON fp.crypto_id = ca.crypto_id
JOIN dim_date fd ON fp.date_id = fd.date_id
ORDER BY fd.date DESC
LIMIT 10;

-- Bond yields
SELECT db.isin, fb.yield_percent, fd.date
FROM fact_bond_price fb
JOIN dim_bond db ON fb.bond_id = db.bond_id
JOIN dim_date fd ON fb.date_id = fd.date_id
WHERE db.bond_type = 'Government'
ORDER BY fd.date DESC
LIMIT 10;

-- Crypto price changes
SELECT ca.symbol, 
       MIN(fp.price) as min_price,
       MAX(fp.price) as max_price,
       (MAX(fp.price) - MIN(fp.price)) / MIN(fp.price) * 100 as pct_change
FROM fact_crypto_price fp
JOIN dim_crypto_asset ca ON fp.crypto_id = ca.crypto_id
GROUP BY ca.symbol;
```

