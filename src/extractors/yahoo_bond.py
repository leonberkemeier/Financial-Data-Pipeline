"""Yahoo Finance bond and treasury yield extractor."""
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from loguru import logger


class YahooBondExtractor:
    """Extract bond and treasury yield data from Yahoo Finance."""

    def __init__(self):
        self.source_name = "yahoo_finance"
        
        # Treasury ETF tickers and their corresponding Treasury bond symbols
        self.treasury_tickers = {
            '3MO': '^IRX',     # 13 Week Treasury Bill
            '5Y': '^FVX',      # Treasury Yield 5 Years
            '10Y': '^TNX',     # Treasury Yield 10 Years
            '30Y': '^TYX',     # Treasury Yield 30 Years
        }
        
        # Treasury bond ETFs for additional data
        self.treasury_etfs = {
            'SHY': '1-3 Year Treasury',
            'IEF': '7-10 Year Treasury',
            'TLT': '20+ Year Treasury',
            'BIL': '1-3 Month Treasury'
        }

    def extract_treasury_yields(
        self,
        periods: List[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Extract US Treasury yield data from Yahoo Finance.

        Args:
            periods: List of treasury periods (e.g., ['3MO', '5Y', '10Y', '30Y'])
            start_date: Start date in 'YYYY-MM-DD' format
            end_date: End date in 'YYYY-MM-DD' format

        Returns:
            DataFrame with treasury yield data
        """
        if periods is None:
            periods = list(self.treasury_tickers.keys())
        
        logger.info(f"Extracting treasury yields for {len(periods)} periods from Yahoo Finance")
        
        all_data = []
        
        for period in periods:
            try:
                ticker_symbol = self.treasury_tickers.get(period)
                if not ticker_symbol:
                    logger.warning(f"No ticker mapping for {period}")
                    continue
                
                logger.debug(f"Fetching treasury data for {period} ({ticker_symbol})")
                
                # Create ticker object
                ticker = yf.Ticker(ticker_symbol)
                
                # Fetch historical data
                hist = ticker.history(
                    start=start_date,
                    end=end_date,
                    interval='1d'
                )
                
                if hist.empty:
                    logger.warning(f"No data found for {period}")
                    continue
                
                # Yahoo Finance returns yield indices where Close = yield value
                df = pd.DataFrame({
                    'date': hist.index.date,
                    'yield': hist['Close'].values,
                    'period': period,
                    'ticker': ticker_symbol
                })
                
                # Remove null values
                df = df.dropna(subset=['yield'])
                
                if not df.empty:
                    all_data.append(df)
                    logger.debug(f"Successfully fetched {len(df)} records for {period}")
                
            except Exception as e:
                logger.error(f"Error fetching treasury data for {period}: {str(e)}")
                continue
        
        if not all_data:
            logger.warning("No treasury yield data extracted from Yahoo Finance")
            return pd.DataFrame()
        
        # Combine all data
        combined_data = pd.concat(all_data, ignore_index=True)
        combined_data['date'] = pd.to_datetime(combined_data['date'])
        
        logger.info(f"Extracted {len(combined_data)} total treasury yield records")
        return combined_data

    def extract_treasury_etf_prices(
        self,
        etf_symbols: List[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Extract Treasury ETF price data.

        Args:
            etf_symbols: List of ETF symbols (e.g., ['SHY', 'IEF', 'TLT'])
            start_date: Start date in 'YYYY-MM-DD' format
            end_date: End date in 'YYYY-MM-DD' format

        Returns:
            DataFrame with ETF price data
        """
        if etf_symbols is None:
            etf_symbols = list(self.treasury_etfs.keys())
        
        logger.info(f"Extracting treasury ETF prices for {len(etf_symbols)} ETFs from Yahoo Finance")
        
        all_data = []
        
        for symbol in etf_symbols:
            try:
                logger.debug(f"Fetching ETF data for {symbol}")
                
                ticker = yf.Ticker(symbol)
                hist = ticker.history(
                    start=start_date,
                    end=end_date,
                    interval='1d'
                )
                
                if hist.empty:
                    logger.warning(f"No data found for {symbol}")
                    continue
                
                df = pd.DataFrame({
                    'date': hist.index.date,
                    'open': hist['Open'].values,
                    'high': hist['High'].values,
                    'low': hist['Low'].values,
                    'close': hist['Close'].values,
                    'volume': hist['Volume'].values,
                    'symbol': symbol,
                    'name': self.treasury_etfs.get(symbol, symbol)
                })
                
                df = df.dropna()
                
                if not df.empty:
                    all_data.append(df)
                    logger.debug(f"Successfully fetched {len(df)} records for {symbol}")
                
            except Exception as e:
                logger.error(f"Error fetching ETF data for {symbol}: {str(e)}")
                continue
        
        if not all_data:
            logger.warning("No treasury ETF data extracted from Yahoo Finance")
            return pd.DataFrame()
        
        combined_data = pd.concat(all_data, ignore_index=True)
        combined_data['date'] = pd.to_datetime(combined_data['date'])
        
        logger.info(f"Extracted {len(combined_data)} total ETF records")
        return combined_data

    def extract_corporate_bond_etfs(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Extract corporate bond ETF data as proxy for corporate bond yields.

        Args:
            start_date: Start date in 'YYYY-MM-DD' format
            end_date: End date in 'YYYY-MM-DD' format

        Returns:
            DataFrame with corporate bond ETF data
        """
        logger.info("Extracting corporate bond ETF data from Yahoo Finance")
        
        # Corporate bond ETFs by rating
        corp_etfs = {
            'LQD': 'Investment Grade Corporate',
            'HYG': 'High Yield Corporate',
            'JNK': 'High Yield Corporate (Alt)',
            'VCIT': 'Intermediate Corporate',
            'VCSH': 'Short-Term Corporate'
        }
        
        all_data = []
        
        for symbol, name in corp_etfs.items():
            try:
                logger.debug(f"Fetching corporate ETF data for {symbol}")
                
                ticker = yf.Ticker(symbol)
                hist = ticker.history(
                    start=start_date,
                    end=end_date,
                    interval='1d'
                )
                
                if hist.empty:
                    logger.warning(f"No data found for {symbol}")
                    continue
                
                df = pd.DataFrame({
                    'date': hist.index.date,
                    'close': hist['Close'].values,
                    'volume': hist['Volume'].values,
                    'symbol': symbol,
                    'name': name
                })
                
                df = df.dropna()
                
                if not df.empty:
                    all_data.append(df)
                    logger.debug(f"Successfully fetched {len(df)} records for {symbol}")
                
            except Exception as e:
                logger.error(f"Error fetching corporate ETF data for {symbol}: {str(e)}")
                continue
        
        if not all_data:
            logger.warning("No corporate bond ETF data extracted")
            return pd.DataFrame()
        
        combined_data = pd.concat(all_data, ignore_index=True)
        combined_data['date'] = pd.to_datetime(combined_data['date'])
        
        logger.info(f"Extracted {len(combined_data)} total corporate ETF records")
        return combined_data

    def get_bond_metadata(self) -> Dict[str, Dict]:
        """
        Get metadata for treasury instruments tracked via Yahoo Finance.

        Returns:
            Dictionary with bond metadata
        """
        bonds = {
            'US_3MO_YF': {
                'ticker': '^IRX',
                'name': 'US Treasury 3-Month (Yahoo)',
                'bond_type': 'Government',
                'maturity_days': 90,
                'country': 'USA',
                'currency': 'USD',
                'source': 'yahoo_finance'
            },
            'US_5Y_YF': {
                'ticker': '^FVX',
                'name': 'US Treasury 5-Year (Yahoo)',
                'bond_type': 'Government',
                'maturity_days': 1825,
                'country': 'USA',
                'currency': 'USD',
                'source': 'yahoo_finance'
            },
            'US_10Y_YF': {
                'ticker': '^TNX',
                'name': 'US Treasury 10-Year (Yahoo)',
                'bond_type': 'Government',
                'maturity_days': 3650,
                'country': 'USA',
                'currency': 'USD',
                'source': 'yahoo_finance'
            },
            'US_30Y_YF': {
                'ticker': '^TYX',
                'name': 'US Treasury 30-Year (Yahoo)',
                'bond_type': 'Government',
                'maturity_days': 10950,
                'country': 'USA',
                'currency': 'USD',
                'source': 'yahoo_finance'
            }
        }
        
        return bonds
