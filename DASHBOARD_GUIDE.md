# Web Dashboard - Complete Guide

## 🚀 Quick Start

```bash
# 1. Make sure you have data
python pipeline.py --tickers AAPL TSLA MSFT GOOGL --period 1mo

# 2. Start the dashboard
./run_dashboard.sh

# 3. Open in your browser
http://localhost:5000
```

## 📊 Dashboard Features

### Main Dashboard (Home Page)
- **Summary Cards**: Total companies, records, trading days, latest date
- **Top Gainers/Losers**: See the 5 best and worst performing stocks
- **Latest Prices Table**: All stocks with current prices, change %, and volume
- **Quick Actions**: Click "View" to see detailed stock information

### Stock Detail Page
**URL**: `http://localhost:5000/stock/AAPL`

Features:
- **Company Info**: Name, sector, industry, country
- **Key Stats**: Current price, average, high, low, average volume
- **Interactive Candlestick Chart**: OHLC (Open-High-Low-Close) data
  - Hover for details
  - Zoom and pan
  - Download as PNG
- **Volume Chart**: Bar chart showing trading volume
- **Historical Data Table**: Full price history with all metrics

### Compare Stocks Page
**URL**: `http://localhost:5000/compare`

Features:
- **Stock Selector**: Checkboxes for all available stocks
- **Line Chart**: Compare closing prices over time
- **Multi-stock Analysis**: Select 2+ stocks to see trends

## 🔌 API Endpoints

### List All Stocks
```bash
curl http://localhost:5000/api/stocks | jq
```

Response:
```json
[
  {
    "ticker": "AAPL",
    "company_name": "Apple Inc.",
    "sector": "Technology",
    "data_points": 24,
    "latest_date": "2025-11-13"
  }
]
```

### Get Stock Data
```bash
curl http://localhost:5000/api/stock/AAPL/data | jq
```

Response:
```json
[
  {
    "date": "2025-10-13",
    "open_price": 249.13,
    "high_price": 249.44,
    "low_price": 245.32,
    "close_price": 247.42,
    "volume": 38142900,
    "price_change_percent": -0.69
  }
]
```

## 🎨 Customization

### Change Colors
Edit `dashboard/static/css/style.css`:

```css
/* Change primary color */
.navbar {
    background: linear-gradient(135deg, #your-color 0%, #your-color-2 100%);
}

/* Change accent color */
.stat-card h3 {
    color: #your-accent-color;
}
```

### Change Port
Edit `dashboard/app.py` (last line):

```python
app.run(debug=True, host='0.0.0.0', port=8080)
```

### Add Custom Pages
1. Create new route in `app.py`
2. Create template in `dashboard/templates/`
3. Add navigation link in `templates/base.html`

## 🔧 Troubleshooting

### Dashboard won't start

**Error: No module named 'flask'**
```bash
cd /home/archy/Desktop/Server/FinancialData/financial_data_aggregator
source venv/bin/activate
pip install flask plotly
```

**Error: Database not found**
```bash
# Run the pipeline first
python pipeline.py --tickers AAPL
```

### No data showing

**Check database has data:**
```bash
sqlite3 financial_data.db "SELECT COUNT(*) FROM fact_stock_price;"
```

**Run pipeline to populate data:**
```bash
python pipeline.py --period 1mo
```

### Charts not displaying

- Check browser console (F12) for errors
- Ensure you have internet connection (Plotly loads from CDN)
- Try refreshing the page (Ctrl+R)

### Port already in use

```bash
# Find process using port 5000
lsof -i :5000

# Kill it
kill -9 <PID>

# Or use different port (edit app.py)
```

## 📱 Access from Other Devices

The dashboard runs on `0.0.0.0`, meaning it's accessible on your network:

```bash
# Find your IP
ip addr show | grep inet

# Access from another device
http://YOUR_IP:5000
```

Example: `http://192.168.1.100:5000`

## 🛑 Stopping the Dashboard

Press `Ctrl+C` in the terminal where it's running.

## 💡 Tips

1. **Refresh Data**: Run the pipeline while dashboard is running - it will show new data on page refresh
2. **Bookmarks**: Bookmark specific stock pages for quick access
3. **API Integration**: Use the API endpoints in scripts or other applications
4. **Mobile Friendly**: The dashboard is responsive and works on mobile browsers

## 🎯 Use Cases

**Daily Market Review**
```bash
# Update data
python pipeline.py

# View dashboard
./run_dashboard.sh
# Check top movers, review stock charts
```

**Stock Analysis**
- Navigate to specific stock page
- Analyze candlestick patterns
- Check volume trends
- Review historical performance

**Portfolio Comparison**
- Go to Compare page
- Select your holdings
- See relative performance

**Data Export**
- Use API endpoints to fetch data
- Process with scripts or notebooks
- Build custom analyses
