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

    def _request_with_retry(self, url: str, max_retries: int = 3, timeout: int = 30, **kwargs):
        """Make HTTP request with retry logic and exponential backoff."""
        for attempt in range(max_retries):
            try:
                self._rate_limit()
                response = self.session.get(url, timeout=timeout, **kwargs)
                response.raise_for_status()
                return response
            except requests.exceptions.Timeout as e:
                wait_time = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s
                if attempt < max_retries - 1:
                    logger.warning(f"Timeout on attempt {attempt + 1}/{max_retries}, retrying in {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    raise e
            except Exception as e:
                raise e

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
            response = self._request_with_retry(self.COMPANY_TICKERS_URL, max_retries=3, timeout=30)
            
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
        
        response = self._request_with_retry(submissions_url, max_retries=3, timeout=30, params=params)
        
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
            
            # Find the primary document link robustly
            primary_href = None
            
            # The index page typically has a table with class containing 'tableFile'
            table = soup.find('table', class_=lambda c: c and 'tableFile' in c if c else False)
            if table:
                rows = table.find_all('tr')
                if rows:
                    # Identify column indices by header labels
                    header_cells = [th.get_text(strip=True).lower() for th in rows[0].find_all(['th','td'])]
                    def col_index(label):
                        try:
                            return header_cells.index(label)
                        except ValueError:
                            return None
                    doc_col = col_index('document')
                    type_col = col_index('type')
                    desc_col = col_index('description')
                    
                    candidate_rows = []
                    for row in rows[1:]:  # skip header
                        cells = row.find_all('td')
                        if not cells:
                            continue
                        # Extract href from the Document column (col 2 typically) OR Type column
                        href = None
                        # Try Document column first
                        if doc_col is not None and doc_col < len(cells):
                            link_tag = cells[doc_col].find('a', href=True)
                            if link_tag:
                                # Check if link is an /ix viewer or direct file
                                potential_href = link_tag['href']
                                # If it's /ix?doc=... extract the file path from query param
                                if '/ix?doc=' in potential_href:
                                    # Extract the doc path - it's already the full archive path
                                    href_full = potential_href.split('doc=')[1]
                                    # Ensure it starts with / but doesn't have duplication
                                    if not href_full.startswith('/'):
                                        href = '/' + href_full
                                    else:
                                        href = href_full
                                else:
                                    href = potential_href
                        # Fall back: try any link in the row
                        if not href:
                            link_tag = row.find('a', href=True)
                            if link_tag:
                                href = link_tag['href']
                        if not href:
                            continue
                        ftype = cells[type_col].get_text(strip=True) if type_col is not None and type_col < len(cells) else ''
                        desc = cells[desc_col].get_text(strip=True) if desc_col is not None and desc_col < len(cells) else ''
                        candidate_rows.append((href, ftype, desc))
                    
                    # Selection strategy:
                    # Prefer the primary HTML document (better formatted), fall back to .txt complete submission
                    primary_types = {'10-K', '10-Q', '8-K', '10-K/A', '10-Q/A'}

                    # 1) Prefer primary HTML doc by type (10-K, 10-Q, 8-K in .htm/.html format)
                    for href, ftype, desc in candidate_rows:
                        lower = href.lower()
                        if (ftype in primary_types) and (lower.endswith('.htm') or lower.endswith('.html')):
                            primary_href = href
                            logger.debug(f"Selected primary HTML doc by type: {ftype} - {href}")
                            break

                    # 2) Otherwise, pick the first HTML doc that isn't an exhibit or summary
                    if not primary_href:
                        for href, ftype, desc in candidate_rows:
                            lower = href.lower()
                            if (lower.endswith('.htm') or lower.endswith('.html')) and 'filingsummary' not in lower and 'exhibit' not in desc.lower():
                                primary_href = href
                                logger.debug(f"Selected first HTML doc: {desc} - {href}")
                                break

                    # 3) Otherwise, try .txt complete submission file
                    if not primary_href:
                        for href, ftype, desc in candidate_rows:
                            lower = href.lower()
                            desc_lower = desc.lower()
                            if lower.endswith('.txt') and ('complete' in desc_lower or 'submission' in desc_lower):
                                primary_href = href
                                logger.debug(f"Selected complete submission text file: {desc} - {href}")
                                break

                    # 4) Fall back to any .txt file
                    if not primary_href:
                        for href, ftype, desc in candidate_rows:
                            if href.lower().endswith('.txt'):
                                primary_href = href
                                logger.debug(f"Selected .txt submission file: {desc} - {href}")
                                break
            
            if not primary_href:
                logger.warning(f"Could not find document link in filing index: {filing_url}")
                # Fall back to extracting text from the index page itself
                for script in soup(["script", "style"]):
                    script.decompose()
                text = soup.get_text(separator='\n', strip=True)
                text = text.replace('\xa0', ' ')
                logger.debug(f"Extracted {len(text)} characters from index page (fallback)")
                return text
            
            # Construct full URL and fetch the actual document
            if primary_href.startswith('http'):
                doc_url = primary_href
            else:
                base_url = '/'.join(filing_url.split('/')[:-1])
                doc_url = urljoin(base_url + '/', primary_href)
            
            logger.debug(f"Fetching document from: {doc_url}")
            self._rate_limit()
            doc_response = self.session.get(doc_url, timeout=30)
            doc_response.raise_for_status()
            
            content_type = doc_response.headers.get('Content-Type', '').lower()
            if 'text/plain' in content_type or doc_url.lower().endswith('.txt'):
                text = doc_response.text
                text = text.replace('\xa0', ' ')
                logger.debug(f"Extracted {len(text)} characters from TXT filing document")
                return text
            
            # Parse the HTML document
            doc_soup = BeautifulSoup(doc_response.content, 'html.parser')
            for script in doc_soup(["script", "style"]):
                script.decompose()
            text = doc_soup.get_text(separator='\n', strip=True)
            text = text.replace('\xa0', ' ')
            logger.debug(f"Extracted {len(text)} characters from HTML filing document")
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
