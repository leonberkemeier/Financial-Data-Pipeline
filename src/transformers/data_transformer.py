"""Transform raw data into star schema format."""
import pandas as pd
from datetime import datetime
from typing import Dict, Tuple
from loguru import logger
import calendar


class DataTransformer:
    """Transform extracted data for loading into star schema."""

    @staticmethod
    def transform_date_dimension(dates: pd.Series) -> pd.DataFrame:
        """
        Transform dates into date dimension format.

        Args:
            dates: Series of dates

        Returns:
            DataFrame with date dimension attributes
        """
        logger.info("Transforming date dimension")
        
        unique_dates = pd.to_datetime(dates).unique()
        
        date_data = []
        for date in unique_dates:
            date_data.append({
                'date': date.date(),
                'year': date.year,
                'quarter': (date.month - 1) // 3 + 1,
                'month': date.month,
                'week': date.isocalendar()[1],
                'day': date.day,
                'day_of_week': date.dayofweek,
                'day_name': date.strftime('%A'),
                'is_weekend': 1 if date.dayofweek >= 5 else 0,
                'is_quarter_end': 1 if date.month in [3, 6, 9, 12] and date.day == calendar.monthrange(date.year, date.month)[1] else 0,
                'is_year_end': 1 if date.month == 12 and date.day == 31 else 0
            })
        
        df = pd.DataFrame(date_data)
        logger.info(f"Transformed {len(df)} date records")
        return df

    @staticmethod
    def transform_company_dimension(company_df: pd.DataFrame) -> pd.DataFrame:
        """
        Transform company data into company dimension format.

        Args:
            company_df: DataFrame with raw company data

        Returns:
            DataFrame with company dimension attributes
        """
        logger.info("Transforming company dimension")
        
        # Select and rename columns
        transformed = company_df[[
            'ticker', 'company_name', 'sector', 'industry', 'country'
        ]].copy()
        
        # Clean data
        transformed = transformed.fillna({
            'company_name': 'Unknown',
            'sector': 'Unknown',
            'industry': 'Unknown',
            'country': 'Unknown'
        })
        
        # Remove duplicates
        transformed = transformed.drop_duplicates(subset=['ticker'])
        
        logger.info(f"Transformed {len(transformed)} company records")
        return transformed

    @staticmethod
    def transform_exchange_dimension(company_df: pd.DataFrame) -> pd.DataFrame:
        """
        Transform exchange data into exchange dimension format.

        Args:
            company_df: DataFrame with raw company data containing exchange info

        Returns:
            DataFrame with exchange dimension attributes
        """
        logger.info("Transforming exchange dimension")
        
        if 'exchange' not in company_df.columns:
            logger.warning("No exchange data found")
            return pd.DataFrame(columns=['exchange_code', 'exchange_name', 'country', 'timezone', 'currency'])
        
        # Extract unique exchanges
        exchange_data = company_df[['exchange', 'country', 'currency']].copy()
        exchange_data = exchange_data.dropna(subset=['exchange'])
        exchange_data = exchange_data.drop_duplicates(subset=['exchange'])
        
        # Rename and add default values
        exchange_data = exchange_data.rename(columns={'exchange': 'exchange_code'})
        exchange_data['exchange_name'] = exchange_data['exchange_code']  # Could be enriched
        exchange_data['timezone'] = 'UTC'  # Could be enriched based on exchange
        
        logger.info(f"Transformed {len(exchange_data)} exchange records")
        return exchange_data

    @staticmethod
    def transform_stock_prices(
        price_df: pd.DataFrame,
        company_mapping: Dict[str, int],
        date_mapping: Dict, 
        source_id: int
    ) -> pd.DataFrame:
        """
        Transform stock price data into fact table format.

        Args:
            price_df: DataFrame with raw stock price data
            company_mapping: Dict mapping ticker to company_id
            date_mapping: Dict mapping date to date_id
            source_id: ID of the data source

        Returns:
            DataFrame with fact table attributes
        """
        logger.info("Transforming stock price facts")
        
        transformed = price_df.copy()
        
        # Map foreign keys
        transformed['company_id'] = transformed['ticker'].map(company_mapping)
        transformed['date_id'] = transformed['date'].apply(
            lambda x: date_mapping.get(pd.to_datetime(x).date())
        )
        transformed['source_id'] = source_id
        
        # Calculate derived metrics
        if 'open' in transformed.columns and 'close' in transformed.columns:
            transformed['price_change'] = transformed['close'] - transformed['open']
            transformed['price_change_percent'] = (
                (transformed['close'] - transformed['open']) / transformed['open'] * 100
            ).round(4)
        
        # Select and rename columns for fact table
        fact_columns = {
            'company_id': 'company_id',
            'date_id': 'date_id',
            'source_id': 'source_id',
            'open': 'open_price',
            'high': 'high_price',
            'low': 'low_price',
            'close': 'close_price',
            'adj_close': 'adjusted_close',
            'volume': 'volume',
            'price_change': 'price_change',
            'price_change_percent': 'price_change_percent'
        }
        
        # Keep only columns that exist
        available_columns = {k: v for k, v in fact_columns.items() if k in transformed.columns}
        transformed = transformed.rename(columns=available_columns)
        transformed = transformed[list(available_columns.values())]
        
        # Remove rows with missing required fields
        transformed = transformed.dropna(subset=['company_id', 'date_id', 'close_price'])
        
        # Ensure integer IDs (avoid float IDs from mapping)
        transformed['company_id'] = transformed['company_id'].astype(int)
        transformed['date_id'] = transformed['date_id'].astype(int)
        transformed['source_id'] = int(source_id) if 'source_id' in transformed.columns else source_id
        
        logger.info(f"Transformed {len(transformed)} stock price records")
        return transformed

    @staticmethod
    def validate_transformed_data(df: pd.DataFrame, required_columns: list) -> Tuple[bool, str]:
        """
        Validate transformed data.

        Args:
            df: DataFrame to validate
            required_columns: List of required column names

        Returns:
            Tuple of (is_valid, error_message)
        """
        if df.empty:
            return False, "DataFrame is empty"
        
        missing_columns = set(required_columns) - set(df.columns)
        if missing_columns:
            return False, f"Missing required columns: {missing_columns}"
        
        return True, "Valid"
