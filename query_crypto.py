"""Query and analyze crypto data from the database."""
from sqlalchemy import func, desc
from src.models.base import SessionLocal
from src.models import (
    FactCryptoPrice, DimCryptoAsset, DimDate, DimDataSource
)
import pandas as pd


def get_crypto_overview():
    """Get a comprehensive overview of crypto data."""
    db = SessionLocal()
    
    try:
        print("=" * 80)
        print("CRYPTO DATA OVERVIEW")
        print("=" * 80)
        
        # 1. Basic Statistics
        print("\n📊 BASIC STATISTICS")
        print("-" * 80)
        
        total_records = db.query(func.count(FactCryptoPrice.crypto_price_id)).scalar()
        print(f"Total price records: {total_records:,}")
        
        total_assets = db.query(func.count(DimCryptoAsset.crypto_id)).scalar()
        print(f"Total crypto assets tracked: {total_assets}")
        
        # Date range
        date_range = db.query(
            func.min(DimDate.date).label('earliest'),
            func.max(DimDate.date).label('latest')
        ).join(
            FactCryptoPrice,
            DimDate.date_id == FactCryptoPrice.date_id
        ).first()
        
        print(f"Date range: {date_range.earliest} to {date_range.latest}")
        
        # 2. Assets Breakdown
        print("\n💰 ASSETS BREAKDOWN")
        print("-" * 80)
        
        assets = db.query(
            DimCryptoAsset.symbol,
            DimCryptoAsset.name,
            DimCryptoAsset.chain,
            func.count(FactCryptoPrice.crypto_price_id).label('record_count')
        ).join(
            FactCryptoPrice,
            DimCryptoAsset.crypto_id == FactCryptoPrice.crypto_id
        ).group_by(
            DimCryptoAsset.crypto_id
        ).all()
        
        for asset in assets:
            print(f"{asset.symbol:6} - {asset.name:20} ({asset.chain:15}) - {asset.record_count:4} records")
        
        # 3. Latest Prices
        print("\n💵 LATEST PRICES")
        print("-" * 80)
        
        latest_prices = db.query(
            DimCryptoAsset.symbol,
            DimCryptoAsset.name,
            DimDate.date,
            FactCryptoPrice.price,
            FactCryptoPrice.market_cap,
            FactCryptoPrice.trading_volume
        ).join(
            DimCryptoAsset,
            FactCryptoPrice.crypto_id == DimCryptoAsset.crypto_id
        ).join(
            DimDate,
            FactCryptoPrice.date_id == DimDate.date_id
        ).order_by(
            DimCryptoAsset.symbol,
            DimDate.date.desc()
        ).distinct(
            DimCryptoAsset.symbol
        ).all()
        
        print(f"{'Symbol':<8} {'Price':>15} {'Market Cap':>20} {'24h Volume':>20} {'Date':<12}")
        print("-" * 80)
        for price in latest_prices:
            print(f"{price.symbol:<8} ${price.price:>14,.2f} ${price.market_cap:>19,.0f} ${price.trading_volume:>19,.0f} {price.date}")
        
        # 4. Price Changes
        print("\n📈 PRICE CHANGES (First vs Latest)")
        print("-" * 80)
        
        for asset in assets:
            # Get first and last price
            prices = db.query(
                FactCryptoPrice.price,
                DimDate.date
            ).join(
                DimCryptoAsset,
                FactCryptoPrice.crypto_id == DimCryptoAsset.crypto_id
            ).join(
                DimDate,
                FactCryptoPrice.date_id == DimDate.date_id
            ).filter(
                DimCryptoAsset.symbol == asset.symbol
            ).order_by(
                DimDate.date
            ).all()
            
            if len(prices) >= 2:
                first_price = prices[0].price
                last_price = prices[-1].price
                change = last_price - first_price
                change_pct = (change / first_price * 100) if first_price > 0 else 0
                
                arrow = "🟢" if change >= 0 else "🔴"
                print(f"{arrow} {asset.symbol:6} ${first_price:>10,.2f} → ${last_price:>10,.2f} ({change_pct:>+6.2f}%)")
        
        # 5. Data Sources
        print("\n📡 DATA SOURCES")
        print("-" * 80)
        
        sources = db.query(
            DimDataSource.source_name,
            func.count(FactCryptoPrice.crypto_price_id).label('record_count')
        ).join(
            FactCryptoPrice,
            DimDataSource.source_id == FactCryptoPrice.source_id
        ).group_by(
            DimDataSource.source_id
        ).all()
        
        for source in sources:
            print(f"{source.source_name:<20} - {source.record_count:,} records")
        
        # 6. Recent Activity
        print("\n🕐 MOST RECENT RECORDS (Last 10)")
        print("-" * 80)
        
        recent = db.query(
            DimCryptoAsset.symbol,
            DimDate.date,
            FactCryptoPrice.price,
            FactCryptoPrice.created_at
        ).join(
            DimCryptoAsset,
            FactCryptoPrice.crypto_id == DimCryptoAsset.crypto_id
        ).join(
            DimDate,
            FactCryptoPrice.date_id == DimDate.date_id
        ).order_by(
            FactCryptoPrice.created_at.desc()
        ).limit(10).all()
        
        print(f"{'Symbol':<8} {'Date':<12} {'Price':>15} {'Created At':<20}")
        print("-" * 80)
        for rec in recent:
            print(f"{rec.symbol:<8} {rec.date} ${rec.price:>14,.2f} {rec.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
        
        print("\n" + "=" * 80)
        
    finally:
        db.close()


def get_crypto_timeseries(symbol: str = "BTC", days: int = 30):
    """Get time series data for a specific crypto."""
    db = SessionLocal()
    
    try:
        print(f"\n📊 TIME SERIES: {symbol} (Last {days} days)")
        print("=" * 80)
        
        results = db.query(
            DimDate.date,
            FactCryptoPrice.price,
            FactCryptoPrice.market_cap,
            FactCryptoPrice.trading_volume
        ).join(
            DimCryptoAsset,
            FactCryptoPrice.crypto_id == DimCryptoAsset.crypto_id
        ).join(
            DimDate,
            FactCryptoPrice.date_id == DimDate.date_id
        ).filter(
            DimCryptoAsset.symbol == symbol
        ).order_by(
            DimDate.date.desc()
        ).limit(days).all()
        
        if not results:
            print(f"No data found for {symbol}")
            return
        
        # Convert to DataFrame for better display
        df = pd.DataFrame([
            {
                'Date': r.date,
                'Price': r.price,
                'Market Cap': r.market_cap,
                'Volume': r.trading_volume
            }
            for r in results
        ])
        # Convert 'Price' column to numeric for calculations
        df['Price'] = pd.to_numeric(df['Price'])
        
        # Calculate statistics
        print(f"\n{'Metric':<20} {'Value':>15}")
        print("-" * 40)
        print(f"{'Current Price':<20} ${df['Price'].iloc[0]:>14,.2f}")
        print(f"{'Avg Price':<20} ${df['Price'].mean():>14,.2f}")
        print(f"{'High':<20} ${df['Price'].max():>14,.2f}")
        print(f"{'Low':<20} ${df['Price'].min():>14,.2f}")
        print(f"{'Volatility (StdDev)':<20} ${df['Price'].std():>14,.2f}")
        
        # Show data table
        print(f"\n{'Date':<12} {'Price':>15} {'Market Cap':>20} {'Volume':>20}")
        print("-" * 70)
        for _, row in df.iterrows():
            print(f"{row['Date']} ${row['Price']:>14,.2f} ${row['Market Cap']:>19,.0f} ${row['Volume']:>19,.0f}")
        
        print("=" * 80)
        
    finally:
        db.close()


def compare_cryptos(symbols: list = None):
    """Compare multiple cryptocurrencies."""
    if symbols is None:
        symbols = ['BTC', 'ETH', 'ADA']
    
    db = SessionLocal()
    
    try:
        print(f"\n🔄 CRYPTO COMPARISON: {', '.join(symbols)}")
        print("=" * 80)
        
        for symbol in symbols:
            latest = db.query(
                DimCryptoAsset.symbol,
                DimCryptoAsset.name,
                DimDate.date,
                FactCryptoPrice.price,
                FactCryptoPrice.market_cap
            ).join(
                DimCryptoAsset,
                FactCryptoPrice.crypto_id == DimCryptoAsset.crypto_id
            ).join(
                DimDate,
                FactCryptoPrice.date_id == DimDate.date_id
            ).filter(
                DimCryptoAsset.symbol == symbol
            ).order_by(
                DimDate.date.desc()
            ).first()
            
            if latest:
                print(f"\n{latest.symbol} - {latest.name}")
                print(f"  Price:      ${latest.price:>15,.2f}")
                print(f"  Market Cap: ${latest.market_cap:>15,.0f}")
                print(f"  As of:      {latest.date}")
        
        print("\n" + "=" * 80)
        
    finally:
        db.close()


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "overview":
            get_crypto_overview()
        elif command == "timeseries":
            symbol = sys.argv[2] if len(sys.argv) > 2 else "BTC"
            days = int(sys.argv[3]) if len(sys.argv) > 3 else 30
            get_crypto_timeseries(symbol, days)
        elif command == "compare":
            symbols = sys.argv[2:] if len(sys.argv) > 2 else ['BTC', 'ETH', 'ADA']
            compare_cryptos(symbols)
        else:
            print("Usage:")
            print("  python query_crypto.py overview")
            print("  python query_crypto.py timeseries BTC 30")
            print("  python query_crypto.py compare BTC ETH ADA")
    else:
        # Run all by default
        get_crypto_overview()
        get_crypto_timeseries("BTC", 10)
        compare_cryptos()
