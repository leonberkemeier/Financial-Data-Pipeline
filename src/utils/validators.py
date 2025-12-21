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
            
            # Warning only for high/low vs open/close mismatches (not errors)
            invalid_high = ((df['high'] < df['open']) | (df['high'] < df['close'])).sum()
            if invalid_high > 0:
                logger.warning(f"{invalid_high} records have high < open or close (minor data quality issue)")
            
            invalid_low = ((df['low'] > df['open']) | (df['low'] > df['close'])).sum()
            if invalid_low > 0:
                logger.warning(f"{invalid_low} records have low > open or close (minor data quality issue)")
        
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

    @staticmethod
    def validate_crypto_prices(df: pd.DataFrame) -> Tuple[bool, List[str]]:
        """
        Validate cryptocurrency price data quality.

        Args:
            df: DataFrame with crypto price data

        Returns:
            Tuple of (is_valid, list of error messages)
        """
        errors = []
        
        # Check for required columns
        required_columns = ['symbol', 'date', 'price']
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
        if 'price' in df.columns:
            negative_price = (df['price'] < 0).sum()
            if negative_price > 0:
                errors.append(f"Price column has {negative_price} negative values")
        
        # Validate market cap
        if 'market_cap' in df.columns:
            negative_mc = (df['market_cap'] < 0).sum()
            if negative_mc > 0:
                errors.append(f"Market cap has {negative_mc} negative values")
        
        # Validate volume
        if 'volume' in df.columns:
            negative_volume = (df['volume'] < 0).sum()
            if negative_volume > 0:
                errors.append(f"Volume has {negative_volume} negative values")
        
        # Check for duplicate records
        if 'symbol' in df.columns and 'date' in df.columns:
            duplicates = df.duplicated(subset=['symbol', 'date']).sum()
            if duplicates > 0:
                errors.append(f"{duplicates} duplicate symbol-date combinations found")
        
        is_valid = len(errors) == 0
        
        if is_valid:
            logger.info("Crypto price validation passed")
        else:
            logger.warning(f"Crypto price validation failed with {len(errors)} errors")
            for error in errors:
                logger.warning(f"  - {error}")
        
        return is_valid, errors

    @staticmethod
    def validate_bond_prices(df: pd.DataFrame) -> Tuple[bool, List[str]]:
        """
        Validate bond price and yield data quality.

        Args:
            df: DataFrame with bond price data

        Returns:
            Tuple of (is_valid, list of error messages)
        """
        errors = []
        
        # Check for required columns
        required_columns = ['isin', 'date', 'price', 'yield']
        missing_columns = set(required_columns) - set(df.columns)
        if missing_columns:
            errors.append(f"Missing required columns: {missing_columns}")
            return False, errors
        
        # Check for empty dataframe
        if df.empty:
            errors.append("DataFrame is empty")
            return False, errors
        
        # Check for null values
        for col in required_columns:
            null_count = df[col].isnull().sum()
            if null_count > 0:
                errors.append(f"Column '{col}' has {null_count} null values")
        
        # Validate price (should be 0-200% of par value, typically 50-150%)
        if 'price' in df.columns:
            invalid_price = ((df['price'] < 0) | (df['price'] > 200)).sum()
            if invalid_price > 0:
                logger.warning(f"{invalid_price} bond prices outside typical range (0-200)")
        
        # Validate yield (should be reasonable %)
        if 'yield' in df.columns:
            negative_yield = (df['yield'] < 0).sum()
            if negative_yield > 0:
                logger.warning(f"{negative_yield} bonds with negative yields")
            
            high_yield = (df['yield'] > 50).sum()
            if high_yield > 0:
                logger.warning(f"{high_yield} bonds with yields > 50%")
        
        # Validate duration (should be positive)
        if 'duration' in df.columns:
            negative_duration = (df['duration'] < 0).sum()
            if negative_duration > 0:
                errors.append(f"Duration has {negative_duration} negative values")
        
        # Check for duplicate records
        if 'isin' in df.columns and 'date' in df.columns:
            duplicates = df.duplicated(subset=['isin', 'date']).sum()
            if duplicates > 0:
                errors.append(f"{duplicates} duplicate ISIN-date combinations found")
        
        is_valid = len(errors) == 0
        
        if is_valid:
            logger.info("Bond price validation passed")
        else:
            logger.warning(f"Bond price validation failed with {len(errors)} errors")
            for error in errors:
                logger.warning(f"  - {error}")
        
        return is_valid, errors
