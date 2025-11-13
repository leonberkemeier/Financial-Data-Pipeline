"""Alpha Vantage data extractor."""
import requests
import pandas as pd
from typing import List, Dict, Optional
from loguru import logger
from config.config import ALPHA_VANTAGE_API_KEY
import time


class AlphaVantageExtractor:
    """Extract financial data from Alpha Vantage API."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or ALPHA_VANTAGE_API_KEY
        self.base_url = "https://www.alphavantage.co/query"
        self.source_name = "alpha_vantage"
        
        if not self.api_key:
            logger.warning("Alpha Vantage API key not configured")

    def extract_daily_prices(
        self,
        tickers: List[str],
        outputsize: str = "compact"
    ) -> pd.DataFrame:
        """
        Extract daily stock prices from Alpha Vantage.

        Args:
            tickers: List of stock ticker symbols
            outputsize: 'compact' (100 data points) or 'full' (20+ years)

        Returns:
            DataFrame with stock price data
        """
        if not self.api_key:
            logger.error("Cannot extract data: API key not configured")
            return pd.DataFrame()
        
        logger.info(f"Extracting daily prices for {len(tickers)} tickers from Alpha Vantage")
        
        all_data = []
        
        for ticker in tickers:
            try:
                logger.debug(f"Fetching data for {ticker}")
                
                params = {
                    'function': 'TIME_SERIES_DAILY_ADJUSTED',
                    'symbol': ticker,
                    'outputsize': outputsize,
                    'apikey': self.api_key
                }
                
                response = requests.get(self.base_url, params=params, timeout=30)
                response.raise_for_status()
                
                data = response.json()
                
                # Check for API errors
                if 'Error Message' in data:
                    logger.error(f"API error for {ticker}: {data['Error Message']}")
                    continue
                
                if 'Note' in data:
                    logger.warning(f"API rate limit reached: {data['Note']}")
                    time.sleep(60)  # Wait before retrying
                    continue
                
                # Extract time series data
                time_series = data.get('Time Series (Daily)', {})
                
                if not time_series:
                    logger.warning(f"No data found for {ticker}")
                    continue
                
                # Convert to DataFrame
                df = pd.DataFrame.from_dict(time_series, orient='index')
                df.index = pd.to_datetime(df.index)
                df = df.reset_index()
                df = df.rename(columns={'index': 'date'})
                
                # Rename columns
                df = df.rename(columns={
                    '1. open': 'open',
                    '2. high': 'high',
                    '3. low': 'low',
                    '4. close': 'close',
                    '5. adjusted close': 'adj_close',
                    '6. volume': 'volume',
                    '7. dividend amount': 'dividend',
                    '8. split coefficient': 'split_coefficient'
                })
                
                # Convert to numeric
                numeric_cols = ['open', 'high', 'low', 'close', 'adj_close', 'volume']
                for col in numeric_cols:
                    if col in df.columns:
                        df[col] = pd.to_numeric(df[col], errors='coerce')
                
                df['ticker'] = ticker
                
                all_data.append(df)
                logger.debug(f"Successfully fetched {len(df)} records for {ticker}")
                
                # Rate limiting: Alpha Vantage has 5 calls per minute for free tier
                time.sleep(12)  # Wait 12 seconds between calls
                
            except Exception as e:
                logger.error(f"Error fetching data for {ticker}: {str(e)}")
                continue
        
        if not all_data:
            logger.warning("No data extracted from Alpha Vantage")
            return pd.DataFrame()
        
        combined_data = pd.concat(all_data, ignore_index=True)
        logger.info(f"Extracted {len(combined_data)} total records")
        
        return combined_data

    def extract_company_overview(self, ticker: str) -> Dict:
        """
        Extract company overview data.

        Args:
            ticker: Stock ticker symbol

        Returns:
            Dictionary with company information
        """
        if not self.api_key:
            logger.error("Cannot extract data: API key not configured")
            return {}
        
        try:
            params = {
                'function': 'OVERVIEW',
                'symbol': ticker,
                'apikey': self.api_key
            }
            
            response = requests.get(self.base_url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            return {
                'ticker': ticker,
                'company_name': data.get('Name'),
                'sector': data.get('Sector'),
                'industry': data.get('Industry'),
                'country': data.get('Country'),
                'exchange': data.get('Exchange'),
                'currency': data.get('Currency'),
                'market_cap': data.get('MarketCapitalization'),
                'pe_ratio': data.get('PERatio'),
                'dividend_yield': data.get('DividendYield'),
                'beta': data.get('Beta')
            }
            
        except Exception as e:
            logger.error(f"Error extracting company overview for {ticker}: {str(e)}")
            return {}
