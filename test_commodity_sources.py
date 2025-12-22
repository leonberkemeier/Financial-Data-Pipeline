"""
Test and compare commodity data from Yahoo Finance and FRED.
"""

from src.extractors.yahoo_commodity import YahooCommodityExtractor
from src.extractors.fred_commodity import FREDCommodityExtractor
from dotenv import load_dotenv
import pandas as pd

load_dotenv()


def test_yahoo_commodities():
    """Test Yahoo Finance commodity extraction."""
    print("=" * 60)
    print("YAHOO FINANCE COMMODITY EXTRACTION")
    print("=" * 60)
    
    extractor = YahooCommodityExtractor()
    
    # Test with major commodities
    symbols = ['CL=F', 'GC=F', 'SI=F', 'NG=F', 'HG=F']
    
    print(f"\nTesting {len(symbols)} commodities over 30 days...")
    df = extractor.extract_commodity_prices(symbols, days=30)
    
    if df.empty:
        print("❌ No data extracted from Yahoo Finance")
        return None
    
    print(f"\n✅ SUCCESS: Extracted {len(df)} records")
    print(f"   Date range: {df['date'].min()} to {df['date'].max()}")
    print(f"   Commodities: {df['symbol'].nunique()}")
    
    # Show latest prices
    print("\n📊 Latest Prices (Yahoo Finance):")
    latest = df.sort_values('date').groupby('symbol').tail(1)
    for _, row in latest.iterrows():
        name = extractor.COMMODITIES[row['symbol']]['name']
        print(f"   {name:20s} ({row['symbol']:6s}): ${row['close']:8.2f}  "
              f"Change: {row['price_change_percent']:+.2f}%")
    
    return df


def test_fred_commodities():
    """Test FRED commodity extraction."""
    print("\n" + "=" * 60)
    print("FRED COMMODITY EXTRACTION")
    print("=" * 60)
    
    extractor = FREDCommodityExtractor()
    
    # Test with commodities available on FRED
    series = ['DCOILWTICO', 'DCOILBRENTEU', 'DHHNGSP']
    
    print(f"\nTesting {len(series)} series over 30 days...")
    df = extractor.extract_commodity_prices(series, days=30)
    
    if df.empty:
        print("❌ No data extracted from FRED")
        return None
    
    print(f"\n✅ SUCCESS: Extracted {len(df)} records")
    print(f"   Date range: {df['date'].min()} to {df['date'].max()}")
    print(f"   Series: {df['series_id'].nunique()}")
    
    # Show latest prices
    print("\n📊 Latest Prices (FRED):")
    latest = df.sort_values('date').groupby('series_id').tail(1)
    for _, row in latest.iterrows():
        name = extractor.COMMODITIES[row['series_id']]['name']
        print(f"   {name:20s} ({row['series_id']:15s}): ${row['value']:8.2f}  "
              f"Change: {row['price_change_percent']:+.2f}%")
    
    return df


def compare_oil_prices():
    """Compare WTI oil prices from both sources."""
    print("\n" + "=" * 60)
    print("COMPARISON: WTI CRUDE OIL (Yahoo vs FRED)")
    print("=" * 60)
    
    # Yahoo Finance
    yahoo_ext = YahooCommodityExtractor()
    yahoo_df = yahoo_ext.extract_commodity_prices(['CL=F'], days=30)
    
    # FRED
    fred_ext = FREDCommodityExtractor()
    fred_df = fred_ext.extract_commodity_prices(['DCOILWTICO'], days=30)
    
    if yahoo_df.empty or fred_df.empty:
        print("⚠️  Could not fetch data from both sources")
        return
    
    print(f"\n📊 WTI Crude Oil Comparison:")
    print(f"   Yahoo Finance: {len(yahoo_df)} records (futures contract)")
    print(f"   FRED:          {len(fred_df)} records (spot price)")
    
    # Find common dates
    yahoo_dates = set(yahoo_df['date'])
    fred_dates = set(fred_df['date'])
    common_dates = yahoo_dates & fred_dates
    
    if common_dates:
        print(f"\n   Common dates: {len(common_dates)}")
        print("\n   Date         Yahoo      FRED    Difference")
        print("   " + "-" * 50)
        
        for date in sorted(common_dates)[-5:]:  # Last 5 common dates
            yahoo_price = yahoo_df[yahoo_df['date'] == date]['close'].values[0]
            fred_price = fred_df[fred_df['date'] == date]['value'].values[0]
            diff = yahoo_price - fred_price
            print(f"   {date}   ${yahoo_price:7.2f}   ${fred_price:7.2f}   ${diff:+7.2f}")


def main():
    """Run all tests."""
    print("\n🧪 COMMODITY DATA SOURCE TESTING\n")
    
    # Test Yahoo Finance
    yahoo_data = test_yahoo_commodities()
    
    # Test FRED
    fred_data = test_fred_commodities()
    
    # Compare oil prices
    compare_oil_prices()
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    if yahoo_data is not None:
        print(f"✅ Yahoo Finance: {len(yahoo_data)} records across {yahoo_data['symbol'].nunique()} commodities")
    else:
        print("❌ Yahoo Finance: Failed")
    
    if fred_data is not None:
        print(f"✅ FRED:          {len(fred_data)} records across {fred_data['series_id'].nunique()} series")
    else:
        print("❌ FRED:          Failed")
    
    print("\n💡 Recommendation: Use Yahoo Finance for real-time futures data")
    print("                   Use FRED for official spot/reference prices")
    print()


if __name__ == "__main__":
    main()
