#!/bin/bash

# Quick test runner for crypto and bond extraction tests

set -e  # Exit on any error

echo "=================================================="
echo "Financial Data Aggregator - Test Suite"
echo "=================================================="

# Check if venv is activated
if [[ -z "${VIRTUAL_ENV}" ]]; then
    echo "⚠️  Virtual environment not activated!"
    echo "Please run: source venv/bin/activate"
    exit 1
fi

echo "✓ Virtual environment activated: $VIRTUAL_ENV"

# Check database connection
echo ""
echo "Checking database connection..."
if ! python -c "from config.config import DATABASE_URL; print('Database URL:', DATABASE_URL)" 2>/dev/null; then
    echo "❌ Database configuration error"
    exit 1
fi
echo "✓ Database configured"

# Check Python dependencies
echo ""
echo "Checking Python dependencies..."
python -c "import yfinance, pandas, sqlalchemy, requests, loguru" || {
    echo "❌ Missing dependencies"
    echo "Please run: pip install -r requirements.txt"
    exit 1
}
echo "✓ All dependencies installed"

# Test crypto pipeline
echo ""
echo "=================================================="
echo "TEST 1: Cryptocurrency Pipeline"
echo "=================================================="
python test_crypto.py
CRYPTO_RESULT=$?

if [ $CRYPTO_RESULT -eq 0 ]; then
    echo "✓ Cryptocurrency test PASSED"
else
    echo "❌ Cryptocurrency test FAILED"
fi

echo ""

# Test bond pipeline
echo "=================================================="
echo "TEST 2: Bond Pipeline"
echo "=================================================="

# Check for FRED API key
if [[ -z "${FRED_API_KEY}" ]]; then
    echo "⚠️  FRED_API_KEY not set"
    echo "To test bonds, set: export FRED_API_KEY='your_api_key'"
    echo "Get a free key at: https://fred.stlouisfed.org/docs/api/"
    echo ""
    echo "Skipping bond test..."
    BOND_RESULT=0
else
    python test_bonds.py
    BOND_RESULT=$?
    
    if [ $BOND_RESULT -eq 0 ]; then
        echo "✓ Bond test PASSED"
    else
        echo "❌ Bond test FAILED"
    fi
fi

echo ""
echo "=================================================="
echo "Test Summary"
echo "=================================================="

if [ $CRYPTO_RESULT -eq 0 ] && [ $BOND_RESULT -eq 0 ]; then
    echo "✓ All tests PASSED!"
    echo ""
    echo "Next steps:"
    echo "  1. Verify data in database: psql -d financial_data -U your_user"
    echo "  2. Update configuration: config/config.py"
    echo "  3. Review test logs: logs/"
    exit 0
else
    echo "❌ Some tests FAILED"
    echo ""
    echo "Troubleshooting:"
    echo "  1. Check logs in logs/ directory"
    echo "  2. Verify .env configuration"
    echo "  3. Ensure PostgreSQL is running"
    echo "  4. For bonds, set FRED_API_KEY"
    exit 1
fi
