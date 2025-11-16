# SEC EDGAR Filing Extraction

This module adds SEC EDGAR filing extraction capabilities to the Financial Data Aggregator, allowing you to fetch, store, and analyze company filings like 10-K, 10-Q, and 8-K reports.

## Features

- **Automated Filing Retrieval**: Fetch 10-K, 10-Q, 8-K, and other SEC filings
- **Rate Limiting**: Built-in compliance with SEC's 10 requests/second limit
- **CIK Resolution**: Automatic ticker-to-CIK mapping
- **Structured Storage**: Star schema design with filing metadata and content
- **Batch Processing**: Efficient extraction for multiple tickers
- **Company Facts API**: Access to structured financial data from SEC

## Quick Start

### 1. Install Dependencies

```bash
# Activate your virtual environment
source venv/bin/activate

# Install new dependencies
pip install -r requirements.txt
```

### 2. Run the SEC Pipeline

**Basic usage (fetch last year of 10-K and 10-Q filings):**
```bash
python sec_pipeline_example.py --tickers AAPL MSFT GOOGL
```

**Fetch specific filing types:**
```bash
python sec_pipeline_example.py --tickers AAPL --filing-types 10-K 8-K
```

**Specify date range:**
```bash
python sec_pipeline_example.py --tickers AAPL MSFT \
    --start-date 2023-01-01 \
    --end-date 2023-12-31
```

**Fetch more filings per ticker:**
```bash
python sec_pipeline_example.py --tickers AAPL --count 20
```

## Database Schema

### New Tables

#### `dim_filing_type`
Dimension table for SEC filing types.

| Column | Type | Description |
|--------|------|-------------|
| filing_type_id | Integer | Primary key |
| filing_type | String(20) | Filing type code (e.g., '10-K') |
| description | String(255) | Description of filing |
| category | String(50) | Category (Annual, Quarterly, etc.) |
| created_at | DateTime | Creation timestamp |

#### `fact_sec_filing`
Fact table storing SEC filing metadata and content.

| Column | Type | Description |
|--------|------|-------------|
| filing_id | Integer | Primary key |
| company_id | Integer | FK to dim_company |
| filing_type_id | Integer | FK to dim_filing_type |
| date_id | Integer | FK to dim_date |
| source_id | Integer | FK to dim_data_source |
| cik | String(10) | Company CIK number |
| accession_number | String(20) | Unique filing identifier |
| file_number | String(20) | SEC file number |
| accepted_date | DateTime | Filing acceptance date |
| filing_url | String(500) | URL to filing document |
| filing_text | String | Extracted text content (optional) |
| filing_size | Integer | Size of filing text in bytes |

## API Usage

### Basic Extraction

```python
from src.extractors import SECEdgarExtractor

# Initialize extractor
extractor = SECEdgarExtractor()

# Fetch filings for a single ticker
filings_df = extractor.get_company_filings(
    ticker='AAPL',
    filing_types=['10-K', '10-Q'],
    start_date='2023-01-01',
    end_date='2023-12-31',
    count=10
)

print(filings_df.head())
```

### Batch Extraction

```python
# Fetch filings for multiple tickers
tickers = ['AAPL', 'MSFT', 'GOOGL', 'AMZN']
filings_df = extractor.extract_filings_batch(
    tickers=tickers,
    filing_types=['10-K', '10-Q'],
    count_per_ticker=5
)
```

### Extract Filing Text

```python
# Get filing metadata
filings_df = extractor.get_company_filings(ticker='AAPL', count=1)

# Extract text from first filing
filing_url = filings_df.iloc[0]['filing_url']
text = extractor.extract_filing_text(filing_url)

print(f"Filing contains {len(text)} characters")
```

### Get Company Facts

```python
# Fetch structured financial data from SEC
facts = extractor.get_company_facts(ticker='AAPL')

if facts:
    # Access revenue data
    revenue = facts['facts']['us-gaap']['Revenues']
    print(revenue)
```

## Example Queries

After loading SEC filing data, you can query it:

### Find Latest Filings

```sql
SELECT 
    c.ticker,
    c.company_name,
    ft.filing_type,
    d.date,
    f.filing_url
FROM fact_sec_filing f
JOIN dim_company c ON f.company_id = c.company_id
JOIN dim_filing_type ft ON f.filing_type_id = ft.filing_type_id
JOIN dim_date d ON f.date_id = d.date_id
ORDER BY d.date DESC
LIMIT 10;
```

### Count Filings by Type

```sql
SELECT 
    ft.filing_type,
    ft.description,
    COUNT(*) as filing_count
FROM fact_sec_filing f
JOIN dim_filing_type ft ON f.filing_type_id = ft.filing_type_id
GROUP BY ft.filing_type, ft.description
ORDER BY filing_count DESC;
```

### Find Companies with Most Filings

```sql
SELECT 
    c.ticker,
    c.company_name,
    COUNT(*) as total_filings
FROM fact_sec_filing f
JOIN dim_company c ON f.company_id = c.company_id
GROUP BY c.ticker, c.company_name
ORDER BY total_filings DESC
LIMIT 10;
```

## Filing Types Supported

| Type | Description | Category |
|------|-------------|----------|
| 10-K | Annual report | Annual |
| 10-Q | Quarterly report | Quarterly |
| 8-K | Current report (material events) | Current |
| 10-K/A | Amended annual report | Annual |
| 10-Q/A | Amended quarterly report | Quarterly |
| S-1 | Registration statement (IPO) | Registration |
| DEF 14A | Proxy statement | Proxy |

## SEC Fair Access Policy

The extractor automatically complies with SEC's fair access policy:
- Maximum 10 requests per second
- User-Agent header includes identification
- Built-in rate limiting between requests

**Important**: Update the User-Agent in `src/extractors/sec_edgar.py` with your contact information:

```python
HEADERS = {
    "User-Agent": "Your Company Name your.email@example.com",
    ...
}
```

## Next Steps

### Enable RAG System for Financial Q&A

1. **Store filing text in vector database**:
   - Use the `extract_filing_text()` method to get full text
   - Chunk text into manageable segments
   - Generate embeddings using OpenAI or similar
   - Store in Pinecone, Chroma, or Weaviate

2. **Build Q&A interface**:
   ```python
   # Example: Query filings about risk factors
   query = "What are the main risk factors for AAPL?"
   # Retrieve relevant chunks from vector DB
   # Generate answer using LLM with context
   ```

### Advanced Analysis

- **Fundamental Metrics**: Extract financial tables from 10-K/10-Q
- **Sentiment Analysis**: Analyze MD&A sections for sentiment trends
- **Topic Modeling**: Identify common themes across filings
- **Risk Assessment**: Track changes in risk factor disclosures

## Troubleshooting

### Rate Limit Errors
If you encounter rate limit errors, the extractor will automatically slow down. For large batches, consider:
- Reducing `count_per_ticker`
- Processing tickers in smaller batches
- Adding delays between batch runs

### CIK Not Found
Some tickers may not have CIKs in the SEC database:
- Check if the ticker is correct
- Ensure the company files with the SEC (foreign companies may not)
- Try searching manually at https://www.sec.gov/edgar/searchedgar/companysearch

### Empty Results
If no filings are returned:
- Check the date range (some companies may not have filed in that period)
- Verify filing types are correct
- Check SEC's website directly to confirm filings exist

## Resources

- [SEC EDGAR Documentation](https://www.sec.gov/edgar/sec-api-documentation)
- [Understanding SEC Filings](https://www.sec.gov/fast-answers/answers-reportshtml.html)
- [SEC Company Search](https://www.sec.gov/edgar/searchedgar/companysearch)

## Contributing

To add support for additional filing types:

1. Add the filing type to `load_filing_types()` in `sec_loader.py`
2. Update documentation
3. Test extraction with sample tickers
