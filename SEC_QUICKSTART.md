# SEC EDGAR Quick Start Guide

## Installation

```bash
cd /home/archy/Desktop/Server/FinancialData/financial_data_aggregator

# Install new dependencies
source venv/bin/activate
pip install beautifulsoup4 lxml
```

## Update User-Agent (Required)

Before using the SEC extractor, update the User-Agent with your contact info:

**Edit:** `src/extractors/sec_edgar.py`

```python
# Line 20-24
HEADERS = {
    "User-Agent": "YourName your.email@example.com",  # ← Change this!
    "Accept-Encoding": "gzip, deflate",
    "Host": "www.sec.gov"
}
```

## Basic Usage

### 1. Fetch Filings for a Few Tickers

```bash
python sec_pipeline_example.py --tickers AAPL MSFT GOOGL
```

This will:
- Fetch last year of 10-K and 10-Q filings
- Store metadata in the database
- Create new tables: `dim_filing_type` and `fact_sec_filing`

### 2. Test the Extractor Directly

```python
from src.extractors import SECEdgarExtractor

# Initialize
extractor = SECEdgarExtractor()

# Get filings for Apple
filings = extractor.get_company_filings(
    ticker='AAPL',
    filing_types=['10-K', '10-Q'],
    count=5
)

print(filings)
```

### 3. Query the Data

After running the pipeline, query your database:

```python
from src.models import SessionLocal, FactSECFiling, DimCompany, DimFilingType

session = SessionLocal()

# Get all filings
filings = session.query(
    DimCompany.ticker,
    DimFilingType.filing_type,
    FactSECFiling.filing_url
).join(
    DimCompany
).join(
    DimFilingType
).all()

for ticker, filing_type, url in filings:
    print(f"{ticker}: {filing_type} - {url}")
```

## Next Steps

### Option 1: Build RAG System
Extract filing text and store in vector database for Q&A:

```python
extractor = SECEdgarExtractor()

# Get filings
filings = extractor.get_company_filings('AAPL', count=1)

# Extract full text
text = extractor.extract_filing_text(filings.iloc[0]['filing_url'])

# Now chunk and embed this text for RAG...
```

### Option 2: Fundamental Data Analysis
Use the Company Facts API:

```python
facts = extractor.get_company_facts('AAPL')

# Access structured financial data
if facts:
    revenue_data = facts['facts']['us-gaap']['Revenues']
    # Analyze trends, compare companies, etc.
```

### Option 3: Automate with Airflow
Create a scheduled DAG to fetch new filings daily:

```python
from airflow import DAG
from airflow.operators.python import PythonOperator

def fetch_sec_filings():
    from sec_pipeline_example import run_sec_filing_pipeline
    run_sec_filing_pipeline(tickers=['AAPL', 'MSFT'])

dag = DAG('sec_filings', schedule_interval='@daily')
task = PythonOperator(task_id='fetch', python_callable=fetch_sec_filings)
```

## Common Commands

```bash
# Fetch last 3 months of 10-K filings for tech stocks
python sec_pipeline_example.py \
    --tickers AAPL MSFT GOOGL AMZN META \
    --filing-types 10-K \
    --start-date 2024-09-01 \
    --count 10

# Fetch 8-K current reports (material events)
python sec_pipeline_example.py \
    --tickers TSLA \
    --filing-types 8-K \
    --count 20

# Fetch all filing types for a ticker
python sec_pipeline_example.py \
    --tickers NVDA \
    --filing-types 10-K 10-Q 8-K \
    --count 50
```

## Troubleshooting

**Error: "Could not find CIK for ticker"**
- Check ticker symbol is correct
- Ensure company files with SEC (not all do)

**Rate limit warnings**
- The extractor auto-throttles to SEC's 10 req/sec limit
- This is normal for large batches

**Empty DataFrame returned**
- Check date range
- Verify filing types exist for that company
- Try checking SEC website directly

## File Structure

```
financial_data_aggregator/
├── src/
│   ├── extractors/
│   │   └── sec_edgar.py          # ← SEC extractor
│   ├── loaders/
│   │   └── sec_loader.py         # ← Database loader
│   └── models/
│       ├── dimensions.py         # ← Added DimFilingType
│       └── facts.py              # ← Added FactSECFiling
├── sec_pipeline_example.py       # ← Example script
├── SEC_EDGAR_README.md           # ← Full documentation
└── SEC_QUICKSTART.md            # ← This file
```

## What's Next?

1. ✅ Update User-Agent header
2. ✅ Run example pipeline
3. ✅ Query the data
4. 🚀 Build RAG system for filing Q&A
5. 🚀 Add Airflow orchestration
6. 🚀 Deploy to cloud

See `SEC_EDGAR_README.md` for detailed documentation!
