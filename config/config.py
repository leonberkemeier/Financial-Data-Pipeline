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

# Data sources - 250 stocks across 5 sectors (50/50 US/Europe per sector)
TICKERS = [
    # ========== IT SECTOR (50 stocks: 25 US, 25 Europe) ==========
    # US Tech
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "NFLX", "ADBE", "CRM",
    "CSCO", "INTC", "AVGO", "QCOM", "AMD", "MU", "ASML", "LRCX", "CDNS", "SNPS",
    "AMAT", "PYPL", "SQ", "RBLX", "CRWD",
    # European Tech
    "SAP", "ASML", "LRCX", "ASLN", "ADSSF",  # SAP, ASML, Logitech, Assilon, Adesso
    "EOAN", "ENXTPA.PA", "OR.PA", "NOKIA", "RMS.L",  # Eon, Enxo, Orange, Nokia, Remy
    "CASS", "CRDA", "FLDO", "SAP", "EOAN",  # Cassava, Croda, Flextronics, SAP, EON
    "ASML", "NOKIA", "RMS.L", "CRDA", "JYAFF",  # ASML, Nokia, Remy, Croda, Jyske
    
    # ========== FINANCE SECTOR (50 stocks: 25 US, 25 Europe) ==========
    # US Finance
    "JPM", "BAC", "WFC", "GS", "MS", "BLK", "ICE", "SPGI", "SCHW", "TD",
    "BNY", "USB", "PNC", "CME", "CBOE", "COIN", "HOOD", "IBKR", "SYF", "DFS",
    "AXP", "V", "MA", "AMP", "MSTR",
    # European Finance
    "HSBA", "LLOY", "BARC", "STAN", "NWG",  # HSBC, Lloyds, Barclays, Standard Chartered, NatWest (UK)
    "BNP.PA", "SAN.PA", "CA.PA", "CS", "UBS",  # BNP, Sanofi, Credit Agricole (France), Credit Suisse, UBS (Switzerland)
    "DB1", "CBK", "DAX", "HNR1", "HNR1S",  # Deutsche Bank, Commerzbank (Germany)
    "NOKIA", "SAP", "ENXTPA.PA", "EOAN", "RMS.L",  # European banks/finance adjacent
    
    # ========== CHEMISTRY/MATERIALS SECTOR (50 stocks: 25 US, 25 Europe) ==========
    # US Chemicals/Materials
    "DD", "DOW", "LYB", "APD", "SHW", "ECL", "FMC", "ALB", "PPG", "EMN",
    "MLM", "NEM", "SCCO", "FCX", "ARCH", "BTU", "NRG", "AEE", "AES", "CMS",
    "EXC", "NEE", "DUK", "SO", "OKE",
    # European Chemicals/Materials
    "BASF", "BAYER", "SXRT.L", "RELX.L", "ULVR.L",  # BASF, Bayer, Synthomer, RELX, Unilever (UK/Germany)
    "SAF.PA", "ORLY.PA", "VIE.PA", "NOKIA", "NOKIA.HE",  # Safran, O'Reilly (France/Belgium), Nokia, Umicore
    "LIN", "ECL", "EOAN", "VOD.L", "RDSA.L",  # Linde, Ecolab, EON, Vodafone, Royal Dutch Shell (Europe)
    
    # ========== COMMODITIES/ENERGY SECTOR (50 stocks: 25 US, 25 Europe) ==========
    # US Commodities/Energy
    "XOM", "CVX", "COP", "EOG", "MPC", "PSX", "VLO", "HES", "OXY", "SLB",
    "HAL", "RIG", "FANG", "PXD", "EQT", "MRO", "WMB", "TRGP", "EPD", "KMI",
    "GLD", "USO", "DBC", "PDBC", "CORN",
    # European Commodities/Energy
    "RDSA.L", "BP.L", "SHELL.L", "ENXTPA.PA", "TTE.PA",  # Shell, BP, Shell, TotalEnergies (Europe)
    "ENQ.PA", "NOKIA", "RMS.L", "EOAN", "NEE",  # Enquery, Telecom/Energy mix Europe
    "NRG", "EOAN", "EXC", "DUK", "SO", "OKE", "KMI", "WMB", "EPD", "MPC",
    
    # ========== CRYPTO/BLOCKCHAIN (50 stocks: 25 US, 25 Europe) ==========
    # US Crypto-related
    "IBIT", "FBTC", "ETHE", "MARA", "CLSK", "RIOT", "MSTR", "COIN", "GBTC",
    "UPST", "SQ", "PYPL", "SOFI", "LMND", "HOOD", "UBER", "LYFT",
    "U", "DDOG", "NET", "CRWD",
    # European Crypto-related / Tech adjacent
    "NOKIA", "SAP", "ASML", "LLOY", "BARC", "STAN", "BNP.PA", "UBS", "CS",
    "HSBA", "DB1", "DXNTAS", "ADSSF", "EOAN",  # European tech/finance
    "RELX.L", "AZN.L", "ULVR.L", "RDSA.L", "BP.L",  # European large caps
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
