"""Economic indicators extractor using FRED API."""
import requests
import pandas as pd
import time
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from loguru import logger
import os


class EconomicIndicatorsExtractor:
    """Extract economic indicators from FRED API."""

    def __init__(self, api_key: Optional[str] = None, rate_limit_delay: float = 0.5):
        self.source_name = "fred_economic"
        self.api_key = api_key or os.getenv("FRED_API_KEY")
        self.base_url = "https://api.stlouisfed.org/fred"
        self.session = requests.Session()
        self.rate_limit_delay = rate_limit_delay
        
        if not self.api_key:
            logger.warning("FRED_API_KEY not provided")
        
        # Common economic indicator series IDs
        self.indicators = {
            # GDP & Growth
            'GDP': {
                'series_id': 'GDP',
                'name': 'Gross Domestic Product',
                'category': 'GDP',
                'unit': 'Billions of Dollars',
                'frequency': 'Quarterly'
            },
            'GDPC1': {
                'series_id': 'GDPC1',
                'name': 'Real Gross Domestic Product',
                'category': 'GDP',
                'unit': 'Billions of Chained 2017 Dollars',
                'frequency': 'Quarterly'
            },
            
            # Inflation
            'CPIAUCSL': {
                'series_id': 'CPIAUCSL',
                'name': 'Consumer Price Index',
                'category': 'Inflation',
                'unit': 'Index 1982-1984=100',
                'frequency': 'Monthly'
            },
            'CPILFESL': {
                'series_id': 'CPILFESL',
                'name': 'Core CPI (ex Food & Energy)',
                'category': 'Inflation',
                'unit': 'Index 1982-1984=100',
                'frequency': 'Monthly'
            },
            'PCEPI': {
                'series_id': 'PCEPI',
                'name': 'PCE Price Index',
                'category': 'Inflation',
                'unit': 'Index 2017=100',
                'frequency': 'Monthly'
            },
            
            # Employment
            'UNRATE': {
                'series_id': 'UNRATE',
                'name': 'Unemployment Rate',
                'category': 'Employment',
                'unit': 'Percent',
                'frequency': 'Monthly'
            },
            'PAYEMS': {
                'series_id': 'PAYEMS',
                'name': 'Nonfarm Payrolls',
                'category': 'Employment',
                'unit': 'Thousands of Persons',
                'frequency': 'Monthly'
            },
            'CIVPART': {
                'series_id': 'CIVPART',
                'name': 'Labor Force Participation Rate',
                'category': 'Employment',
                'unit': 'Percent',
                'frequency': 'Monthly'
            },
            
            # Interest Rates
            'FEDFUNDS': {
                'series_id': 'FEDFUNDS',
                'name': 'Federal Funds Effective Rate',
                'category': 'Interest Rates',
                'unit': 'Percent',
                'frequency': 'Monthly'
            },
            'DFF': {
                'series_id': 'DFF',
                'name': 'Federal Funds Rate (Daily)',
                'category': 'Interest Rates',
                'unit': 'Percent',
                'frequency': 'Daily'
            },
            
            # Consumer & Business
            'UMCSENT': {
                'series_id': 'UMCSENT',
                'name': 'Consumer Sentiment Index',
                'category': 'Sentiment',
                'unit': 'Index 1966:Q1=100',
                'frequency': 'Monthly'
            },
            'HOUST': {
                'series_id': 'HOUST',
                'name': 'Housing Starts',
                'category': 'Housing',
                'unit': 'Thousands of Units',
                'frequency': 'Monthly'
            },
            'RSXFS': {
                'series_id': 'RSXFS',
                'name': 'Retail Sales',
                'category': 'Consumer',
                'unit': 'Millions of Dollars',
                'frequency': 'Monthly'
            },
            
            # Money Supply
            'M1SL': {
                'series_id': 'M1SL',
                'name': 'M1 Money Supply',
                'category': 'Money Supply',
                'unit': 'Billions of Dollars',
                'frequency': 'Monthly'
            },
            'M2SL': {
                'series_id': 'M2SL',
                'name': 'M2 Money Supply',
                'category': 'Money Supply',
                'unit': 'Billions of Dollars',
                'frequency': 'Monthly'
            },
        }

    def extract_indicators(
        self,
        indicators: List[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Extract economic indicators.

        Args:
            indicators: List of indicator keys (e.g., ['GDP', 'UNRATE', 'CPIAUCSL'])
            start_date: Start date in 'YYYY-MM-DD' format
            end_date: End date in 'YYYY-MM-DD' format

        Returns:
            DataFrame with economic indicator data
        """
        if indicators is None:
            # Default: key economic indicators
            indicators = ['GDP', 'UNRATE', 'CPIAUCSL', 'FEDFUNDS', 'UMCSENT']
        
        logger.info(f"Extracting {len(indicators)} economic indicators from FRED")
        
        all_data = []
        
        for indicator in indicators:
            try:
                if indicator not in self.indicators:
                    logger.warning(f"Unknown indicator: {indicator}")
                    continue
                
                indicator_info = self.indicators[indicator]
                series_id = indicator_info['series_id']
                
                logger.debug(f"Fetching {indicator_info['name']}")
                
                url = f"{self.base_url}/series/observations"
                params = {
                    "series_id": series_id,
                    "api_key": self.api_key,
                    "file_type": "json"
                }
                
                if start_date:
                    params["observation_start"] = start_date
                if end_date:
                    params["observation_end"] = end_date
                
                response = self.session.get(url, params=params, timeout=10)
                response.raise_for_status()
                data = response.json()
                
                if 'observations' not in data or not data['observations']:
                    logger.warning(f"No data found for {indicator}")
                    time.sleep(self.rate_limit_delay)
                    continue
                
                observations = data['observations']
                df = pd.DataFrame({
                    'date': [obs['date'] for obs in observations],
                    'value': [float(obs['value']) if obs['value'] != '.' else None for obs in observations],
                    'indicator': indicator,
                    'indicator_name': indicator_info['name'],
                    'category': indicator_info['category'],
                    'unit': indicator_info['unit'],
                    'frequency': indicator_info['frequency']
                })
                
                df = df.dropna(subset=['value'])
                
                if not df.empty:
                    all_data.append(df)
                    logger.debug(f"Extracted {len(df)} records for {indicator}")
                
                # Rate limiting
                time.sleep(self.rate_limit_delay)
                
            except Exception as e:
                logger.error(f"Error fetching {indicator}: {str(e)}")
                time.sleep(self.rate_limit_delay)
                continue
        
        if not all_data:
            logger.warning("No economic indicator data extracted")
            return pd.DataFrame()
        
        combined_data = pd.concat(all_data, ignore_index=True)
        combined_data['date'] = pd.to_datetime(combined_data['date'])
        
        logger.info(f"Extracted {len(combined_data)} total indicator records")
        return combined_data

    def extract_by_category(
        self,
        category: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Extract all indicators in a specific category.

        Args:
            category: Category name (e.g., 'Inflation', 'Employment', 'GDP')
            start_date: Start date
            end_date: End date

        Returns:
            DataFrame with indicator data
        """
        indicators_in_category = [
            key for key, info in self.indicators.items()
            if info['category'] == category
        ]
        
        if not indicators_in_category:
            logger.warning(f"No indicators found for category: {category}")
            return pd.DataFrame()
        
        logger.info(f"Extracting {len(indicators_in_category)} indicators in category '{category}'")
        return self.extract_indicators(indicators_in_category, start_date, end_date)

    def get_latest_values(self, indicators: List[str] = None) -> pd.DataFrame:
        """
        Get the most recent values for specified indicators.

        Args:
            indicators: List of indicator keys

        Returns:
            DataFrame with latest values
        """
        if indicators is None:
            indicators = list(self.indicators.keys())
        
        logger.info(f"Fetching latest values for {len(indicators)} indicators")
        
        # Get last 30 days to ensure we have recent data
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        
        data = self.extract_indicators(
            indicators=indicators,
            start_date=start_date.strftime('%Y-%m-%d'),
            end_date=end_date.strftime('%Y-%m-%d')
        )
        
        if data.empty:
            return pd.DataFrame()
        
        # Get latest value for each indicator
        latest = data.sort_values('date').groupby('indicator').tail(1)
        return latest[['indicator', 'indicator_name', 'category', 'date', 'value', 'unit']].reset_index(drop=True)

    def list_available_indicators(self) -> pd.DataFrame:
        """
        Get a list of all available indicators.

        Returns:
            DataFrame with indicator metadata
        """
        indicators_list = []
        for key, info in self.indicators.items():
            indicators_list.append({
                'key': key,
                'series_id': info['series_id'],
                'name': info['name'],
                'category': info['category'],
                'unit': info['unit'],
                'frequency': info['frequency']
            })
        
        return pd.DataFrame(indicators_list)
