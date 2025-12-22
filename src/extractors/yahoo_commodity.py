"""
Yahoo Finance Commodity Data Extractor

Extracts commodity futures prices from Yahoo Finance.
"""

import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import time


class YahooCommodityExtractor:
    """Extract commodity futures data from Yahoo Finance."""
    
    # Commodity ticker symbols and metadata
    COMMODITIES = {
        # Energy
        'CL=F': {'name': 'Crude Oil WTI', 'category': 'Energy', 'unit': 'barrel'},
        'BZ=F': {'name': 'Brent Crude Oil', 'category': 'Energy', 'unit': 'barrel'},
        'NG=F': {'name': 'Natural Gas', 'category': 'Energy', 'unit': 'MMBtu'},
        'RB=F': {'name': 'RBOB Gasoline', 'category': 'Energy', 'unit': 'gallon'},
        'HO=F': {'name': 'Heating Oil', 'category': 'Energy', 'unit': 'gallon'},
        
        # Precious Metals
        'GC=F': {'name': 'Gold', 'category': 'Metals', 'unit': 'troy ounce'},
        'SI=F': {'name': 'Silver', 'category': 'Metals', 'unit': 'troy ounce'},
        'PL=F': {'name': 'Platinum', 'category': 'Metals', 'unit': 'troy ounce'},
        'PA=F': {'name': 'Palladium', 'category': 'Metals', 'unit': 'troy ounce'},
        
        # Industrial Metals
        'HG=F': {'name': 'Copper', 'category': 'Metals', 'unit': 'pound'},
        
        # Agriculture
        'ZC=F': {'name': 'Corn', 'category': 'Agriculture', 'unit': 'bushel'},
        'ZS=F': {'name': 'Soybeans', 'category': 'Agriculture', 'unit': 'bushel'},
        'ZW=F': {'name': 'Wheat', 'category': 'Agriculture', 'unit': 'bushel'},
        'KC=F': {'name': 'Coffee', 'category': 'Agriculture', 'unit': 'pound'},
        'SB=F': {'name': 'Sugar', 'category': 'Agriculture', 'unit': 'pound'},
        'CC=F': {'name': 'Cocoa', 'category': 'Agriculture', 'unit': 'metric ton'},
        'CT=F': {'name': 'Cotton', 'category': 'Agriculture', 'unit': 'pound'},
    }
    
    def __init__(self, rate_limit_delay: float = 0.5):
        """
        Initialize the Yahoo commodity extractor.
        
        Args:
            rate_limit_delay: Delay between API calls in seconds (default 0.5)
        """
        self.rate_limit_delay = rate_limit_delay
        self.source = 'yahoo_finance'
    
    def get_available_commodities(self, category: Optional[str] = None) -> Dict[str, Dict]:
        """
        Get list of available commodities.
        
        Args:
            category: Filter by category (Energy, Metals, Agriculture)
            
        Returns:
            Dictionary of commodity symbols and metadata
        """
        if category:
            return {
                symbol: info 
                for symbol, info in self.COMMODITIES.items() 
                if info['category'] == category
            }
        return self.COMMODITIES
    
    def extract_commodity_info(self, symbols: Optional[List[str]] = None) -> pd.DataFrame:
        """
        Extract commodity metadata.
        
        Args:
            symbols: List of commodity symbols (e.g., ['CL=F', 'GC=F'])
                    If None, extracts all available commodities
            
        Returns:
            DataFrame with commodity information
        """
        if symbols is None:
            symbols = list(self.COMMODITIES.keys())
        
        commodities = []
        for symbol in symbols:
            if symbol not in self.COMMODITIES:
                print(f"Warning: Unknown commodity symbol {symbol}, skipping")
                continue
            
            info = self.COMMODITIES[symbol]
            commodities.append({
                'symbol': symbol,
                'name': info['name'],
                'category': info['category'],
                'unit': info['unit'],
                'exchange': 'NYMEX/COMEX',  # Most Yahoo futures are from these
                'source': self.source
            })
        
        return pd.DataFrame(commodities)
    
    def extract_commodity_prices(
        self,
        symbols: Optional[List[str]] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        days: int = 30
    ) -> pd.DataFrame:
        """
        Extract commodity price data from Yahoo Finance.
        
        Args:
            symbols: List of commodity symbols (e.g., ['CL=F', 'GC=F'])
                    If None, extracts all available commodities
            start_date: Start date (YYYY-MM-DD format)
            end_date: End date (YYYY-MM-DD format)
            days: Number of days to look back if dates not specified
            
        Returns:
            DataFrame with commodity prices
        """
        if symbols is None:
            symbols = list(self.COMMODITIES.keys())
        
        # Set date range
        if not end_date:
            end_date = datetime.now().strftime('%Y-%m-%d')
        if not start_date:
            start = datetime.now() - timedelta(days=days)
            start_date = start.strftime('%Y-%m-%d')
        
        all_prices = []
        
        for symbol in symbols:
            if symbol not in self.COMMODITIES:
                print(f"Warning: Unknown commodity symbol {symbol}, skipping")
                continue
            
            try:
                print(f"Fetching {self.COMMODITIES[symbol]['name']} ({symbol})...")
                
                # Download data
                ticker = yf.Ticker(symbol)
                hist = ticker.history(start=start_date, end=end_date)
                
                if hist.empty:
                    print(f"  No data available for {symbol}")
                    continue
                
                # Process each row
                for date, row in hist.iterrows():
                    price_data = {
                        'symbol': symbol,
                        'date': date.strftime('%Y-%m-%d'),
                        'open': float(row['Open']) if pd.notna(row['Open']) else None,
                        'high': float(row['High']) if pd.notna(row['High']) else None,
                        'low': float(row['Low']) if pd.notna(row['Low']) else None,
                        'close': float(row['Close']) if pd.notna(row['Close']) else None,
                        'volume': int(row['Volume']) if pd.notna(row['Volume']) else None,
                        'source': self.source,
                        'extracted_at': datetime.now().isoformat()
                    }
                    
                    # Calculate price change
                    if price_data['close'] and price_data['open']:
                        price_data['price_change'] = price_data['close'] - price_data['open']
                        price_data['price_change_percent'] = (
                            (price_data['price_change'] / price_data['open']) * 100
                        )
                    else:
                        price_data['price_change'] = None
                        price_data['price_change_percent'] = None
                    
                    all_prices.append(price_data)
                
                print(f"  Extracted {len(hist)} records")
                
                # Rate limiting
                time.sleep(self.rate_limit_delay)
                
            except Exception as e:
                print(f"Error extracting {symbol}: {str(e)}")
                continue
        
        if not all_prices:
            print("No price data extracted")
            return pd.DataFrame()
        
        df = pd.DataFrame(all_prices)
        print(f"\nTotal records extracted: {len(df)}")
        return df
    
    def extract_latest_prices(self, symbols: Optional[List[str]] = None) -> pd.DataFrame:
        """
        Extract only the latest prices for commodities.
        
        Args:
            symbols: List of commodity symbols
            
        Returns:
            DataFrame with latest prices
        """
        return self.extract_commodity_prices(symbols=symbols, days=1)


if __name__ == "__main__":
    # Test the extractor
    extractor = YahooCommodityExtractor()
    
    # Test with a few commodities
    test_symbols = ['CL=F', 'GC=F', 'SI=F', 'NG=F', 'HG=F']
    
    print("=== Extracting Commodity Info ===")
    info_df = extractor.extract_commodity_info(test_symbols)
    print(info_df)
    
    print("\n=== Extracting Latest Prices ===")
    prices_df = extractor.extract_latest_prices(test_symbols)
    print(prices_df.head())
    
    print("\n=== Available Commodities by Category ===")
    for category in ['Energy', 'Metals', 'Agriculture']:
        commodities = extractor.get_available_commodities(category)
        print(f"\n{category}: {len(commodities)} commodities")
        for symbol, info in commodities.items():
            print(f"  {symbol}: {info['name']}")
