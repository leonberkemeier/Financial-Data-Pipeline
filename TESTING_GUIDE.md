# Testing Guide: Cryptocurrency and Bond Data Integration

This guide explains how to test the new cryptocurrency and bond data extraction features.

## Prerequisites

1. **Virtual Environment**: Ensure your venv is activated
   ```bash
   source venv/bin/activate
   ```

2. **Database**: PostgreSQL must be running and configured
   ```bash
   # Check DATABASE_URL in .env
   cat .env | grep DATABASE_URL
   ```

3. **API Keys** (for bonds only):
   - For **cryptocurrencies**: No API key needed (CoinGecko is free)
   - For **bonds**: Get a free FRED API key at https://fred.stlouisfed.org/docs/api/
   
   Set the FRED key in your `.env`:
   ```bash
   echo "FRED_API_KEY=your_api_key_here" >> .env
   ```

## Test Files

Two test scripts have been created:

### 1. Cryptocurrency Test (`test_crypto.py`)
Tests the complete crypto ETL pipeline: extract → validate → transform → load

**What it tests:**
- CoinGecko API extraction for Bitcoin, Ethereum, Cardano (first 3 configured cryptos)
- Data quality validation (negative prices, duplicates, missing values)
- Transformation to star schema format
- Loading into `dim_crypto_asset` and `fact_crypto_price` tables
- Verification queries to confirm data was loaded

### 2. Bond Test (`test_bonds.py`)
Tests the complete bond ETL pipeline with US Treasury data

**What it tests:**
- FRED API extraction for US Treasury yields (3-month, 2-year, 10-year, 30-year)
- Corporate bond yields extraction (AAA and BBB rated)
- Data quality validation
- Transformation to star schema format
- Loading into `dim_issuer`, `dim_bond`, and `fact_bond_price` tables
- Verification queries

## Running the Tests

### Test Cryptocurrency Pipeline

```bash
# From project root directory
python test_crypto.py
```

**Expected Output:**
```
============================================================================
CRYPTOCURRENCY ETL PIPELINE TEST
============================================================================
Initializing database...
Initializing CoinGecko extractor...
============================================================================
EXTRACT PHASE
============================================================================
Extracting crypto data for symbols: ['BTC', 'ETH', 'ADA']
Extracted 21 price records
...
```

**Success indicators:**
- "TEST COMPLETED SUCCESSFULLY ✓" message
- Records loaded > 0
- Sample price records displayed from database
- Exit code 0

### Test Bond Pipeline

First, set your FRED API key:
```bash
export FRED_API_KEY="your_api_key_from_stlouisfed"
```

Then run:
```bash
python test_bonds.py
```

**Expected Output:**
```
============================================================================
BOND ETL PIPELINE TEST
============================================================================
Initializing database...
Initializing FRED bond extractor...
============================================================================
EXTRACT PHASE - Treasury Yields
============================================================================
Extracting treasury yields for periods: ['DGS3MO', 'DGS2', 'DGS10', 'DGS30']
Extracted 16 yield records
...
```

**Success indicators:**
- "TEST COMPLETED SUCCESSFULLY ✓" message
- Treasury yield data extracted
- Records loaded > 0
- Sample bond price records displayed from database
- Exit code 0

## Test Output Files

Logs are saved in `logs/` directory:
```bash
# View test logs
tail -f logs/pipeline_*.log
```

## Troubleshooting

### Crypto Test Issues

**Error: "CoinGecko API timeout"**
- CoinGecko may be rate-limiting requests
- Wait a minute and try again
- Check your internet connection

**Error: "No data extracted"**
- Verify you have internet access
- Check if symbol names are correct in `config/config.py`
- Try adding more common symbols: BTC, ETH, ADA, SOL

### Bond Test Issues

**Error: "FRED_API_KEY not set"**
```bash
# Make sure key is in environment
echo $FRED_API_KEY
# Or set it
export FRED_API_KEY="your_key"
```

**Error: "No treasury yield data extracted"**
- Verify your FRED API key is valid
- Check FRED website: https://fred.stlouisfed.org/
- Ensure you have internet access

**Error: "Failed to connect to database"**
- Verify PostgreSQL is running: `pg_isready`
- Check DATABASE_URL in `.env`
- Ensure database exists: `createdb financial_data`

## Database Verification

After running tests, verify data was loaded:

```bash
# Connect to database
psql -d financial_data -U your_user

# Query crypto assets
SELECT * FROM dim_crypto_asset;

# Query crypto prices
SELECT * FROM fact_crypto_price LIMIT 5;

# Query issuers
SELECT * FROM dim_issuer;

# Query bonds
SELECT * FROM dim_bond;

# Query bond prices
SELECT * FROM fact_bond_price LIMIT 5;
```

## Performance Notes

- **Crypto test**: ~5-10 seconds (depends on CoinGecko API)
- **Bond test**: ~10-15 seconds (depends on FRED API)
- First run initializes database schema
- Subsequent runs are faster as tables already exist

## Continuous Testing

To run both tests in sequence:

```bash
#!/bin/bash
export FRED_API_KEY="your_api_key"

echo "Running crypto test..."
python test_crypto.py
if [ $? -ne 0 ]; then
    echo "Crypto test failed!"
    exit 1
fi

echo "Running bond test..."
python test_bonds.py
if [ $? -ne 0 ]; then
    echo "Bond test failed!"
    exit 1
fi

echo "All tests passed!"
```

## Next Steps

After successful tests:

1. **Configure for Production**:
   - Update `CRYPTO_SYMBOLS` in `config/config.py` with desired cryptocurrencies
   - Configure `BOND_TYPES` with desired bond instruments
   - Set batch sizes if needed

2. **Integrate with Main Pipeline**:
   - Update `pipeline.py` with `--asset-type` argument
   - Run all three asset classes together

3. **Dashboard Integration**:
   - Extend the dashboard to display crypto and bond data
   - Create visualizations for price trends

4. **Scheduled Jobs**:
   - Set up cron jobs or Airflow to run daily/hourly
   - Example: `0 9 * * * python test_crypto.py` (daily at 9 AM)

## Support

For issues or questions:
- Check log files in `logs/` directory
- Review API documentation:
  - CoinGecko: https://www.coingecko.com/api/documentations/v3
  - FRED: https://fred.stlouisfed.org/docs/api/
- Verify data quality in database

