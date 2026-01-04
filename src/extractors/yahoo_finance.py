"""Yahoo Finance data extractor."""
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from loguru import logger


class YahooFinanceExtractor:
    """Extract financial data from Yahoo Finance."""

    def __init__(self):
        self.source_name = "yahoo_finance"

    def extract_stock_prices(
        self,
        tickers: List[str],
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        period: str = "1mo"
    ) -> pd.DataFrame:
        """
        Extract historical stock prices for given tickers.

        Args:
            tickers: List of stock ticker symbols
            start_date: Start date in 'YYYY-MM-DD' format
            end_date: End date in 'YYYY-MM-DD' format
            period: Period to download (e.g., '1d', '5d', '1mo', '1y', 'max')

        Returns:
            DataFrame with stock price data
        """
        logger.info(f"Extracting data for {len(tickers)} tickers from Yahoo Finance")
        
        all_data = []
        
        for ticker in tickers:
            try:
                logger.debug(f"Fetching data for {ticker}")
                
                # Download data
                if start_date and end_date:
                    data = yf.download(
                        ticker,
                        start=start_date,
                        end=end_date,
                        progress=False,
                        auto_adjust=True
                    )
                else:
                    data = yf.download(
                        ticker,
                        period=period,
                        progress=False,
                        auto_adjust=True
                    )
                
                if data.empty:
                    logger.warning(f"No data found for {ticker}")
                    continue
                
                # Reset index to make Date a column
                data = data.reset_index()
                
                # Flatten MultiIndex columns if present (newer yfinance versions)
                if isinstance(data.columns, pd.MultiIndex):
                    data.columns = [col[0] if col[1] == '' else col[0] for col in data.columns]
                
                # Add ticker column
                data['ticker'] = ticker
                
                # Standardize column names (handle different yfinance versions)
                column_mapping = {
                    'Date': 'date',
                    'Open': 'open', 
                    'High': 'high',
                    'Low': 'low',
                    'Close': 'close',
                    'Adj Close': 'adj_close',
                    'Adj_Close': 'adj_close',  # Handle underscore variant
                    'Volume': 'volume'
                }
                
                # Rename only columns that exist
                data = data.rename(columns={k: v for k, v in column_mapping.items() if k in data.columns})
                
                all_data.append(data)
                logger.debug(f"Successfully fetched {len(data)} records for {ticker}")
                
            except Exception as e:
                logger.error(f"Error fetching data for {ticker}: {str(e)}")
                continue
        
        if not all_data:
            logger.warning("No data extracted from Yahoo Finance")
            return pd.DataFrame()
        
        # Combine all data
        combined_data = pd.concat(all_data, ignore_index=True)
        logger.info(f"Extracted {len(combined_data)} total records")
        
        return combined_data

    def extract_company_info(self, tickers: List[str]) -> pd.DataFrame:
        """
        Extract company information for given tickers.

        Args:
            tickers: List of stock ticker symbols

        Returns:
            DataFrame with company information
        """
        logger.info(f"Extracting company info for {len(tickers)} tickers")
        
        company_data = []
        
        for ticker in tickers:
            try:
                stock = yf.Ticker(ticker)
                info = stock.info
                
                company_data.append({
                    'ticker': ticker,
                    'company_name': info.get('longName', info.get('shortName', ticker)),
                    'sector': info.get('sector'),
                    'industry': info.get('industry'),
                    'country': info.get('country'),
                    'exchange': info.get('exchange'),
                    'currency': info.get('currency'),
                    'market_cap': info.get('marketCap'),
                    'pe_ratio': info.get('trailingPE'),
                    'dividend_yield': info.get('dividendYield'),
                    'beta': info.get('beta')
                })
                
                logger.debug(f"Extracted company info for {ticker}")
                
            except Exception as e:
                logger.error(f"Error extracting company info for {ticker}: {str(e)}")
                continue
        
        if not company_data:
            logger.warning("No company data extracted")
            return pd.DataFrame()
        
        df = pd.DataFrame(company_data)
        logger.info(f"Extracted info for {len(df)} companies")
        
        return df
