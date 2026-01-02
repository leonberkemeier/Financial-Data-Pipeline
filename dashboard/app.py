"""Web dashboard for viewing financial data."""
from flask import Flask, render_template, jsonify, request
from sqlalchemy import create_engine, text
import pandas as pd
import plotly.graph_objs as go
import plotly.express as px
from datetime import datetime, timedelta
import sys
import os

# Add parent directory to path for imports
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)

# Import config
from config.config import DATABASE_URL, OLLAMA_HOST, RAG_LLM_MODEL, RAG_EMBEDDING_MODEL, RAG_CHROMA_PATH

# Import RAG system
try:
    from rag_demo import RAGSystem
    RAG_AVAILABLE = True
except Exception as e:
    RAG_AVAILABLE = False
    print(f"Warning: RAG system not available: {e}")

app = Flask(__name__)

# Use absolute path for database
if DATABASE_URL.startswith('sqlite:///'):
    # Convert relative sqlite path to absolute
    db_path = DATABASE_URL.replace('sqlite:///', '')
    if not db_path.startswith('/'):
        # It's a relative path, make it absolute from parent directory
        db_path = os.path.join(parent_dir, db_path.lstrip('./'))
        DATABASE_URL = f'sqlite:///{db_path}'

engine = create_engine(DATABASE_URL)
print(f"Connecting to database: {DATABASE_URL}")


def get_db_connection():
    """Get database connection."""
    return engine.connect()


@app.route('/')
def index():
    """Main dashboard page."""
    conn = get_db_connection()
    
    # Get summary stats for all asset types
    stock_stats = conn.execute(text("""
        SELECT 
            COUNT(DISTINCT c.ticker) as total_companies,
            COUNT(*) as total_records,
            MAX(d.date) as latest_date
        FROM fact_stock_price f
        JOIN dim_company c ON f.company_id = c.company_id
        JOIN dim_date d ON f.date_id = d.date_id
    """)).fetchone()
    
    crypto_stats = conn.execute(text("""
        SELECT 
            COUNT(DISTINCT ca.symbol) as total_cryptos,
            COUNT(*) as total_records,
            MAX(d.date) as latest_date
        FROM fact_crypto_price f
        JOIN dim_crypto_asset ca ON f.crypto_id = ca.crypto_id
        JOIN dim_date d ON f.date_id = d.date_id
    """)).fetchone()
    
    commodity_stats = conn.execute(text("""
        SELECT 
            COUNT(DISTINCT c.symbol) as total_commodities,
            COUNT(*) as total_records,
            MAX(d.date) as latest_date
        FROM fact_commodity_price f
        JOIN dim_commodity c ON f.commodity_id = c.commodity_id
        JOIN dim_date d ON f.date_id = d.date_id
    """)).fetchone()
    
    bond_stats = conn.execute(text("""
        SELECT 
            COUNT(DISTINCT b.isin) as total_bonds,
            COUNT(*) as total_records,
            MAX(d.date) as latest_date
        FROM fact_bond_price f
        JOIN dim_bond b ON f.bond_id = b.bond_id
        JOIN dim_date d ON f.date_id = d.date_id
    """)).fetchone()
    
    economic_stats = conn.execute(text("""
        SELECT 
            COUNT(DISTINCT ei.indicator_code) as total_indicators,
            COUNT(*) as total_records,
            MAX(d.date) as latest_date
        FROM fact_economic_indicator f
        JOIN dim_economic_indicator ei ON f.indicator_id = ei.indicator_id
        JOIN dim_date d ON f.date_id = d.date_id
    """)).fetchone()
    
    # Get latest stock prices
    latest_prices = pd.read_sql(text("""
        SELECT 
            c.ticker,
            c.company_name,
            c.sector,
            d.date,
            f.close_price,
            f.price_change_percent,
            f.volume
        FROM fact_stock_price f
        JOIN dim_company c ON f.company_id = c.company_id
        JOIN dim_date d ON f.date_id = d.date_id
        WHERE d.date = (SELECT MAX(date) FROM dim_date WHERE date_id IN (SELECT date_id FROM fact_stock_price))
        ORDER BY c.ticker
    """), conn)
    
    # Get top movers
    top_gainers = latest_prices.nlargest(5, 'price_change_percent')[['ticker', 'price_change_percent']].to_dict('records') if not latest_prices.empty else []
    top_losers = latest_prices.nsmallest(5, 'price_change_percent')[['ticker', 'price_change_percent']].to_dict('records') if not latest_prices.empty else []
    
    # Get latest crypto prices
    latest_crypto = pd.read_sql(text("""
        SELECT 
            ca.symbol,
            ca.name,
            d.date,
            f.price,
            f.market_cap,
            f.trading_volume
        FROM fact_crypto_price f
        JOIN dim_crypto_asset ca ON f.crypto_id = ca.crypto_id
        JOIN dim_date d ON f.date_id = d.date_id
        WHERE d.date = (SELECT MAX(date) FROM dim_date WHERE date_id IN (SELECT date_id FROM fact_crypto_price))
        ORDER BY ca.symbol
    """), conn)
    
    # Get latest commodities
    latest_commodities = pd.read_sql(text("""
        SELECT 
            c.symbol,
            c.name,
            c.category,
            d.date,
            f.close_price,
            f.price_change_percent
        FROM fact_commodity_price f
        JOIN dim_commodity c ON f.commodity_id = c.commodity_id
        JOIN dim_date d ON f.date_id = d.date_id
        WHERE d.date = (SELECT MAX(date) FROM dim_date WHERE date_id IN (SELECT date_id FROM fact_commodity_price))
        ORDER BY c.symbol
    """), conn)
    
    # Get latest economic indicators
    latest_economic = pd.read_sql(text("""
        SELECT 
            ei.indicator_code,
            ei.indicator_name,
            ei.category,
            d.date,
            f.value
        FROM fact_economic_indicator f
        JOIN dim_economic_indicator ei ON f.indicator_id = ei.indicator_id
        JOIN dim_date d ON f.date_id = d.date_id
        WHERE d.date = (SELECT MAX(date) FROM dim_date WHERE date_id IN (SELECT date_id FROM fact_economic_indicator))
        ORDER BY ei.indicator_code
    """), conn)
    
    conn.close()
    
    return render_template('index.html',
                         stock_stats=stock_stats,
                         crypto_stats=crypto_stats,
                         commodity_stats=commodity_stats,
                         bond_stats=bond_stats,
                         economic_stats=economic_stats,
                         latest_prices=latest_prices.to_dict('records'),
                         top_gainers=top_gainers,
                         top_losers=top_losers,
                         latest_crypto=latest_crypto.to_dict('records'),
                         latest_commodities=latest_commodities.to_dict('records'),
                         latest_economic=latest_economic.to_dict('records'))


@app.route('/filings')
def filings():
    """SEC filings overview page."""
    conn = get_db_connection()
    
    # Get summary stats for filings
    filing_stats = conn.execute(text("""
        SELECT 
            COUNT(DISTINCT c.ticker) as companies_with_filings,
            COUNT(*) as total_filings,
            MAX(d.date) as latest_filing_date
        FROM fact_sec_filing f
        JOIN dim_company c ON f.company_id = c.company_id
        JOIN dim_date d ON f.date_id = d.date_id
    """)).fetchone()
    
    # Get filings by type
    filings_by_type = pd.read_sql(text("""
        SELECT 
            ft.filing_type,
            ft.description,
            ft.category,
            COUNT(*) as count
        FROM fact_sec_filing f
        JOIN dim_filing_type ft ON f.filing_type_id = ft.filing_type_id
        GROUP BY ft.filing_type, ft.description, ft.category
        ORDER BY count DESC
    """), conn)
    
    # Get recent filings
    recent_filings = pd.read_sql(text("""
        SELECT 
            c.ticker,
            c.company_name,
            ft.filing_type,
            d.date as filing_date,
            f.accession_number,
            f.filing_url
        FROM fact_sec_filing f
        JOIN dim_company c ON f.company_id = c.company_id
        JOIN dim_filing_type ft ON f.filing_type_id = ft.filing_type_id
        JOIN dim_date d ON f.date_id = d.date_id
        ORDER BY d.date DESC
        LIMIT 50
    """), conn)
    
    conn.close()
    
    return render_template('filings.html',
                         filing_stats=filing_stats,
                         filings_by_type=filings_by_type.to_dict('records'),
                         recent_filings=recent_filings.to_dict('records'))


@app.route('/stock/<ticker>')
def stock_detail(ticker):
    """Detailed view for a specific stock."""
    conn = get_db_connection()
    
    # Get time range filter from query params
    time_range = request.args.get('range', 'all')
    
    # Get stock info
    stock_info = conn.execute(text("""
        SELECT ticker, company_name, sector, industry, country
        FROM dim_company
        WHERE ticker = :ticker
    """), {"ticker": ticker}).fetchone()
    
    if not stock_info:
        return "Stock not found", 404
    
    # Build date filter based on time range
    date_filter = ""
    if time_range != 'all':
        if time_range == '1m':
            date_filter = "AND d.date >= date('now', '-1 month')"
        elif time_range == '3m':
            date_filter = "AND d.date >= date('now', '-3 months')"
        elif time_range == '6m':
            date_filter = "AND d.date >= date('now', '-6 months')"
        elif time_range == '1y':
            date_filter = "AND d.date >= date('now', '-1 year')"
        elif time_range == '2y':
            date_filter = "AND d.date >= date('now', '-2 years')"
        elif time_range == '5y':
            date_filter = "AND d.date >= date('now', '-5 years')"
    
    # Get price history
    price_history = pd.read_sql(text(f"""
        SELECT 
            d.date,
            f.open_price,
            f.high_price,
            f.low_price,
            f.close_price,
            f.volume,
            f.price_change_percent
        FROM fact_stock_price f
        JOIN dim_company c ON f.company_id = c.company_id
        JOIN dim_date d ON f.date_id = d.date_id
        WHERE c.ticker = :ticker
        {date_filter}
        ORDER BY d.date
    """), conn, params={"ticker": ticker})
    
    # Get SEC filings for this ticker
    sec_filings = pd.read_sql(text("""
        SELECT 
            ft.filing_type,
            d.date as filing_date,
            f.accession_number,
            f.filing_url
        FROM fact_sec_filing f
        JOIN dim_company c ON f.company_id = c.company_id
        JOIN dim_filing_type ft ON f.filing_type_id = ft.filing_type_id
        JOIN dim_date d ON f.date_id = d.date_id
        WHERE c.ticker = :ticker
        ORDER BY d.date DESC
        LIMIT 20
    """), conn, params={"ticker": ticker})
    
    # Close connection after all queries are done
    conn.close()
    
    # Create price chart
    fig = go.Figure()
    fig.add_trace(go.Candlestick(
        x=price_history['date'],
        open=price_history['open_price'],
        high=price_history['high_price'],
        low=price_history['low_price'],
        close=price_history['close_price'],
        name=ticker
    ))
    fig.update_layout(
        title=f'{ticker} Price History',
        yaxis_title='Price ($)',
        xaxis_title='Date',
        template='plotly_white',
        height=500
    )
    price_chart = fig.to_html(full_html=False, div_id="price-chart")
    
    # Create volume chart
    fig_vol = px.bar(price_history, x='date', y='volume', title=f'{ticker} Trading Volume')
    fig_vol.update_layout(template='plotly_white', height=300)
    volume_chart = fig_vol.to_html(full_html=False, div_id="volume-chart")
    
    # Calculate stats
    latest_price = price_history.iloc[-1]['close_price'] if len(price_history) > 0 else 0
    avg_price = price_history['close_price'].mean()
    max_price = price_history['high_price'].max()
    min_price = price_history['low_price'].min()
    avg_volume = price_history['volume'].mean()
    
    stats = {
        'latest_price': round(latest_price, 2),
        'avg_price': round(avg_price, 2),
        'max_price': round(max_price, 2),
        'min_price': round(min_price, 2),
        'avg_volume': f"{avg_volume/1_000_000:.2f}M"
    }
    
    return render_template('stock_detail.html',
                         stock_info=stock_info,
                         stats=stats,
                         price_chart=price_chart,
                         volume_chart=volume_chart,
                         price_data=price_history.to_dict('records'),
                         sec_filings=sec_filings.to_dict('records'),
                         time_range=time_range)


@app.route('/crypto')
def crypto():
    """Cryptocurrency overview page."""
    conn = get_db_connection()
    
    # Get all crypto assets with latest prices
    crypto_data = pd.read_sql(text("""
        SELECT 
            ca.symbol,
            ca.name,
            ca.chain,
            MAX(d.date) as latest_date,
            COUNT(f.crypto_price_id) as data_points
        FROM dim_crypto_asset ca
        LEFT JOIN fact_crypto_price f ON ca.crypto_id = f.crypto_id
        LEFT JOIN dim_date d ON f.date_id = d.date_id
        GROUP BY ca.symbol, ca.name, ca.chain
        ORDER BY ca.symbol
    """), conn)
    
    # Get latest prices with details
    latest_crypto = pd.read_sql(text("""
        SELECT 
            ca.symbol,
            ca.name,
            d.date,
            f.price,
            f.market_cap,
            f.trading_volume
        FROM fact_crypto_price f
        JOIN dim_crypto_asset ca ON f.crypto_id = ca.crypto_id
        JOIN dim_date d ON f.date_id = d.date_id
        WHERE d.date = (SELECT MAX(date) FROM dim_date WHERE date_id IN (SELECT date_id FROM fact_crypto_price))
        ORDER BY f.market_cap DESC
    """), conn)
    
    # Get price history for all cryptos
    price_history = pd.read_sql(text("""
        SELECT 
            ca.symbol,
            d.date,
            f.price
        FROM fact_crypto_price f
        JOIN dim_crypto_asset ca ON f.crypto_id = ca.crypto_id
        JOIN dim_date d ON f.date_id = d.date_id
        ORDER BY d.date
    """), conn)
    
    conn.close()
    
    # Create price chart
    chart_html = None
    if not price_history.empty:
        fig = px.line(price_history, x='date', y='price', color='symbol',
                     title='Cryptocurrency Price History',
                     labels={'price': 'Price (USD)', 'date': 'Date', 'symbol': 'Crypto'})
        fig.update_layout(template='plotly_white', height=500)
        chart_html = fig.to_html(full_html=False, div_id="crypto-chart")
    
    return render_template('crypto.html',
                         crypto_data=crypto_data.to_dict('records'),
                         latest_crypto=latest_crypto.to_dict('records'),
                         chart_html=chart_html)


@app.route('/commodities')
def commodities():
    """Commodities overview page."""
    conn = get_db_connection()
    
    # Get all commodities with latest prices
    commodity_data = pd.read_sql(text("""
        SELECT 
            c.symbol,
            c.name,
            c.category,
            c.unit,
            c.exchange,
            MAX(d.date) as latest_date,
            COUNT(f.commodity_price_id) as data_points
        FROM dim_commodity c
        LEFT JOIN fact_commodity_price f ON c.commodity_id = f.commodity_id
        LEFT JOIN dim_date d ON f.date_id = d.date_id
        GROUP BY c.symbol, c.name, c.category, c.unit, c.exchange
        ORDER BY c.category, c.symbol
    """), conn)
    
    # Get latest prices
    latest_commodities = pd.read_sql(text("""
        SELECT 
            c.symbol,
            c.name,
            c.category,
            d.date,
            f.open_price,
            f.high_price,
            f.low_price,
            f.close_price,
            f.price_change_percent
        FROM fact_commodity_price f
        JOIN dim_commodity c ON f.commodity_id = c.commodity_id
        JOIN dim_date d ON f.date_id = d.date_id
        WHERE d.date = (SELECT MAX(date) FROM dim_date WHERE date_id IN (SELECT date_id FROM fact_commodity_price))
        ORDER BY c.category, c.symbol
    """), conn)
    
    # Get price history
    price_history = pd.read_sql(text("""
        SELECT 
            c.symbol,
            c.name,
            c.category,
            d.date,
            f.close_price
        FROM fact_commodity_price f
        JOIN dim_commodity c ON f.commodity_id = c.commodity_id
        JOIN dim_date d ON f.date_id = d.date_id
        ORDER BY d.date
    """), conn)
    
    conn.close()
    
    # Create price chart
    chart_html = None
    if not price_history.empty:
        fig = px.line(price_history, x='date', y='close_price', color='symbol',
                     title='Commodity Price History',
                     labels={'close_price': 'Price (USD)', 'date': 'Date', 'symbol': 'Commodity'})
        fig.update_layout(template='plotly_white', height=500)
        chart_html = fig.to_html(full_html=False, div_id="commodity-chart")
    
    return render_template('commodities.html',
                         commodity_data=commodity_data.to_dict('records'),
                         latest_commodities=latest_commodities.to_dict('records'),
                         chart_html=chart_html)


@app.route('/economic')
def economic():
    """Economic indicators overview page."""
    conn = get_db_connection()
    
    # Get all indicators with latest values
    indicator_data = pd.read_sql(text("""
        SELECT 
            ei.indicator_code,
            ei.indicator_name,
            ei.category,
            ei.unit,
            ei.frequency,
            MAX(d.date) as latest_date,
            COUNT(f.economic_data_id) as data_points
        FROM dim_economic_indicator ei
        LEFT JOIN fact_economic_indicator f ON ei.indicator_id = f.indicator_id
        LEFT JOIN dim_date d ON f.date_id = d.date_id
        GROUP BY ei.indicator_code, ei.indicator_name, ei.category, ei.unit, ei.frequency
        ORDER BY ei.category, ei.indicator_code
    """), conn)
    
    # Get latest values
    latest_economic = pd.read_sql(text("""
        SELECT 
            ei.indicator_code,
            ei.indicator_name,
            ei.category,
            ei.unit,
            d.date,
            f.value
        FROM fact_economic_indicator f
        JOIN dim_economic_indicator ei ON f.indicator_id = ei.indicator_id
        JOIN dim_date d ON f.date_id = d.date_id
        WHERE d.date = (SELECT MAX(date) FROM dim_date WHERE date_id IN (SELECT date_id FROM fact_economic_indicator))
        ORDER BY ei.category, ei.indicator_code
    """), conn)
    
    # Get value history
    value_history = pd.read_sql(text("""
        SELECT 
            ei.indicator_code,
            ei.indicator_name,
            d.date,
            f.value
        FROM fact_economic_indicator f
        JOIN dim_economic_indicator ei ON f.indicator_id = ei.indicator_id
        JOIN dim_date d ON f.date_id = d.date_id
        ORDER BY d.date
    """), conn)
    
    conn.close()
    
    # Create value chart
    chart_html = None
    if not value_history.empty:
        fig = px.line(value_history, x='date', y='value', color='indicator_code',
                     title='Economic Indicators Over Time',
                     labels={'value': 'Value', 'date': 'Date', 'indicator_code': 'Indicator'})
        fig.update_layout(template='plotly_white', height=500)
        chart_html = fig.to_html(full_html=False, div_id="economic-chart")
    
    return render_template('economic.html',
                         indicator_data=indicator_data.to_dict('records'),
                         latest_economic=latest_economic.to_dict('records'),
                         chart_html=chart_html)


@app.route('/compare')
def compare():
    """Compare multiple stocks."""
    conn = get_db_connection()
    
    # Get all available tickers
    tickers = pd.read_sql(text("SELECT ticker, company_name FROM dim_company ORDER BY ticker"), conn)
    
    # Get selected tickers from query params
    selected_tickers = request.args.getlist('tickers')
    
    chart_html = None
    if selected_tickers:
        # Get price data for selected stocks
        placeholders = ','.join([f':ticker{i}' for i in range(len(selected_tickers))])
        params = {f'ticker{i}': ticker for i, ticker in enumerate(selected_tickers)}
        
        price_data = pd.read_sql(text(f"""
            SELECT 
                c.ticker,
                d.date,
                f.close_price
            FROM fact_stock_price f
            JOIN dim_company c ON f.company_id = c.company_id
            JOIN dim_date d ON f.date_id = d.date_id
            WHERE c.ticker IN ({placeholders})
            ORDER BY d.date, c.ticker
        """), conn, params=params)
        
        # Create comparison chart
        fig = px.line(price_data, x='date', y='close_price', color='ticker',
                     title='Stock Price Comparison',
                     labels={'close_price': 'Price ($)', 'date': 'Date'})
        fig.update_layout(template='plotly_white', height=500)
        chart_html = fig.to_html(full_html=False, div_id="comparison-chart")
    
    conn.close()
    
    return render_template('compare.html',
                         tickers=tickers.to_dict('records'),
                         selected_tickers=selected_tickers,
                         chart_html=chart_html)


@app.route('/api/stocks')
def api_stocks():
    """API endpoint to get all stocks."""
    conn = get_db_connection()
    
    stocks = pd.read_sql(text("""
        SELECT 
            c.ticker,
            c.company_name,
            c.sector,
            COUNT(f.price_id) as data_points,
            MAX(d.date) as latest_date
        FROM dim_company c
        LEFT JOIN fact_stock_price f ON c.company_id = f.company_id
        LEFT JOIN dim_date d ON f.date_id = d.date_id
        GROUP BY c.ticker, c.company_name, c.sector
        ORDER BY c.ticker
    """), conn)
    
    conn.close()
    
    return jsonify(stocks.to_dict('records'))


@app.route('/api/stock/<ticker>/data')
def api_stock_data(ticker):
    """API endpoint to get stock price data."""
    conn = get_db_connection()
    
    data = pd.read_sql(text("""
        SELECT 
            d.date,
            f.open_price,
            f.high_price,
            f.low_price,
            f.close_price,
            f.volume,
            f.price_change_percent
        FROM fact_stock_price f
        JOIN dim_company c ON f.company_id = c.company_id
        JOIN dim_date d ON f.date_id = d.date_id
        WHERE c.ticker = :ticker
        ORDER BY d.date
    """), conn, params={"ticker": ticker})
    
    conn.close()
    
    return jsonify(data.to_dict('records'))


@app.route('/api/filings')
def api_filings():
    """API endpoint to get all SEC filings."""
    conn = get_db_connection()
    
    filings = pd.read_sql(text("""
        SELECT 
            c.ticker,
            c.company_name,
            ft.filing_type,
            ft.category,
            d.date as filing_date,
            f.accession_number,
            f.filing_url,
            f.filing_size
        FROM fact_sec_filing f
        JOIN dim_company c ON f.company_id = c.company_id
        JOIN dim_filing_type ft ON f.filing_type_id = ft.filing_type_id
        JOIN dim_date d ON f.date_id = d.date_id
        ORDER BY d.date DESC
    """), conn)
    
    conn.close()
    
    return jsonify(filings.to_dict('records'))


@app.route('/api/stock/<ticker>/filings')
def api_stock_filings(ticker):
    """API endpoint to get SEC filings for a specific ticker."""
    conn = get_db_connection()
    
    filings = pd.read_sql(text("""
        SELECT 
            ft.filing_type,
            ft.description,
            ft.category,
            d.date as filing_date,
            f.accession_number,
            f.filing_url,
            f.filing_size
        FROM fact_sec_filing f
        JOIN dim_company c ON f.company_id = c.company_id
        JOIN dim_filing_type ft ON f.filing_type_id = ft.filing_type_id
        JOIN dim_date d ON f.date_id = d.date_id
        WHERE c.ticker = :ticker
        ORDER BY d.date DESC
    """), conn, params={"ticker": ticker})
    
    conn.close()
    
    return jsonify(filings.to_dict('records'))


@app.route('/chat')
def chat():
    """RAG chat interface for querying SEC filings."""
    conn = get_db_connection()
    
    # Get available companies with SEC filings
    companies = pd.read_sql(text("""
        SELECT DISTINCT
            c.ticker,
            c.company_name,
            COUNT(f.filing_id) as filing_count
        FROM dim_company c
        JOIN fact_sec_filing f ON c.company_id = f.company_id
        WHERE f.filing_text IS NOT NULL
        GROUP BY c.ticker, c.company_name
        ORDER BY c.ticker
    """), conn)
    
    conn.close()
    
    return render_template('chat.html',
                         rag_available=RAG_AVAILABLE,
                         companies=companies.to_dict('records'))


def fetch_multi_asset_data(question):
    """Fetch relevant data from all asset types based on question keywords."""
    conn = get_db_connection()
    data_summary = ""
    
    question_lower = question.lower()
    
    # Check for crypto keywords
    crypto_keywords = ['crypto', 'bitcoin', 'btc', 'ethereum', 'eth', 'ada', 'cardano']
    if any(kw in question_lower for kw in crypto_keywords):
        crypto_data = pd.read_sql(text("""
            SELECT 
                ca.symbol,
                ca.name,
                d.date,
                f.price,
                f.market_cap,
                f.price_change_24h
            FROM fact_crypto_price f
            JOIN dim_crypto_asset ca ON f.crypto_id = ca.crypto_id
            JOIN dim_date d ON f.date_id = d.date_id
            ORDER BY d.date DESC
            LIMIT 30
        """), conn)
        
        if not crypto_data.empty:
            data_summary += "\n\n₿ **Cryptocurrency Data:**\n"
            for symbol in crypto_data['symbol'].unique():
                symbol_data = crypto_data[crypto_data['symbol'] == symbol]
                latest = symbol_data.iloc[0]
                data_summary += f"\n{symbol} ({latest['name']}):\n"
                data_summary += f"  Latest Price: ${latest['price']:,.2f} ({latest['date']})\n"
                if latest['market_cap']:
                    data_summary += f"  Market Cap: ${latest['market_cap']:,.0f}\n"
                if latest['price_change_24h']:
                    data_summary += f"  24h Change: {latest['price_change_24h']:.2f}%\n"
    
    # Check for commodity keywords
    commodity_keywords = ['commodity', 'commodities', 'oil', 'gold', 'silver', 'copper', 'gas', 'metal']
    if any(kw in question_lower for kw in commodity_keywords):
        commodity_data = pd.read_sql(text("""
            SELECT 
                c.symbol,
                c.name,
                c.category,
                d.date,
                f.close_price,
                f.price_change_percent
            FROM fact_commodity_price f
            JOIN dim_commodity c ON f.commodity_id = c.commodity_id
            JOIN dim_date d ON f.date_id = d.date_id
            ORDER BY d.date DESC
            LIMIT 30
        """), conn)
        
        if not commodity_data.empty:
            data_summary += "\n\n🛢️ **Commodity Data:**\n"
            for symbol in commodity_data['symbol'].unique():
                symbol_data = commodity_data[commodity_data['symbol'] == symbol]
                latest = symbol_data.iloc[0]
                data_summary += f"\n{latest['name']} ({symbol}) - {latest['category']}:\n"
                data_summary += f"  Latest Price: ${latest['close_price']:.2f} ({latest['date']})\n"
                if latest['price_change_percent']:
                    data_summary += f"  Change: {latest['price_change_percent']:.2f}%\n"
    
    # Check for economic keywords
    economic_keywords = ['gdp', 'unemployment', 'inflation', 'cpi', 'interest rate', 'fed', 'economy', 'economic']
    if any(kw in question_lower for kw in economic_keywords):
        economic_data = pd.read_sql(text("""
            SELECT 
                ei.indicator_code,
                ei.indicator_name,
                ei.category,
                ei.unit,
                d.date,
                f.value
            FROM fact_economic_indicator f
            JOIN dim_economic_indicator ei ON f.indicator_id = ei.indicator_id
            JOIN dim_date d ON f.date_id = d.date_id
            ORDER BY d.date DESC
            LIMIT 20
        """), conn)
        
        if not economic_data.empty:
            data_summary += "\n\n📈 **Economic Indicators:**\n"
            for code in economic_data['indicator_code'].unique():
                indicator_data = economic_data[economic_data['indicator_code'] == code]
                latest = indicator_data.iloc[0]
                data_summary += f"\n{latest['indicator_name']} ({code}):\n"
                data_summary += f"  Latest Value: {latest['value']:.2f} {latest['unit']} ({latest['date']})\n"
                
                # Calculate trend if we have multiple data points
                if len(indicator_data) > 1:
                    oldest = indicator_data.iloc[-1]
                    change = latest['value'] - oldest['value']
                    data_summary += f"  Trend: {change:+.2f} since {oldest['date']}\n"
    
    conn.close()
    return data_summary


@app.route('/api/chat/query', methods=['POST'])
def api_chat_query():
    """API endpoint for RAG queries with multi-asset data access."""
    if not RAG_AVAILABLE:
        return jsonify({
            'success': False,
            'error': 'RAG system not available. Check Ollama connection.'
        }), 503
    
    try:
        data = request.get_json()
        question = data.get('question', '').strip()
        
        if not question:
            return jsonify({'success': False, 'error': 'No question provided'}), 400
        
        # Strategy: Provide comprehensive multi-asset data
        # 1. Try RAG for SEC filing context
        # 2. Fetch relevant crypto/commodity/economic data
        # 3. Extract tickers and get stock price data
        # 4. Let LLM synthesize all sources
        
        rag = RAGSystem()
        result = rag.query(question, verbose=False)
        
        # Fetch multi-asset data based on question keywords
        multi_asset_summary = fetch_multi_asset_data(question)
        
        # Extract tickers from sources OR question
        tickers = list(set([s['ticker'] for s in result['sources']])) if result['sources'] else []
        
        # If no sources, try to extract ticker from question
        if not tickers:
            import re
            # Common ticker patterns
            ticker_matches = re.findall(r'\b([A-Z]{1,5})\b', question.upper())
            # Also check for company names
            company_map = {'APPLE': 'AAPL', 'MICROSOFT': 'MSFT', 'NVIDIA': 'NVDA', 'AMAZON': 'AMZN'}
            for company, ticker in company_map.items():
                if company in question.upper():
                    tickers.append(ticker)
                    break
            if not tickers and ticker_matches:
                # Use first potential ticker found
                tickers = [ticker_matches[0]]
        
        # If we found tickers, fetch price data
        if tickers:
            conn = get_db_connection()
            
            # Get recent price data for mentioned tickers
            placeholders = ','.join([f':ticker{i}' for i in range(len(tickers))])
            params = {f'ticker{i}': ticker for i, ticker in enumerate(tickers)}
            
            price_data = pd.read_sql(text(f"""
                SELECT 
                    c.ticker,
                    d.date,
                    f.open_price,
                    f.high_price,
                    f.low_price,
                    f.close_price,
                    f.volume,
                    f.price_change_percent
                FROM fact_stock_price f
                JOIN dim_company c ON f.company_id = c.company_id
                JOIN dim_date d ON f.date_id = d.date_id
                WHERE c.ticker IN ({placeholders})
                ORDER BY d.date DESC
                LIMIT 100
            """), conn, params=params)
            
            conn.close()
            
            if not price_data.empty:
                # Build comprehensive price summary
                price_summary = "\n\n📊 Stock Market Data:\n"
                
                for ticker in tickers:
                    ticker_data = price_data[price_data['ticker'] == ticker]
                    if not ticker_data.empty:
                        latest = ticker_data.iloc[0]
                        oldest = ticker_data.iloc[-1]
                        avg_price = ticker_data['close_price'].mean()
                        max_price = ticker_data['high_price'].max()
                        min_price = ticker_data['low_price'].min()
                        
                        # Calculate price change
                        price_change = latest['close_price'] - oldest['close_price']
                        price_change_pct = (price_change / oldest['close_price']) * 100
                        
                        price_summary += f"\n{ticker}:\n"
                        price_summary += f"  Latest Close: ${latest['close_price']:.2f} ({latest['date']})\n"
                        price_summary += f"  Period Change: ${price_change:+.2f} ({price_change_pct:+.2f}%)\n"
                        price_summary += f"  Average: ${avg_price:.2f}\n"
                        price_summary += f"  Range: ${min_price:.2f} - ${max_price:.2f}\n"
                        price_summary += f"  Data Points: {len(ticker_data)} days\n"
                
                # Combine all data sources
                all_market_data = price_summary + multi_asset_summary
                
                # If we have SEC filing context, create integrated analysis
                if result['sources'] and result['answer'] and "No relevant information found" not in result['answer']:
                    # Create integrated prompt with all data sources
                    integrated_prompt = f"""You have access to SEC filings, stock prices, cryptocurrency data, commodity prices, and economic indicators. Provide a comprehensive multi-asset analysis.

SEC Filing Context:
{result['answer']}

{all_market_data}

Question: {question}

Provide an integrated analysis combining insights from ALL available data sources (SEC filings, stocks, crypto, commodities, economic indicators). Be specific and actionable."""
                    
                    try:
                        # Get integrated analysis from LLM
                        import ollama
                        ollama_client = ollama.Client(host=OLLAMA_HOST)
                        response = ollama_client.generate(
                            model=RAG_LLM_MODEL,
                            prompt=integrated_prompt
                        )
                        result['answer'] = response['response']
                    except Exception as e:
                        # Fallback: just append all data
                        result['answer'] += all_market_data
                else:
                    # No SEC data, provide market data analysis
                    if not result['answer'] or "No relevant information found" in result['answer']:
                        if tickers:
                            result['answer'] = f"Here's the available multi-asset data:" + all_market_data
                        else:
                            result['answer'] = all_market_data if all_market_data else "No relevant data found for this query."
                    else:
                        result['answer'] += all_market_data
                
                result['price_data'] = price_data.to_dict('records')
        else:
            # No tickers found, but we might have multi-asset data
            if multi_asset_summary:
                if result['answer'] and "No relevant information found" not in result['answer']:
                    # Have SEC data + multi-asset data
                    integrated_prompt = f"""You have access to SEC filings and market data. Provide a comprehensive analysis.

SEC Filing Context:
{result['answer']}

{multi_asset_summary}

Question: {question}

Provide an integrated analysis combining all available information."""
                    
                    try:
                        import ollama
                        ollama_client = ollama.Client(host=OLLAMA_HOST)
                        response = ollama_client.generate(
                            model=RAG_LLM_MODEL,
                            prompt=integrated_prompt
                        )
                        result['answer'] = response['response']
                    except Exception as e:
                        result['answer'] += multi_asset_summary
                else:
                    result['answer'] = multi_asset_summary
        
        return jsonify({
            'success': True,
            'answer': result['answer'],
            'sources': result['sources'],
            'price_data': result.get('price_data', [])
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/nl-to-sql', methods=['POST'])
def api_nl_to_sql():
    """API endpoint for natural language to SQL queries."""
    try:
        from nl_to_sql import NLToSQLEngine
        
        data = request.get_json()
        question = data.get('question', '').strip()
        
        if not question:
            return jsonify({'success': False, 'error': 'No question provided'}), 400
        
        engine = NLToSQLEngine()
        result = engine.query(question)
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/add-ticker')
def add_ticker_page():
    """Page to add new tickers."""
    return render_template('add_ticker.html')


@app.route('/api/add-ticker', methods=['POST'])
def add_ticker_api():
    """API endpoint to fetch and add a new ticker."""
    import subprocess
    import json
    from datetime import datetime
    
    data = request.get_json()
    tickers = data.get('tickers', [])
    period = data.get('period', '1mo')
    
    if not tickers:
        return jsonify({'success': False, 'error': 'No tickers provided'}), 400
    
    # Validate tickers (basic check)
    tickers = [t.strip().upper() for t in tickers if t.strip()]
    
    if not tickers:
        return jsonify({'success': False, 'error': 'Invalid tickers'}), 400
    
    try:
        # Run the pipeline for the new tickers
        pipeline_path = os.path.join(parent_dir, 'pipeline.py')
        venv_python = os.path.join(parent_dir, 'venv', 'bin', 'python')
        
        cmd = [venv_python, pipeline_path, '--tickers'] + tickers + ['--period', period]
        
        result = subprocess.run(
            cmd,
            cwd=parent_dir,
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )
        
        if result.returncode == 0:
            return jsonify({
                'success': True,
                'message': f'Successfully added {len(tickers)} ticker(s)',
                'tickers': tickers,
                'output': result.stdout[-500:]  # Last 500 chars
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Pipeline failed',
                'details': result.stderr[-500:]
            }), 500
            
    except subprocess.TimeoutExpired:
        return jsonify({
            'success': False,
            'error': 'Pipeline timed out after 5 minutes'
        }), 500
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
