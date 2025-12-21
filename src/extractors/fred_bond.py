"""Federal Reserve Economic Data (FRED) bond and treasury extractor."""
import requests
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from loguru import logger
import os


class FREDBondExtractor:
    """Extract bond and treasury data from Federal Reserve Economic Data (FRED) API."""

    def __init__(self, api_key: Optional[str] = None):
        self.source_name = "fred"
        self.api_key = api_key or os.getenv("FRED_API_KEY")
        self.base_url = "https://api.stlouisfed.org/fred"
        self.session = requests.Session()
        
        if not self.api_key:
            logger.warning("FRED_API_KEY not provided. Register at https://fred.stlouisfed.org/docs/api/")

    def extract_treasury_yields(
        self,
        periods: List[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Extract US Treasury yield data.

        Args:
            periods: List of treasury periods (e.g., ['3MO', '5Y', '10Y', '30Y'])
            start_date: Start date in 'YYYY-MM-DD' format
            end_date: End date in 'YYYY-MM-DD' format

        Returns:
            DataFrame with treasury yield data
        """
        if periods is None:
            periods = ['DGS3MO', 'DGS2', 'DGS5', 'DGS10', 'DGS30']
        
        logger.info(f"Extracting treasury yields for {len(periods)} periods from FRED")
        
        all_data = []
        
        # Map period names to FRED series IDs
        period_mapping = {
            '3MO': 'DGS3MO',
            '1Y': 'DGS1',
            '2Y': 'DGS2',
            '3Y': 'DGS3',
            '5Y': 'DGS5',
            '7Y': 'DGS7',
            '10Y': 'DGS10',
            '20Y': 'DGS20',
            '30Y': 'DGS30',
            'DGS3MO': 'DGS3MO',
            'DGS1': 'DGS1',
            'DGS2': 'DGS2',
            'DGS3': 'DGS3',
            'DGS5': 'DGS5',
            'DGS7': 'DGS7',
            'DGS10': 'DGS10',
            'DGS20': 'DGS20',
            'DGS30': 'DGS30'
        }
        
        for period in periods:
            try:
                series_id = period_mapping.get(period, period)
                logger.debug(f"Fetching treasury data for {period}")
                
                url = f"{self.base_url}/series/{series_id}/observations"
                params = {
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
                    logger.warning(f"No data found for {period}")
                    continue
                
                # Convert to DataFrame
                observations = data['observations']
                df = pd.DataFrame({
                    'date': [obs['date'] for obs in observations],
                    'yield': [float(obs['value']) if obs['value'] != '.' else None for obs in observations],
                    'period': period,
                    'series_id': series_id
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
            logger.warning("No treasury yield data extracted")
            return pd.DataFrame()
        
        # Combine all data
        combined_data = pd.concat(all_data, ignore_index=True)
        combined_data['date'] = pd.to_datetime(combined_data['date'])
        
        logger.info(f"Extracted {len(combined_data)} total treasury yield records")
        return combined_data

    def extract_bond_spreads(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Extract bond spread data (corporate spreads, credit spreads, etc.).

        Args:
            start_date: Start date in 'YYYY-MM-DD' format
            end_date: End date in 'YYYY-MM-DD' format

        Returns:
            DataFrame with bond spread data
        """
        logger.info("Extracting bond spreads from FRED")
        
        # Common bond spread series
        spread_series = {
            'AAA_SPREAD': 'BAMLH0A0HYM2',
            'BAA_SPREAD': 'BAMLH0A4CBBB',
            'HY_SPREAD': 'BAMLH0B0TRUU'
        }
        
        all_data = []
        
        for spread_name, series_id in spread_series.items():
            try:
                logger.debug(f"Fetching {spread_name}")
                
                url = f"{self.base_url}/series/{series_id}/observations"
                params = {
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
                    logger.warning(f"No data found for {spread_name}")
                    continue
                
                observations = data['observations']
                df = pd.DataFrame({
                    'date': [obs['date'] for obs in observations],
                    'spread': [float(obs['value']) if obs['value'] != '.' else None for obs in observations],
                    'spread_type': spread_name,
                    'series_id': series_id
                })
                
                df = df.dropna(subset=['spread'])
                
                if not df.empty:
                    all_data.append(df)
                    logger.debug(f"Successfully fetched {len(df)} records for {spread_name}")
                
            except Exception as e:
                logger.error(f"Error fetching {spread_name}: {str(e)}")
                continue
        
        if not all_data:
            logger.warning("No bond spread data extracted")
            return pd.DataFrame()
        
        combined_data = pd.concat(all_data, ignore_index=True)
        combined_data['date'] = pd.to_datetime(combined_data['date'])
        
        logger.info(f"Extracted {len(combined_data)} total spread records")
        return combined_data

    def extract_corporate_bond_yields(
        self,
        ratings: List[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Extract corporate bond yield data by credit rating.

        Args:
            ratings: List of credit ratings (AAA, AA, A, BBB, BB, B, CCC)
            start_date: Start date in 'YYYY-MM-DD' format
            end_date: End date in 'YYYY-MM-DD' format

        Returns:
            DataFrame with corporate bond yields
        """
        if ratings is None:
            ratings = ['AAA', 'AA', 'A', 'BBB', 'BB', 'B', 'CCC']
        
        logger.info(f"Extracting corporate bond yields for {len(ratings)} ratings")
        
        # Moody's corporate bond yield indices
        rating_mapping = {
            'AAA': 'BAMLH0A1LEVZ',
            'AA': 'BAMLH0A2LEVZ',
            'A': 'BAMLH0A3LEVZ',
            'BBB': 'BAMLH0A4LEVZ',
            'BB': 'BAMLH0B1LEVZ',
            'B': 'BAMLH0B2LEVZ',
            'CCC': 'BAMLH0B3LEVZ'
        }
        
        all_data = []
        
        for rating in ratings:
            try:
                series_id = rating_mapping.get(rating)
                if not series_id:
                    logger.warning(f"No series mapping for {rating}")
                    continue
                
                logger.debug(f"Fetching corporate yields for {rating}")
                
                url = f"{self.base_url}/series/{series_id}/observations"
                params = {
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
                    logger.warning(f"No data found for {rating}")
                    continue
                
                observations = data['observations']
                df = pd.DataFrame({
                    'date': [obs['date'] for obs in observations],
                    'yield': [float(obs['value']) if obs['value'] != '.' else None for obs in observations],
                    'rating': rating,
                    'series_id': series_id
                })
                
                df = df.dropna(subset=['yield'])
                
                if not df.empty:
                    all_data.append(df)
                    logger.debug(f"Successfully fetched {len(df)} records for {rating}")
                
            except Exception as e:
                logger.error(f"Error fetching corporate yields for {rating}: {str(e)}")
                continue
        
        if not all_data:
            logger.warning("No corporate bond yield data extracted")
            return pd.DataFrame()
        
        combined_data = pd.concat(all_data, ignore_index=True)
        combined_data['date'] = pd.to_datetime(combined_data['date'])
        
        logger.info(f"Extracted {len(combined_data)} total corporate yield records")
        return combined_data

    def get_bond_metadata(self) -> Dict[str, Dict]:
        """
        Get metadata for common bond instruments.

        Returns:
            Dictionary with bond metadata
        """
        bonds = {
            'US_3MO': {
                'isin': 'NOTAXED',
                'name': 'US Treasury 3-Month',
                'bond_type': 'Government',
                'maturity_days': 90,
                'country': 'USA',
                'currency': 'USD'
            },
            'US_2Y': {
                'isin': 'NOTAXED',
                'name': 'US Treasury 2-Year',
                'bond_type': 'Government',
                'maturity_days': 730,
                'country': 'USA',
                'currency': 'USD'
            },
            'US_5Y': {
                'isin': 'NOTAXED',
                'name': 'US Treasury 5-Year',
                'bond_type': 'Government',
                'maturity_days': 1825,
                'country': 'USA',
                'currency': 'USD'
            },
            'US_10Y': {
                'isin': 'NOTAXED',
                'name': 'US Treasury 10-Year',
                'bond_type': 'Government',
                'maturity_days': 3650,
                'country': 'USA',
                'currency': 'USD'
            },
            'US_30Y': {
                'isin': 'NOTAXED',
                'name': 'US Treasury 30-Year',
                'bond_type': 'Government',
                'maturity_days': 10950,
                'country': 'USA',
                'currency': 'USD'
            }
        }
        
        return bonds
