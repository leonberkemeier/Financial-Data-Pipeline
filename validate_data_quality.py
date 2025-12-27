"""
Data Quality Validation Script

Comprehensive validation of all data in the financial data warehouse.
Checks for completeness, accuracy, consistency, and data quality issues.
"""

import os
from sqlalchemy import create_engine, text, func
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
from tabulate import tabulate
from dotenv import load_dotenv

from src.models import (
    DimCompany, DimCryptoAsset, DimBond, DimCommodity, DimEconomicIndicator,
    FactStockPrice, FactCryptoPrice, FactBondPrice, FactCommodityPrice,
    FactEconomicIndicator, DimDate, DimDataSource
)

load_dotenv()


class DataQualityValidator:
    """Validate data quality across all tables."""
    
    def __init__(self):
        """Initialize validator with database connection."""
        database_url = os.getenv('DATABASE_URL', 'sqlite:///financial_data.db')
        self.engine = create_engine(database_url)
        self.session = Session(self.engine)
        self.issues = []
        self.stats = {}
    
    def log_issue(self, severity: str, category: str, message: str):
        """Log a data quality issue."""
        self.issues.append({
            'severity': severity,  # CRITICAL, WARNING, INFO
            'category': category,
            'message': message
        })
    
    def validate_record_counts(self):
        """Validate record counts in all tables."""
        print("\n" + "=" * 80)
        print("📊 RECORD COUNTS VALIDATION")
        print("=" * 80)
        
        counts = {}
        
        # Dimension tables
        counts['Companies'] = self.session.query(func.count(DimCompany.company_id)).scalar()
        counts['Crypto Assets'] = self.session.query(func.count(DimCryptoAsset.crypto_id)).scalar()
        counts['Bonds'] = self.session.query(func.count(DimBond.bond_id)).scalar()
        counts['Commodities'] = self.session.query(func.count(DimCommodity.commodity_id)).scalar()
        counts['Economic Indicators'] = self.session.query(func.count(DimEconomicIndicator.indicator_id)).scalar()
        counts['Dates'] = self.session.query(func.count(DimDate.date_id)).scalar()
        counts['Data Sources'] = self.session.query(func.count(DimDataSource.source_id)).scalar()
        
        # Fact tables
        counts['Stock Prices'] = self.session.query(func.count(FactStockPrice.price_id)).scalar()
        counts['Crypto Prices'] = self.session.query(func.count(FactCryptoPrice.crypto_price_id)).scalar()
        counts['Bond Prices'] = self.session.query(func.count(FactBondPrice.bond_price_id)).scalar()
        counts['Commodity Prices'] = self.session.query(func.count(FactCommodityPrice.commodity_price_id)).scalar()
        counts['Economic Data'] = self.session.query(func.count(FactEconomicIndicator.economic_data_id)).scalar()
        
        # Print table
        table = [[k, v] for k, v in counts.items()]
        print(tabulate(table, headers=['Table', 'Count'], tablefmt='grid'))
        
        # Validate
        if counts['Stock Prices'] == 0 and counts['Crypto Prices'] == 0 and counts['Commodity Prices'] == 0:
            self.log_issue('CRITICAL', 'Completeness', 'No price data found in any fact tables')
        
        self.stats['record_counts'] = counts
        return counts
    
    def validate_null_values(self):
        """Check for NULL values in critical fields."""
        print("\n" + "=" * 80)
        print("🔍 NULL VALUE VALIDATION")
        print("=" * 80)
        
        null_checks = []
        
        # Stock prices - close_price should not be NULL
        null_stocks = self.session.query(func.count(FactStockPrice.price_id))\
            .filter(FactStockPrice.close_price == None).scalar()
        null_checks.append(('Stock Prices', 'close_price', null_stocks))
        
        # Crypto prices - price should not be NULL
        null_crypto = self.session.query(func.count(FactCryptoPrice.crypto_price_id))\
            .filter(FactCryptoPrice.price == None).scalar()
        null_checks.append(('Crypto Prices', 'price', null_crypto))
        
        # Commodity prices - close_price should not be NULL
        null_commodities = self.session.query(func.count(FactCommodityPrice.commodity_price_id))\
            .filter(FactCommodityPrice.close_price == None).scalar()
        null_checks.append(('Commodity Prices', 'close_price', null_commodities))
        
        # Bond prices - yield_percent should not be NULL
        null_bonds = self.session.query(func.count(FactBondPrice.bond_price_id))\
            .filter(FactBondPrice.yield_percent == None).scalar()
        null_checks.append(('Bond Prices', 'yield_percent', null_bonds))
        
        # Economic data - value should not be NULL
        null_economic = self.session.query(func.count(FactEconomicIndicator.economic_data_id))\
            .filter(FactEconomicIndicator.value == None).scalar()
        null_checks.append(('Economic Data', 'value', null_economic))
        
        # Print results
        table = [[table, field, count, '✅ PASS' if count == 0 else '❌ FAIL'] 
                 for table, field, count in null_checks]
        print(tabulate(table, headers=['Table', 'Field', 'NULL Count', 'Status'], tablefmt='grid'))
        
        # Log issues
        for table, field, count in null_checks:
            if count > 0:
                self.log_issue('CRITICAL', 'Data Quality', 
                             f'{table}.{field} has {count} NULL values')
        
        return null_checks
    
    def validate_price_ranges(self):
        """Validate that prices are within reasonable ranges."""
        print("\n" + "=" * 80)
        print("💰 PRICE RANGE VALIDATION")
        print("=" * 80)
        
        issues = []
        
        # Stock prices - negative prices
        negative_stocks = self.session.query(func.count(FactStockPrice.price_id))\
            .filter(FactStockPrice.close_price < 0).scalar()
        issues.append(('Stock Prices', 'Negative', negative_stocks))
        
        # Stock prices - unreasonably high (> $100,000)
        extreme_stocks = self.session.query(func.count(FactStockPrice.price_id))\
            .filter(FactStockPrice.close_price > 100000).scalar()
        issues.append(('Stock Prices', 'Extreme High', extreme_stocks))
        
        # Crypto prices - negative
        negative_crypto = self.session.query(func.count(FactCryptoPrice.crypto_price_id))\
            .filter(FactCryptoPrice.price < 0).scalar()
        issues.append(('Crypto Prices', 'Negative', negative_crypto))
        
        # Commodity prices - negative
        negative_commodities = self.session.query(func.count(FactCommodityPrice.commodity_price_id))\
            .filter(FactCommodityPrice.close_price < 0).scalar()
        issues.append(('Commodity Prices', 'Negative', negative_commodities))
        
        # Bond yields - negative (some can be negative, but check for extreme values)
        extreme_yields = self.session.query(func.count(FactBondPrice.bond_price_id))\
            .filter(FactBondPrice.yield_percent < -10).scalar()
        issues.append(('Bond Yields', 'Extreme Negative', extreme_yields))
        
        extreme_high_yields = self.session.query(func.count(FactBondPrice.bond_price_id))\
            .filter(FactBondPrice.yield_percent > 50).scalar()
        issues.append(('Bond Yields', 'Extreme High', extreme_high_yields))
        
        # Print results
        table = [[table, issue_type, count, '✅ PASS' if count == 0 else '⚠️  WARNING']
                 for table, issue_type, count in issues]
        print(tabulate(table, headers=['Table', 'Issue Type', 'Count', 'Status'], tablefmt='grid'))
        
        # Log issues
        for table, issue_type, count in issues:
            if count > 0:
                self.log_issue('WARNING', 'Data Quality',
                             f'{table} has {count} records with {issue_type} prices')
        
        return issues
    
    def validate_ohlc_relationships(self):
        """Validate OHLC (Open-High-Low-Close) relationships.
        
        Uses epsilon tolerance (0.0001) to handle floating-point precision issues.
        """
        print("\n" + "=" * 80)
        print("📈 OHLC RELATIONSHIP VALIDATION")
        print("=" * 80)
        
        issues = []
        epsilon = 0.0001  # Tolerance for floating-point comparison
        
        # Stock prices - High >= Low (with epsilon tolerance)
        invalid_stocks = self.session.execute(text(f"""
            SELECT COUNT(*)
            FROM fact_stock_price
            WHERE high_price IS NOT NULL AND low_price IS NOT NULL
            AND high_price < (low_price - {epsilon})
        """)).scalar()
        issues.append(('Stock Prices', 'High < Low', invalid_stocks))
        
        # Stock prices - Close within High/Low range (with epsilon tolerance)
        invalid_close_stocks = self.session.execute(text(f"""
            SELECT COUNT(*)
            FROM fact_stock_price
            WHERE close_price IS NOT NULL AND high_price IS NOT NULL AND low_price IS NOT NULL
            AND (close_price > (high_price + {epsilon}) OR close_price < (low_price - {epsilon}))
        """)).scalar()
        issues.append(('Stock Prices', 'Close outside High/Low', invalid_close_stocks))
        
        # Commodity prices - same checks
        invalid_commodities = self.session.execute(text(f"""
            SELECT COUNT(*)
            FROM fact_commodity_price
            WHERE high_price IS NOT NULL AND low_price IS NOT NULL
            AND high_price < (low_price - {epsilon})
        """)).scalar()
        issues.append(('Commodity Prices', 'High < Low', invalid_commodities))
        
        invalid_close_commodities = self.session.execute(text(f"""
            SELECT COUNT(*)
            FROM fact_commodity_price
            WHERE close_price IS NOT NULL AND high_price IS NOT NULL AND low_price IS NOT NULL
            AND (close_price > (high_price + {epsilon}) OR close_price < (low_price - {epsilon}))
        """)).scalar()
        issues.append(('Commodity Prices', 'Close outside High/Low', invalid_close_commodities))
        
        # Print results
        table = [[table, issue_type, count, '✅ PASS' if count == 0 else '❌ FAIL']
                 for table, issue_type, count in issues]
        print(tabulate(table, headers=['Table', 'Issue Type', 'Count', 'Status'], tablefmt='grid'))
        
        # Log issues
        for table, issue_type, count in issues:
            if count > 0:
                self.log_issue('CRITICAL', 'Data Integrity',
                             f'{table} has {count} records with {issue_type}')
        
        return issues
    
    def validate_duplicates(self):
        """Check for duplicate records."""
        print("\n" + "=" * 80)
        print("🔁 DUPLICATE RECORD VALIDATION")
        print("=" * 80)
        
        duplicates = []
        
        # Stock prices - same company, date, source
        dup_stocks = self.session.execute(text("""
            SELECT company_id, date_id, source_id, COUNT(*) as count
            FROM fact_stock_price
            GROUP BY company_id, date_id, source_id
            HAVING COUNT(*) > 1
        """)).fetchall()
        duplicates.append(('Stock Prices', len(dup_stocks)))
        
        # Crypto prices
        dup_crypto = self.session.execute(text("""
            SELECT crypto_id, date_id, source_id, COUNT(*) as count
            FROM fact_crypto_price
            GROUP BY crypto_id, date_id, source_id
            HAVING COUNT(*) > 1
        """)).fetchall()
        duplicates.append(('Crypto Prices', len(dup_crypto)))
        
        # Commodity prices
        dup_commodities = self.session.execute(text("""
            SELECT commodity_id, date_id, source_id, COUNT(*) as count
            FROM fact_commodity_price
            GROUP BY commodity_id, date_id, source_id
            HAVING COUNT(*) > 1
        """)).fetchall()
        duplicates.append(('Commodity Prices', len(dup_commodities)))
        
        # Bond prices
        dup_bonds = self.session.execute(text("""
            SELECT bond_id, date_id, source_id, COUNT(*) as count
            FROM fact_bond_price
            GROUP BY bond_id, date_id, source_id
            HAVING COUNT(*) > 1
        """)).fetchall()
        duplicates.append(('Bond Prices', len(dup_bonds)))
        
        # Economic data
        dup_economic = self.session.execute(text("""
            SELECT indicator_id, date_id, source_id, COUNT(*) as count
            FROM fact_economic_indicator
            GROUP BY indicator_id, date_id, source_id
            HAVING COUNT(*) > 1
        """)).fetchall()
        duplicates.append(('Economic Data', len(dup_economic)))
        
        # Print results
        table = [[table, count, '✅ PASS' if count == 0 else '⚠️  WARNING']
                 for table, count in duplicates]
        print(tabulate(table, headers=['Table', 'Duplicate Groups', 'Status'], tablefmt='grid'))
        
        # Log issues
        for table, count in duplicates:
            if count > 0:
                self.log_issue('WARNING', 'Data Integrity',
                             f'{table} has {count} duplicate record groups')
        
        return duplicates
    
    def validate_data_freshness(self):
        """Check how recent the data is."""
        print("\n" + "=" * 80)
        print("🕒 DATA FRESHNESS VALIDATION")
        print("=" * 80)
        
        today = datetime.now().date()
        freshness = []
        
        # Get latest dates for each data type
        latest_stock = self.session.execute(text("""
            SELECT MAX(d.date) FROM fact_stock_price f
            JOIN dim_date d ON f.date_id = d.date_id
        """)).scalar()
        
        latest_crypto = self.session.execute(text("""
            SELECT MAX(d.date) FROM fact_crypto_price f
            JOIN dim_date d ON f.date_id = d.date_id
        """)).scalar()
        
        latest_commodity = self.session.execute(text("""
            SELECT MAX(d.date) FROM fact_commodity_price f
            JOIN dim_date d ON f.date_id = d.date_id
        """)).scalar()
        
        latest_bond = self.session.execute(text("""
            SELECT MAX(d.date) FROM fact_bond_price f
            JOIN dim_date d ON f.date_id = d.date_id
        """)).scalar()
        
        latest_economic = self.session.execute(text("""
            SELECT MAX(d.date) FROM fact_economic_indicator f
            JOIN dim_date d ON f.date_id = d.date_id
        """)).scalar()
        
        # Calculate days old
        for name, latest_date in [
            ('Stocks', latest_stock),
            ('Crypto', latest_crypto),
            ('Commodities', latest_commodity),
            ('Bonds', latest_bond),
            ('Economic', latest_economic)
        ]:
            if latest_date:
                # Convert string to date if necessary
                if isinstance(latest_date, str):
                    latest_date = datetime.strptime(latest_date, '%Y-%m-%d').date()
                days_old = (today - latest_date).days
                status = '✅ FRESH' if days_old <= 7 else '⚠️  STALE' if days_old <= 30 else '❌ OLD'
                freshness.append((name, latest_date, days_old, status))
                
                if days_old > 30:
                    self.log_issue('WARNING', 'Data Freshness',
                                 f'{name} data is {days_old} days old (last: {latest_date})')
            else:
                freshness.append((name, None, None, '❌ NO DATA'))
                self.log_issue('CRITICAL', 'Completeness', f'No {name} data found')
        
        # Print results
        print(tabulate(freshness, headers=['Data Type', 'Latest Date', 'Days Old', 'Status'], tablefmt='grid'))
        
        return freshness
    
    def validate_data_sources(self):
        """Validate data sources are properly recorded."""
        print("\n" + "=" * 80)
        print("📁 DATA SOURCE VALIDATION")
        print("=" * 80)
        
        sources = self.session.query(DimDataSource.source_name).all()
        source_names = [s[0] for s in sources]
        
        expected_sources = ['yahoo_finance', 'coingecko', 'fred', 'alpha_vantage', 'sec_edgar']
        
        table = []
        for expected in expected_sources:
            present = expected in source_names
            table.append((expected, '✅ Present' if present else '⚠️  Missing'))
            if not present:
                self.log_issue('INFO', 'Configuration',
                             f'Data source "{expected}" not found in database')
        
        print(tabulate(table, headers=['Expected Source', 'Status'], tablefmt='grid'))
        
        return source_names
    
    def print_summary(self):
        """Print validation summary."""
        print("\n" + "=" * 80)
        print("📋 VALIDATION SUMMARY")
        print("=" * 80)
        
        critical = [i for i in self.issues if i['severity'] == 'CRITICAL']
        warnings = [i for i in self.issues if i['severity'] == 'WARNING']
        info = [i for i in self.issues if i['severity'] == 'INFO']
        
        print(f"\n✅ Total Validations: {len(self.issues) if self.issues else 'All checks passed'}")
        print(f"❌ CRITICAL Issues: {len(critical)}")
        print(f"⚠️  WARNINGS: {len(warnings)}")
        print(f"ℹ️  INFO: {len(info)}")
        
        if critical:
            print("\n🚨 CRITICAL ISSUES:")
            for issue in critical:
                print(f"  - [{issue['category']}] {issue['message']}")
        
        if warnings:
            print("\n⚠️  WARNINGS:")
            for issue in warnings:
                print(f"  - [{issue['category']}] {issue['message']}")
        
        if info:
            print("\nℹ️  INFO:")
            for issue in info:
                print(f"  - [{issue['category']}] {issue['message']}")
        
        print("\n" + "=" * 80)
        if not critical and not warnings:
            print("🎉 DATA QUALITY: EXCELLENT - No critical issues or warnings found!")
        elif not critical:
            print("✅ DATA QUALITY: GOOD - No critical issues, but some warnings present")
        else:
            print("❌ DATA QUALITY: NEEDS ATTENTION - Critical issues found")
        print("=" * 80 + "\n")
    
    def run_all_validations(self):
        """Run all validation checks."""
        print("\n" + "🔍" * 40)
        print("DATA QUALITY VALIDATION REPORT")
        print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("🔍" * 40)
        
        self.validate_record_counts()
        self.validate_null_values()
        self.validate_price_ranges()
        self.validate_ohlc_relationships()
        self.validate_duplicates()
        self.validate_data_freshness()
        self.validate_data_sources()
        self.print_summary()
        
        return self.issues
    
    def __del__(self):
        """Cleanup database connection."""
        self.session.close()


def main():
    """Run data quality validation."""
    validator = DataQualityValidator()
    issues = validator.run_all_validations()
    
    # Exit with error code if critical issues found
    critical_issues = [i for i in issues if i['severity'] == 'CRITICAL']
    if critical_issues:
        exit(1)


if __name__ == "__main__":
    main()
