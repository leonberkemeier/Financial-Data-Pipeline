# Financial Data Dashboard

A web-based visualization dashboard for exploring your financial data.

## Features

- **Market Overview**: View summary statistics and latest prices
- **Stock Details**: Interactive candlestick charts, volume graphs, and historical data
- **Stock Comparison**: Compare multiple stocks side-by-side
- **Top Movers**: See biggest gainers and losers
- **RESTful API**: JSON endpoints for programmatic access

## Quick Start

### Start the Dashboard

```bash
# From the project root
./run_dashboard.sh

# Or manually
cd dashboard
source ../venv/bin/activate
python app.py
```

The dashboard will be available at: **http://localhost:5000**

## Pages

### Main Dashboard (`/`)
- Summary statistics (companies, records, dates)
- Top gainers and losers
- Latest prices table with all stocks

### Stock Detail (`/stock/<TICKER>`)
- Company information
- Interactive candlestick chart (OHLC data)
- Volume bar chart
- Historical data table
- Key statistics (current, average, high, low prices)

### Compare Stocks (`/compare`)
- Select multiple stocks
- View price trends on a single chart
- Compare performance over time

## API Endpoints

### Get All Stocks
```bash
curl http://localhost:5000/api/stocks
```

Returns list of all stocks with metadata.

### Get Stock Data
```bash
curl http://localhost:5000/api/stock/AAPL/data
```

Returns historical price data for specified ticker.

## Configuration

The dashboard uses the same database configuration as the main pipeline (`.env` file).

## Screenshots

Navigate to:
- `http://localhost:5000` - Main dashboard
- `http://localhost:5000/stock/AAPL` - AAPL stock details
- `http://localhost:5000/compare?tickers=AAPL&tickers=TSLA` - Compare AAPL and TSLA

## Tech Stack

- **Flask**: Web framework
- **Plotly**: Interactive charts
- **SQLAlchemy**: Database queries
- **Pandas**: Data manipulation

## Customization

Edit `static/css/style.css` to change colors and styling.

## Troubleshooting

**Database not found?**
- Make sure you've run the pipeline first: `python pipeline.py`
- Check your `.env` file has the correct DATABASE_URL

**Port already in use?**
- Change the port in `app.py`: `app.run(port=5001)`

**Charts not displaying?**
- Check browser console for errors
- Ensure Plotly CDN is accessible
