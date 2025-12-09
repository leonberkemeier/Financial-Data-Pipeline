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
from config.config import DATABASE_URL

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
    
    # Get summary stats
    stats = conn.execute(text("""
        SELECT 
            COUNT(DISTINCT c.ticker) as total_companies,
            COUNT(DISTINCT d.date) as total_dates,
            COUNT(*) as total_records,
            MAX(d.date) as latest_date
        FROM fact_stock_price f
        JOIN dim_company c ON f.company_id = c.company_id
        JOIN dim_date d ON f.date_id = d.date_id
    """)).fetchone()
    
    # Get latest prices
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
    top_gainers = latest_prices.nlargest(5, 'price_change_percent')[['ticker', 'price_change_percent']].to_dict('records')
    top_losers = latest_prices.nsmallest(5, 'price_change_percent')[['ticker', 'price_change_percent']].to_dict('records')
    
    conn.close()
    
    return render_template('index.html',
                         stats=stats,
                         latest_prices=latest_prices.to_dict('records'),
                         top_gainers=top_gainers,
                         top_losers=top_losers)


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
