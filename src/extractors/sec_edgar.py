"""SEC EDGAR data extractor for fetching company filings."""
import requests
import pandas as pd
from datetime import datetime
from typing import List, Dict, Optional
from loguru import logger
from bs4 import BeautifulSoup
import time
import json
from urllib.parse import urljoin


class SECEdgarExtractor:
    """Extract SEC EDGAR filings data."""

    BASE_URL = "https://www.sec.gov"
    COMPANY_TICKERS_URL = f"{BASE_URL}/files/company_tickers.json"
    
    # SEC requires user agent with contact info
    HEADERS = {
        "User-Agent": "Financial Data Aggregator research@example.com",
        "Accept-Encoding": "gzip, deflate",
        "Host": "www.sec.gov"
    }
    
    # Rate limiting: SEC allows 10 requests per second
    RATE_LIMIT_DELAY = 0.1  # 100ms between requests

    def __init__(self):
        """Initialize SEC EDGAR extractor."""
        self.source_name = "sec_edgar"
        self.session = requests.Session()
        self.session.headers.update(self.HEADERS)
        self.last_request_time = 0
        self._cik_cache = {}
        logger.info("Initialized SEC EDGAR extractor")

    def _rate_limit(self):
        """Enforce rate limiting to comply with SEC fair access policy."""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.RATE_LIMIT_DELAY:
            time.sleep(self.RATE_LIMIT_DELAY - elapsed)
        self.last_request_time = time.time()

    def _get_cik_for_ticker(self, ticker: str) -> Optional[str]:
        """
        Get CIK (Central Index Key) for a ticker symbol.
        
        Args:
            ticker: Stock ticker symbol
            
        Returns:
            CIK as zero-padded 10-digit string, or None if not found
        """
        if ticker in self._cik_cache:
            return self._cik_cache[ticker]
        
        try:
            self._rate_limit()
            response = self.session.get(self.COMPANY_TICKERS_URL, timeout=10)
            response.raise_for_status()
            
            tickers_data = response.json()
            
            # Build cache
            for entry in tickers_data.values():
                tick = entry.get('ticker', '').upper()
                cik = str(entry.get('cik_str', '')).zfill(10)
                self._cik_cache[tick] = cik
            
            cik = self._cik_cache.get(ticker.upper())
            
            if cik:
                logger.debug(f"Found CIK {cik} for ticker {ticker}")
            else:
                logger.warning(f"Could not find CIK for ticker {ticker}")
            
            return cik
            
        except Exception as e:
            logger.error(f"Error fetching CIK for {ticker}: {str(e)}")
            return None

    def get_company_filings(
        self,
        ticker: str,
        filing_types: List[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        count: int = 100
    ) -> pd.DataFrame:
        """
        Get company filings from SEC EDGAR.
        
        Args:
            ticker: Stock ticker symbol
            filing_types: List of filing types (e.g., ['10-K', '10-Q', '8-K'])
            start_date: Start date in 'YYYY-MM-DD' format
            end_date: End date in 'YYYY-MM-DD' format
            count: Maximum number of filings to retrieve
            
        Returns:
            DataFrame with filing information
        """
        if filing_types is None:
            filing_types = ['10-K', '10-Q', '8-K']
        
        logger.info(f"Fetching {filing_types} filings for {ticker}")
        
        # Get CIK for ticker
        cik = self._get_cik_for_ticker(ticker)
        if not cik:
            logger.error(f"Cannot fetch filings: CIK not found for {ticker}")
            return pd.DataFrame()
        
        all_filings = []
        
        for filing_type in filing_types:
            try:
                filings = self._fetch_filings_for_type(
                    cik=cik,
                    ticker=ticker,
                    filing_type=filing_type,
                    start_date=start_date,
                    end_date=end_date,
                    count=count
                )
                all_filings.extend(filings)
                
            except Exception as e:
                logger.error(f"Error fetching {filing_type} for {ticker}: {str(e)}")
                continue
        
        if not all_filings:
            logger.warning(f"No filings found for {ticker}")
            return pd.DataFrame()
        
        df = pd.DataFrame(all_filings)
        logger.info(f"Found {len(df)} filings for {ticker}")
        
        return df

    def _fetch_filings_for_type(
        self,
        cik: str,
        ticker: str,
        filing_type: str,
        start_date: Optional[str],
        end_date: Optional[str],
        count: int
    ) -> List[Dict]:
        """
        Fetch filings of a specific type using SEC EDGAR API.
        
        Args:
            cik: Company CIK number
            ticker: Stock ticker
            filing_type: Filing type (e.g., '10-K', '10-Q')
            start_date: Start date filter
            end_date: End date filter
            count: Maximum number to retrieve
            
        Returns:
            List of filing dictionaries
        """
        # Use SEC's submissions endpoint
        submissions_url = f"{self.BASE_URL}/cgi-bin/browse-edgar"
        
        params = {
            'action': 'getcompany',
            'CIK': cik,
            'type': filing_type,
            'dateb': '',  # End date (leave blank for all)
            'owner': 'exclude',
            'count': count,
            'output': 'atom'
        }
        
        self._rate_limit()
        response = self.session.get(submissions_url, params=params, timeout=10)
        response.raise_for_status()
        
        # Parse Atom feed
        soup = BeautifulSoup(response.content, 'xml')
        entries = soup.find_all('entry')
        
        filings = []
        
        for entry in entries:
            try:
                filing_date_str = entry.find('filing-date').text if entry.find('filing-date') else None
                filing_href = entry.find('filing-href').text if entry.find('filing-href') else None
                
                if not filing_date_str:
                    continue
                
                filing_date = datetime.strptime(filing_date_str, '%Y-%m-%d')
                
                # Apply date filters
                if start_date:
                    start_dt = datetime.strptime(start_date, '%Y-%m-%d')
                    if filing_date < start_dt:
                        continue
                
                if end_date:
                    end_dt = datetime.strptime(end_date, '%Y-%m-%d')
                    if filing_date > end_dt:
                        continue
                
                filing_data = {
                    'ticker': ticker,
                    'cik': cik,
                    'filing_type': filing_type,
                    'filing_date': filing_date_str,
                    'accession_number': entry.find('accession-number').text if entry.find('accession-number') else None,
                    'filing_url': filing_href,
                    'file_number': entry.find('file-number').text if entry.find('file-number') else None,
                    'accepted_date': entry.find('accepted').text if entry.find('accepted') else None,
                }
                
                filings.append(filing_data)
                
            except Exception as e:
                logger.warning(f"Error parsing filing entry: {str(e)}")
                continue
        
        logger.debug(f"Found {len(filings)} {filing_type} filings for {ticker}")
        return filings

    def extract_filing_text(self, filing_url: str) -> Optional[str]:
        """
        Extract text content from a filing URL.
        
        Args:
            filing_url: URL to the filing document (index page)
            
        Returns:
            Extracted text content or None if error
        """
        try:
            # First, fetch the index page to find the actual document
            self._rate_limit()
            response = self.session.get(filing_url, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find the primary document link
            # Look for the primary HTML document
            txt_link = None
            
            # Look for the first document table row
            table = soup.find('table', {'class': 'tableFile'})
            if table:
                rows = table.find_all('tr')[1:]  # Skip header
                if rows:
                    # Strategy: find first .htm file that's NOT .txt and NOT an exhibit
                    for row in rows:
                        cells = row.find_all('td')
                        if len(cells) >= 2:
                            doc_link = cells[2].find('a', href=True) if len(cells) > 2 else None
                            if not doc_link:
                                doc_link = row.find('a', href=True)
                            
                            if doc_link:
                                href = doc_link['href']
                                doc_desc = cells[1].text.strip() if len(cells) > 1 else ''
                                
                                # Get first .htm document that's not a .txt file
                                if (('.htm' in href.lower() or '.html' in href.lower()) and 
                                    '.txt' not in href.lower() and
                                    'R1.htm' not in href and
                                    'R2.htm' not in href and
                                    'FilingSummary' not in href):
                                    txt_link = href
                                    logger.debug(f"Found document: {doc_desc} - {href}")
                                    break
            
            if not txt_link:
                logger.warning(f"Could not find document link in filing index: {filing_url}")
                # Fall back to extracting text from the index page itself
                for script in soup(["script", "style"]):
                    script.decompose()
                text = soup.get_text(separator='\n', strip=True)
                logger.debug(f"Extracted {len(text)} characters from index page (fallback)")
                return text
            
            # Construct full URL and fetch the actual document
            if txt_link.startswith('http'):
                doc_url = txt_link
            else:
                # Build full URL from relative path
                base_url = '/'.join(filing_url.split('/')[:-1])
                doc_url = urljoin(base_url + '/', txt_link)
            
            logger.debug(f"Fetching document from: {doc_url}")
            self._rate_limit()
            doc_response = self.session.get(doc_url, timeout=15)
            doc_response.raise_for_status()
            
            # Parse the document
            doc_soup = BeautifulSoup(doc_response.content, 'html.parser')
            
            # Remove script and style elements
            for script in doc_soup(["script", "style"]):
                script.decompose()
            
            # Get text
            text = doc_soup.get_text(separator='\n', strip=True)
            
            logger.debug(f"Extracted {len(text)} characters from filing document")
            return text
            
        except Exception as e:
            logger.error(f"Error extracting filing text from {filing_url}: {str(e)}")
            return None

    def extract_filings_batch(
        self,
        tickers: List[str],
        filing_types: List[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        count_per_ticker: int = 10
    ) -> pd.DataFrame:
        """
        Extract filings for multiple tickers.
        
        Args:
            tickers: List of stock ticker symbols
            filing_types: List of filing types to fetch
            start_date: Start date in 'YYYY-MM-DD' format
            end_date: End date in 'YYYY-MM-DD' format
            count_per_ticker: Max filings per ticker
            
        Returns:
            DataFrame with all filings
        """
        if filing_types is None:
            filing_types = ['10-K', '10-Q']
        
        logger.info(f"Extracting {filing_types} filings for {len(tickers)} tickers")
        
        all_filings = []
        
        for ticker in tickers:
            try:
                filings_df = self.get_company_filings(
                    ticker=ticker,
                    filing_types=filing_types,
                    start_date=start_date,
                    end_date=end_date,
                    count=count_per_ticker
                )
                
                if not filings_df.empty:
                    all_filings.append(filings_df)
                    
            except Exception as e:
                logger.error(f"Error processing {ticker}: {str(e)}")
                continue
        
        if not all_filings:
            logger.warning("No filings extracted from any ticker")
            return pd.DataFrame()
        
        combined_df = pd.concat(all_filings, ignore_index=True)
        logger.info(f"Extracted {len(combined_df)} total filings")
        
        return combined_df

    def get_company_facts(self, ticker: str) -> Optional[Dict]:
        """
        Get company facts from SEC's Company Facts API.
        
        Args:
            ticker: Stock ticker symbol
            
        Returns:
            Dictionary of company facts or None
        """
        cik = self._get_cik_for_ticker(ticker)
        if not cik:
            return None
        
        try:
            facts_url = f"{self.BASE_URL}/files/company/{cik}/companyfacts.json"
            
            self._rate_limit()
            response = self.session.get(facts_url, timeout=10)
            response.raise_for_status()
            
            facts = response.json()
            logger.info(f"Retrieved company facts for {ticker}")
            
            return facts
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                logger.warning(f"No company facts available for {ticker}")
            else:
                logger.error(f"HTTP error fetching facts for {ticker}: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Error fetching company facts for {ticker}: {str(e)}")
            return None
