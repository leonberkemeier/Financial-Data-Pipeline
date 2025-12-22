"""
FRED Commodity Data Extractor

Extracts commodity price data from Federal Reserve Economic Data (FRED).
"""

import requests
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import os
import time


class FREDCommodityExtractor:
    """Extract commodity data from FRED API."""
    
    # FRED series IDs for commodities
    COMMODITIES = {
        # Energy
        'DCOILWTICO': {'name': 'Crude Oil WTI', 'category': 'Energy', 'unit': 'dollars per barrel'},
        'DCOILBRENTEU': {'name': 'Brent Crude Oil', 'category': 'Energy', 'unit': 'dollars per barrel'},
        'DHHNGSP': {'name': 'Natural Gas', 'category': 'Energy', 'unit': 'dollars per million BTU'},
        'GASREGW': {'name': 'Gasoline Regular', 'category': 'Energy', 'unit': 'dollars per gallon'},
        
        # Precious Metals
        'GOLDAMGBD228NLBM': {'name': 'Gold', 'category': 'Metals', 'unit': 'dollars per troy ounce'},
        'GOLDPMGBD228NLBM': {'name': 'Gold PM Fix', 'category': 'Metals', 'unit': 'dollars per troy ounce'},
        'SLVPRUSD': {'name': 'Silver', 'category': 'Metals', 'unit': 'dollars per troy ounce'},
        'PCOPPUSDM': {'name': 'Copper', 'category': 'Metals', 'unit': 'dollars per metric ton'},
        
        # Industrial Metals
        'PALUMUSDM': {'name': 'Aluminum', 'category': 'Metals', 'unit': 'dollars per metric ton'},
        'PZINCUSDM': {'name': 'Zinc', 'category': 'Metals', 'unit': 'dollars per metric ton'},
        'PNICKUSDM': {'name': 'Nickel', 'category': 'Metals', 'unit': 'dollars per metric ton'},
        
        # Agriculture
        'PCOTTINDUSDM': {'name': 'Cotton', 'category': 'Agriculture', 'unit': 'dollars per kilogram'},
        'PWHEAMTUSDM': {'name': 'Wheat', 'category': 'Agriculture', 'unit': 'dollars per metric ton'},
        'PMAIZMT': {'name': 'Corn (Maize)', 'category': 'Agriculture', 'unit': 'dollars per metric ton'},
        'PSOYBUSDM': {'name': 'Soybeans', 'category': 'Agriculture', 'unit': 'dollars per metric ton'},
        'PCOFFOTMUSDM': {'name': 'Coffee', 'category': 'Agriculture', 'unit': 'dollars per kilogram'},
        'PSUGAISAUSDM': {'name': 'Sugar', 'category': 'Agriculture', 'unit': 'cents per pound'},
    }
    
    def __init__(self, api_key: Optional[str] = None, rate_limit_delay: float = 0.5):
        """
        Initialize the FRED commodity extractor.
        
        Args:
            api_key: FRED API key (if None, reads from environment)
            rate_limit_delay: Delay between API calls in seconds (default 0.5)
        """
        self.api_key = api_key or os.getenv('FRED_API_KEY')
        if not self.api_key:
            raise ValueError("FRED_API_KEY not found in environment variables")
        
        self.base_url = "https://api.stlouisfed.org/fred"
        self.rate_limit_delay = rate_limit_delay
        self.source = 'fred'
    
    def get_available_commodities(self, category: Optional[str] = None) -> Dict[str, Dict]:
        """
        Get list of available commodities from FRED.
        
        Args:
            category: Filter by category (Energy, Metals, Agriculture)
            
        Returns:
            Dictionary of series IDs and metadata
        """
        if category:
            return {
                series_id: info 
                for series_id, info in self.COMMODITIES.items() 
                if info['category'] == category
            }
        return self.COMMODITIES
    
    def extract_commodity_info(self, series_ids: Optional[List[str]] = None) -> pd.DataFrame:
        """
        Extract commodity metadata from FRED.
        
        Args:
            series_ids: List of FRED series IDs
                       If None, extracts all available commodities
            
        Returns:
            DataFrame with commodity information
        """
        if series_ids is None:
            series_ids = list(self.COMMODITIES.keys())
        
        commodities = []
        for series_id in series_ids:
            if series_id not in self.COMMODITIES:
                print(f"Warning: Unknown series ID {series_id}, skipping")
                continue
            
            info = self.COMMODITIES[series_id]
            commodities.append({
                'series_id': series_id,
                'name': info['name'],
                'category': info['category'],
                'unit': info['unit'],
                'exchange': 'FRED',
                'source': self.source
            })
        
        return pd.DataFrame(commodities)
    
    def extract_commodity_prices(
        self,
        series_ids: Optional[List[str]] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        days: int = 365
    ) -> pd.DataFrame:
        """
        Extract commodity price data from FRED.
        
        Args:
            series_ids: List of FRED series IDs
            start_date: Start date (YYYY-MM-DD format)
            end_date: End date (YYYY-MM-DD format)
            days: Number of days to look back if dates not specified
            
        Returns:
            DataFrame with commodity prices
        """
        if series_ids is None:
            series_ids = list(self.COMMODITIES.keys())
        
        # Set date range
        if not end_date:
            end_date = datetime.now().strftime('%Y-%m-%d')
        if not start_date:
            start = datetime.now() - timedelta(days=days)
            start_date = start.strftime('%Y-%m-%d')
        
        all_prices = []
        
        for series_id in series_ids:
            if series_id not in self.COMMODITIES:
                print(f"Warning: Unknown series ID {series_id}, skipping")
                continue
            
            try:
                print(f"Fetching {self.COMMODITIES[series_id]['name']} ({series_id})...")
                
                # Build API request
                url = f"{self.base_url}/series/observations"
                params = {
                    'series_id': series_id,
                    'api_key': self.api_key,
                    'file_type': 'json',
                    'observation_start': start_date,
                    'observation_end': end_date
                }
                
                response = requests.get(url, params=params)
                response.raise_for_status()
                data = response.json()
                
                if 'observations' not in data:
                    print(f"  No observations found for {series_id}")
                    continue
                
                observations = data['observations']
                if not observations:
                    print(f"  No data available for {series_id}")
                    continue
                
                # Process observations
                for obs in observations:
                    # Skip if value is missing
                    if obs['value'] == '.':
                        continue
                    
                    try:
                        value = float(obs['value'])
                    except (ValueError, TypeError):
                        continue
                    
                    price_data = {
                        'series_id': series_id,
                        'date': obs['date'],
                        'value': value,
                        'source': self.source,
                        'extracted_at': datetime.now().isoformat()
                    }
                    
                    all_prices.append(price_data)
                
                print(f"  Extracted {len([p for p in all_prices if p['series_id'] == series_id])} records")
                
                # Rate limiting
                time.sleep(self.rate_limit_delay)
                
            except requests.exceptions.RequestException as e:
                print(f"Error fetching {series_id}: {str(e)}")
                continue
            except Exception as e:
                print(f"Unexpected error with {series_id}: {str(e)}")
                continue
        
        if not all_prices:
            print("No price data extracted")
            return pd.DataFrame()
        
        df = pd.DataFrame(all_prices)
        
        # Calculate price changes (day-over-day)
        df = df.sort_values(['series_id', 'date'])
        df['price_change'] = df.groupby('series_id')['value'].diff()
        df['price_change_percent'] = (
            df.groupby('series_id')['value'].pct_change() * 100
        )
        
        print(f"\nTotal records extracted: {len(df)}")
        return df
    
    def extract_latest_prices(self, series_ids: Optional[List[str]] = None) -> pd.DataFrame:
        """
        Extract only the latest prices for commodities.
        
        Args:
            series_ids: List of FRED series IDs
            
        Returns:
            DataFrame with latest prices
        """
        # FRED data is usually daily, so get last 7 days to ensure we get latest
        df = self.extract_commodity_prices(series_ids=series_ids, days=7)
        
        if df.empty:
            return df
        
        # Get most recent value for each series
        latest = df.sort_values('date').groupby('series_id').tail(1)
        return latest.reset_index(drop=True)


if __name__ == "__main__":
    # Test the extractor
    from dotenv import load_dotenv
    load_dotenv()
    
    extractor = FREDCommodityExtractor()
    
    # Test with a few commodities
    test_series = ['DCOILWTICO', 'GOLDAMGBD228NLBM', 'DCOILBRENTEU', 'PCOPPUSDM']
    
    print("=== Extracting Commodity Info ===")
    info_df = extractor.extract_commodity_info(test_series)
    print(info_df)
    
    print("\n=== Extracting Latest Prices ===")
    latest_df = extractor.extract_latest_prices(test_series)
    print(latest_df)
    
    print("\n=== Available Commodities by Category ===")
    for category in ['Energy', 'Metals', 'Agriculture']:
        commodities = extractor.get_available_commodities(category)
        print(f"\n{category}: {len(commodities)} commodities")
        for series_id, info in commodities.items():
            print(f"  {series_id}: {info['name']}")
