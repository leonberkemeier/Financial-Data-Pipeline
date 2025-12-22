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

    @staticmethod
    def transform_crypto_dimension(crypto_df: pd.DataFrame) -> pd.DataFrame:
        """
        Transform cryptocurrency data into crypto dimension format.

        Args:
            crypto_df: DataFrame with raw crypto data

        Returns:
            DataFrame with crypto dimension attributes
        """
        logger.info("Transforming crypto dimension")
        
        # Select and rename columns
        transformed = crypto_df[[
            'symbol', 'name', 'chain', 'description'
        ]].copy()
        
        # Clean data
        transformed = transformed.fillna({
            'name': 'Unknown',
            'chain': 'Unknown',
            'description': ''
        })
        
        # Remove duplicates
        transformed = transformed.drop_duplicates(subset=['symbol'])
        
        logger.info(f"Transformed {len(transformed)} crypto asset records")
        return transformed

    @staticmethod
    def transform_crypto_prices(
        price_df: pd.DataFrame,
        crypto_mapping: Dict[str, int],
        date_mapping: Dict,
        source_id: int
    ) -> pd.DataFrame:
        """
        Transform crypto price data into fact table format.

        Args:
            price_df: DataFrame with raw crypto price data
            crypto_mapping: Dict mapping symbol to crypto_id
            date_mapping: Dict mapping date to date_id
            source_id: ID of the data source

        Returns:
            DataFrame with fact table attributes
        """
        logger.info("Transforming crypto price facts")
        
        transformed = price_df.copy()
        
        # Map foreign keys
        transformed['crypto_id'] = transformed['symbol'].map(crypto_mapping)
        
        # Handle date mapping - convert various date formats to date objects
        def get_date_id(x):
            if isinstance(x, str):
                date_obj = pd.to_datetime(x).date()
            elif isinstance(x, pd.Timestamp):
                date_obj = x.date()
            elif isinstance(x, str):
                date_obj = pd.to_datetime(x).date()
            else:
                date_obj = x  # Assume it's already a date object
            return date_mapping.get(date_obj)
        
        transformed['date_id'] = transformed['date'].apply(get_date_id)
        transformed['source_id'] = source_id
        
        # Select and rename columns for fact table
        fact_columns = {
            'crypto_id': 'crypto_id',
            'date_id': 'date_id',
            'source_id': 'source_id',
            'price': 'price',
            'market_cap': 'market_cap',
            'volume': 'trading_volume',
            'circulating_supply': 'circulating_supply',
            'total_supply': 'total_supply'
        }
        
        # Keep only columns that exist
        available_columns = {k: v for k, v in fact_columns.items() if k in transformed.columns}
        transformed = transformed.rename(columns=available_columns)
        transformed = transformed[list(available_columns.values())]
        
        # Remove rows with missing required fields
        transformed = transformed.dropna(subset=['crypto_id', 'date_id', 'price'])
        
        # Ensure integer IDs
        transformed['crypto_id'] = transformed['crypto_id'].astype(int)
        transformed['date_id'] = transformed['date_id'].astype(int)
        transformed['source_id'] = int(source_id)
        
        logger.info(f"Transformed {len(transformed)} crypto price records")
        return transformed

    @staticmethod
    def transform_issuer_dimension(issuer_df: pd.DataFrame) -> pd.DataFrame:
        """
        Transform issuer data into issuer dimension format.

        Args:
            issuer_df: DataFrame with issuer data

        Returns:
            DataFrame with issuer dimension attributes
        """
        logger.info("Transforming issuer dimension")
        
        transformed = issuer_df[[
            'issuer_name', 'issuer_type', 'country', 'credit_rating', 'sector'
        ]].copy()
        
        transformed = transformed.fillna({
            'issuer_type': 'Unknown',
            'country': 'Unknown',
            'credit_rating': 'NR',
            'sector': 'General'
        })
        
        transformed = transformed.drop_duplicates(subset=['issuer_name'])
        
        logger.info(f"Transformed {len(transformed)} issuer records")
        return transformed

    @staticmethod
    def transform_bond_dimension(
        bond_df: pd.DataFrame,
        issuer_mapping: Dict[str, int]
    ) -> pd.DataFrame:
        """
        Transform bond data into bond dimension format.

        Args:
            bond_df: DataFrame with raw bond data
            issuer_mapping: Dict mapping issuer_name to issuer_id

        Returns:
            DataFrame with bond dimension attributes
        """
        logger.info("Transforming bond dimension")
        
        transformed = bond_df[[
            'isin', 'issuer_name', 'bond_type', 'maturity_date', 'coupon_rate', 'currency', 'country'
        ]].copy()
        
        # Map issuer IDs
        transformed['issuer_id'] = transformed['issuer_name'].map(issuer_mapping)
        
        # Convert maturity_date to datetime if needed
        if 'maturity_date' in transformed.columns:
            transformed['maturity_date'] = pd.to_datetime(transformed['maturity_date'])
        
        transformed = transformed.fillna({
            'bond_type': 'Unknown',
            'coupon_rate': 0.0,
            'currency': 'USD',
            'country': 'Unknown'
        })
        
        # Select relevant columns
        transformed = transformed[[
            'isin', 'issuer_id', 'bond_type', 'maturity_date', 'coupon_rate', 'currency', 'country'
        ]]
        
        transformed = transformed.drop_duplicates(subset=['isin'])
        
        logger.info(f"Transformed {len(transformed)} bond records")
        return transformed

    @staticmethod
    def transform_bond_prices(
        price_df: pd.DataFrame,
        bond_mapping: Dict[str, int],
        date_mapping: Dict,
        source_id: int
    ) -> pd.DataFrame:
        """
        Transform bond price data into fact table format.

        Args:
            price_df: DataFrame with raw bond price data
            bond_mapping: Dict mapping ISIN to bond_id
            date_mapping: Dict mapping date to date_id
            source_id: ID of the data source

        Returns:
            DataFrame with fact table attributes
        """
        logger.info("Transforming bond price facts")
        
        transformed = price_df.copy()
        
        # Map foreign keys
        if 'isin' in transformed.columns:
            transformed['bond_id'] = transformed['isin'].map(bond_mapping)
        else:
            logger.warning("No ISIN column found in bond price data")
            return pd.DataFrame()
        
        transformed['date_id'] = transformed['date'].apply(
            lambda x: date_mapping.get(pd.to_datetime(x).date()) if isinstance(x, str) else date_mapping.get(x)
        )
        transformed['source_id'] = source_id
        
        # Select and rename columns for fact table
        fact_columns = {
            'bond_id': 'bond_id',
            'date_id': 'date_id',
            'source_id': 'source_id',
            'price': 'price',
            'yield': 'yield_percent',
            'spread': 'spread',
            'duration': 'duration'
        }
        
        available_columns = {k: v for k, v in fact_columns.items() if k in transformed.columns}
        transformed = transformed.rename(columns=available_columns)
        transformed = transformed[list(available_columns.values())]
        
        # Remove rows with missing required fields
        transformed = transformed.dropna(subset=['bond_id', 'date_id', 'price', 'yield_percent'])
        
        # Ensure integer IDs
        transformed['bond_id'] = transformed['bond_id'].astype(int)
        transformed['date_id'] = transformed['date_id'].astype(int)
        transformed['source_id'] = int(source_id)
        
        logger.info(f"Transformed {len(transformed)} bond price records")
        return transformed

    @staticmethod
    def transform_economic_indicator_dimension(indicator_df: pd.DataFrame) -> pd.DataFrame:
        """
        Transform economic indicator data into indicator dimension format.

        Args:
            indicator_df: DataFrame with raw economic indicator metadata

        Returns:
            DataFrame with indicator dimension attributes
        """
        logger.info("Transforming economic indicator dimension")
        
        transformed = indicator_df[[
            'indicator', 'indicator_name', 'category', 'unit', 'frequency'
        ]].copy()
        
        # Rename for database column names
        transformed = transformed.rename(columns={'indicator': 'indicator_code'})
        
        # Clean data
        transformed = transformed.fillna({
            'category': 'General',
            'unit': 'Number',
            'frequency': 'Unknown'
        })
        
        # Remove duplicates
        transformed = transformed.drop_duplicates(subset=['indicator_code'])
        
        logger.info(f"Transformed {len(transformed)} economic indicator records")
        return transformed

    @staticmethod
    def transform_economic_data(
        data_df: pd.DataFrame,
        indicator_mapping: Dict[str, int],
        date_mapping: Dict,
        source_id: int
    ) -> pd.DataFrame:
        """
        Transform economic indicator data into fact table format.

        Args:
            data_df: DataFrame with raw economic data
            indicator_mapping: Dict mapping indicator_code to indicator_id
            date_mapping: Dict mapping date to date_id
            source_id: ID of the data source

        Returns:
            DataFrame with fact table attributes
        """
        logger.info("Transforming economic data facts")
        
        transformed = data_df.copy()
        
        # Map foreign keys
        transformed['indicator_id'] = transformed['indicator'].map(indicator_mapping)
        
        # Handle date mapping
        def get_date_id(x):
            if isinstance(x, str):
                date_obj = pd.to_datetime(x).date()
            elif isinstance(x, pd.Timestamp):
                date_obj = x.date()
            else:
                date_obj = x
            return date_mapping.get(date_obj)
        
        transformed['date_id'] = transformed['date'].apply(get_date_id)
        transformed['source_id'] = source_id
        
        # Select and rename columns for fact table
        fact_columns = {
            'indicator_id': 'indicator_id',
            'date_id': 'date_id',
            'source_id': 'source_id',
            'value': 'value'
        }
        
        # Keep only columns that exist
        available_columns = {k: v for k, v in fact_columns.items() if k in transformed.columns}
        transformed = transformed.rename(columns=available_columns)
        transformed = transformed[list(available_columns.values())]
        
        # Remove rows with missing required fields
        transformed = transformed.dropna(subset=['indicator_id', 'date_id', 'value'])
        
        # Ensure integer IDs
        transformed['indicator_id'] = transformed['indicator_id'].astype(int)
        transformed['date_id'] = transformed['date_id'].astype(int)
        transformed['source_id'] = int(source_id)
        
        logger.info(f"Transformed {len(transformed)} economic data records")
        return transformed

    @staticmethod
    def transform_commodity_dimension(commodity_df: pd.DataFrame) -> pd.DataFrame:
        """
        Transform commodity data into commodity dimension format.

        Args:
            commodity_df: DataFrame with raw commodity metadata
                         For Yahoo: columns ['symbol', 'name', 'category', 'unit', 'exchange', 'source']
                         For FRED: columns ['series_id', 'name', 'category', 'unit', 'exchange', 'source']

        Returns:
            DataFrame with commodity dimension attributes
        """
        logger.info("Transforming commodity dimension")
        
        # Handle both Yahoo (symbol) and FRED (series_id) formats
        if 'symbol' in commodity_df.columns:
            id_column = 'symbol'
        elif 'series_id' in commodity_df.columns:
            id_column = 'series_id'
        else:
            logger.error("No symbol or series_id column found")
            return pd.DataFrame()
        
        transformed = commodity_df[[
            id_column, 'name', 'category', 'unit', 'exchange', 'source'
        ]].copy()
        
        # Rename to standard symbol column
        if id_column == 'series_id':
            transformed = transformed.rename(columns={'series_id': 'symbol'})
        
        # Clean data
        transformed = transformed.fillna({
            'category': 'Unknown',
            'unit': 'Unknown',
            'exchange': 'Unknown'
        })
        
        # Remove duplicates
        transformed = transformed.drop_duplicates(subset=['symbol'])
        
        logger.info(f"Transformed {len(transformed)} commodity records")
        return transformed

    @staticmethod
    def transform_commodity_price(
        price_df: pd.DataFrame,
        commodity_mapping: Dict[str, int],
        date_mapping: Dict,
        source_id: int
    ) -> pd.DataFrame:
        """
        Transform commodity price data into fact table format.

        Args:
            price_df: DataFrame with raw commodity price data
                     For Yahoo: columns ['symbol', 'date', 'open', 'high', 'low', 'close', 'volume', ...]
                     For FRED: columns ['series_id', 'date', 'value', ...]
            commodity_mapping: Dict mapping symbol to commodity_id
            date_mapping: Dict mapping date to date_id
            source_id: ID of the data source

        Returns:
            DataFrame with fact table attributes
        """
        logger.info("Transforming commodity price facts")
        
        transformed = price_df.copy()
        
        # Handle both Yahoo (symbol) and FRED (series_id) formats
        if 'symbol' in transformed.columns:
            id_column = 'symbol'
        elif 'series_id' in transformed.columns:
            id_column = 'series_id'
            # For FRED data, 'value' becomes 'close_price'
            if 'value' in transformed.columns and 'close' not in transformed.columns:
                transformed['close'] = transformed['value']
        else:
            logger.error("No symbol or series_id column found")
            return pd.DataFrame()
        
        # Map foreign keys
        transformed['commodity_id'] = transformed[id_column].map(commodity_mapping)
        
        # Handle date mapping
        def get_date_id(x):
            if isinstance(x, str):
                date_obj = pd.to_datetime(x).date()
            elif isinstance(x, pd.Timestamp):
                date_obj = x.date()
            else:
                date_obj = x
            return date_mapping.get(date_obj)
        
        transformed['date_id'] = transformed['date'].apply(get_date_id)
        transformed['source_id'] = source_id
        
        # Select and rename columns for fact table
        fact_columns = {
            'commodity_id': 'commodity_id',
            'date_id': 'date_id',
            'source_id': 'source_id',
            'open': 'open_price',
            'high': 'high_price',
            'low': 'low_price',
            'close': 'close_price',
            'volume': 'volume',
            'price_change': 'price_change',
            'price_change_percent': 'price_change_percent'
        }
        
        # Keep only columns that exist
        available_columns = {k: v for k, v in fact_columns.items() if k in transformed.columns}
        transformed = transformed.rename(columns=available_columns)
        transformed = transformed[list(available_columns.values())]
        
        # Remove rows with missing required fields
        transformed = transformed.dropna(subset=['commodity_id', 'date_id', 'close_price'])
        
        # Ensure integer IDs
        transformed['commodity_id'] = transformed['commodity_id'].astype(int)
        transformed['date_id'] = transformed['date_id'].astype(int)
        transformed['source_id'] = int(source_id)
        
        logger.info(f"Transformed {len(transformed)} commodity price records")
        return transformed
