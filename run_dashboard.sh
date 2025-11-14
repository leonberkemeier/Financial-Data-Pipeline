#!/bin/bash
# Start the financial data dashboard

cd "$(dirname "$0")"
source venv/bin/activate
cd dashboard
python app.py
