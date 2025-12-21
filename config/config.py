"""Configuration management for the financial data aggregator."""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Project paths
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
LOGS_DIR = BASE_DIR / "logs"

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@localhost:5432/financial_data") # Replace with your actual password

# API Configuration
ALPHA_VANTAGE_API_KEY = os.getenv("ALPHA_VANTAGE_API_KEY")

# Pipeline Configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
BATCH_SIZE = int(os.getenv("BATCH_SIZE", 100))

# Data sources
TICKERS = [
    "AAPL", "GOOGL", "MSFT", "AMZN", "TSLA",
    "META", "NVDA", "JPM", "V", "WMT"
]

# Cryptocurrency Configuration
CRYPTO_SYMBOLS = os.getenv("CRYPTO_SYMBOLS", "BTC,ETH,ADA,SOL,DOGE,XRP,DOT,MATIC").split(",")

# Bond Configuration
BOND_TYPES = [
    "US_3MO", "US_1Y", "US_2Y", "US_5Y", "US_10Y", "US_30Y"
]
CORPORATE_BOND_RATINGS = [
    "AAA", "AA", "A", "BBB", "BB", "B", "CCC"
]

# FRED API Configuration (for bond data)
FRED_API_KEY = os.getenv("FRED_API_KEY")

# Ollama Configuration (for RAG demo)
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")

# RAG Configuration
RAG_LLM_MODEL = os.getenv("RAG_LLM_MODEL", "llama3.1:8b")
RAG_EMBEDDING_MODEL = os.getenv("RAG_EMBEDDING_MODEL", "nomic-embed-text")
RAG_TOP_K_RESULTS = int(os.getenv("RAG_TOP_K_RESULTS", 3))
RAG_CHROMA_PATH = BASE_DIR / "data" / "chromadb"

# Ensure directories exist
DATA_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)
RAG_CHROMA_PATH.mkdir(parents=True, exist_ok=True)
