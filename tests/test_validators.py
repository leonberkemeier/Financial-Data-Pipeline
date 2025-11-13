"""Unit tests for data validators."""
import pytest
import pandas as pd
from src.utils.validators import DataQualityValidator


class TestDataQualityValidator:
    """Test data quality validation."""

    def test_validate_stock_prices_valid(self):
        """Test validation with valid data."""
        df = pd.DataFrame({
            'ticker': ['AAPL', 'GOOGL'],
            'date': ['2024-01-01', '2024-01-01'],
            'open': [150.0, 2800.0],
            'high': [155.0, 2850.0],
            'low': [149.0, 2790.0],
            'close': [152.0, 2820.0],
            'volume': [1000000, 500000]
        })
        
        validator = DataQualityValidator()
        is_valid, errors = validator.validate_stock_prices(df)
        
        assert is_valid
        assert len(errors) == 0

    def test_validate_stock_prices_missing_columns(self):
        """Test validation with missing required columns."""
        df = pd.DataFrame({
            'ticker': ['AAPL'],
            'open': [150.0]
        })
        
        validator = DataQualityValidator()
        is_valid, errors = validator.validate_stock_prices(df)
        
        assert not is_valid
        assert len(errors) > 0

    def test_validate_stock_prices_negative_price(self):
        """Test validation with negative prices."""
        df = pd.DataFrame({
            'ticker': ['AAPL'],
            'date': ['2024-01-01'],
            'open': [150.0],
            'high': [155.0],
            'low': [-10.0],  # Invalid
            'close': [152.0]
        })
        
        validator = DataQualityValidator()
        is_valid, errors = validator.validate_stock_prices(df)
        
        assert not is_valid
        assert any('negative' in str(e).lower() for e in errors)

    def test_validate_stock_prices_invalid_ohlc(self):
        """Test validation with invalid OHLC relationships."""
        df = pd.DataFrame({
            'ticker': ['AAPL'],
            'date': ['2024-01-01'],
            'open': [150.0],
            'high': [145.0],  # Invalid: high < low
            'low': [149.0],
            'close': [152.0]
        })
        
        validator = DataQualityValidator()
        is_valid, errors = validator.validate_stock_prices(df)
        
        assert not is_valid
        assert any('high' in str(e).lower() for e in errors)

    def test_validate_company_info_valid(self):
        """Test company info validation with valid data."""
        df = pd.DataFrame({
            'ticker': ['AAPL', 'GOOGL'],
            'company_name': ['Apple Inc.', 'Alphabet Inc.']
        })
        
        validator = DataQualityValidator()
        is_valid, errors = validator.validate_company_info(df)
        
        assert is_valid
        assert len(errors) == 0

    def test_validate_company_info_duplicates(self):
        """Test company info validation with duplicates."""
        df = pd.DataFrame({
            'ticker': ['AAPL', 'AAPL'],  # Duplicate
            'company_name': ['Apple Inc.', 'Apple Inc.']
        })
        
        validator = DataQualityValidator()
        is_valid, errors = validator.validate_company_info(df)
        
        assert not is_valid
        assert any('duplicate' in str(e).lower() for e in errors)

    def test_get_data_summary(self):
        """Test data summary generation."""
        df = pd.DataFrame({
            'ticker': ['AAPL', 'GOOGL'],
            'date': ['2024-01-01', '2024-01-02'],
            'close': [150.0, 2800.0]
        })
        
        validator = DataQualityValidator()
        summary = validator.get_data_summary(df)
        
        assert summary['row_count'] == 2
        assert summary['column_count'] == 3
        assert 'ticker' in summary['columns']
        assert 'date_range' in summary
