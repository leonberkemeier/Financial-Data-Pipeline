"""Data quality validation utilities."""
import pandas as pd
from typing import Dict, List, Tuple
from loguru import logger


class DataQualityValidator:
    """Validate data quality for financial data."""

    @staticmethod
    def validate_stock_prices(df: pd.DataFrame) -> Tuple[bool, List[str]]:
        """
        Validate stock price data quality.

        Args:
            df: DataFrame with stock price data

        Returns:
            Tuple of (is_valid, list of error messages)
        """
        errors = []
        
        # Check for required columns
        required_columns = ['ticker', 'date', 'close']
        missing_columns = set(required_columns) - set(df.columns)
        if missing_columns:
            errors.append(f"Missing required columns: {missing_columns}")
            return False, errors
        
        # Check for empty dataframe
        if df.empty:
            errors.append("DataFrame is empty")
            return False, errors
        
        # Check for null values in critical columns
        for col in required_columns:
            null_count = df[col].isnull().sum()
            if null_count > 0:
                errors.append(f"Column '{col}' has {null_count} null values")
        
        # Validate price values
        price_columns = ['open', 'high', 'low', 'close', 'adj_close']
        for col in price_columns:
            if col in df.columns:
                # Check for negative prices
                negative_count = (df[col] < 0).sum()
                if negative_count > 0:
                    errors.append(f"Column '{col}' has {negative_count} negative values")
                
                # Check for unreasonably high prices (> $1M per share)
                high_price_count = (df[col] > 1_000_000).sum()
                if high_price_count > 0:
                    logger.warning(f"Column '{col}' has {high_price_count} values > $1M")
        
        # Validate volume
        if 'volume' in df.columns:
            negative_volume = (df['volume'] < 0).sum()
            if negative_volume > 0:
                errors.append(f"Volume has {negative_volume} negative values")
        
        # Validate OHLC relationships
        if all(col in df.columns for col in ['open', 'high', 'low', 'close']):
            # High should be >= Low
            invalid_high_low = (df['high'] < df['low']).sum()
            if invalid_high_low > 0:
                errors.append(f"{invalid_high_low} records have high < low")
            
            # High should be >= Open and Close
            invalid_high = ((df['high'] < df['open']) | (df['high'] < df['close'])).sum()
            if invalid_high > 0:
                errors.append(f"{invalid_high} records have high < open or close")
            
            # Low should be <= Open and Close
            invalid_low = ((df['low'] > df['open']) | (df['low'] > df['close'])).sum()
            if invalid_low > 0:
                errors.append(f"{invalid_low} records have low > open or close")
        
        # Check for duplicate records
        if 'ticker' in df.columns and 'date' in df.columns:
            duplicates = df.duplicated(subset=['ticker', 'date']).sum()
            if duplicates > 0:
                errors.append(f"{duplicates} duplicate ticker-date combinations found")
        
        is_valid = len(errors) == 0
        
        if is_valid:
            logger.info("Data quality validation passed")
        else:
            logger.warning(f"Data quality validation failed with {len(errors)} errors")
            for error in errors:
                logger.warning(f"  - {error}")
        
        return is_valid, errors

    @staticmethod
    def validate_company_info(df: pd.DataFrame) -> Tuple[bool, List[str]]:
        """
        Validate company information data quality.

        Args:
            df: DataFrame with company data

        Returns:
            Tuple of (is_valid, list of error messages)
        """
        errors = []
        
        # Check for required columns
        if 'ticker' not in df.columns:
            errors.append("Missing required column: ticker")
            return False, errors
        
        # Check for empty dataframe
        if df.empty:
            errors.append("DataFrame is empty")
            return False, errors
        
        # Check for null tickers
        null_tickers = df['ticker'].isnull().sum()
        if null_tickers > 0:
            errors.append(f"Found {null_tickers} null ticker values")
        
        # Check for duplicate tickers
        duplicates = df['ticker'].duplicated().sum()
        if duplicates > 0:
            errors.append(f"Found {duplicates} duplicate tickers")
        
        is_valid = len(errors) == 0
        
        if is_valid:
            logger.info("Company info validation passed")
        else:
            logger.warning(f"Company info validation failed with {len(errors)} errors")
        
        return is_valid, errors

    @staticmethod
    def get_data_summary(df: pd.DataFrame) -> Dict:
        """
        Get summary statistics for a DataFrame.

        Args:
            df: DataFrame to summarize

        Returns:
            Dictionary with summary statistics
        """
        summary = {
            'row_count': len(df),
            'column_count': len(df.columns),
            'columns': list(df.columns),
            'null_counts': df.isnull().sum().to_dict(),
            'memory_usage_mb': df.memory_usage(deep=True).sum() / 1024 / 1024
        }
        
        # Add date range if date column exists
        if 'date' in df.columns:
            try:
                df['date'] = pd.to_datetime(df['date'])
                summary['date_range'] = {
                    'start': str(df['date'].min()),
                    'end': str(df['date'].max())
                }
            except:
                pass
        
        return summary
