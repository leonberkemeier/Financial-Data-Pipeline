# 🚀 Deployment Checklist - What to Copy to Server

## 📋 Quick Summary
**Copy EVERYTHING except:**
- ❌ `venv/` or `venv_test/` (virtual environments)
- ❌ `__pycache__/` directories
- ❌ `.pyc` files
- ❌ `*.db` and `*.sqlite` files (databases will be created fresh)
- ❌ `logs/*.log` files
- ❌ `Resume.md`

---

## 📁 Essential Directories to Copy

### **✅ MUST COPY - Core Application**
```
src/                          # All source code modules
├── analyzers/               # Filing analyzers
├── extractors/              # Data extractors (Yahoo, FRED, etc.)
├── loaders/                 # Database loaders
├── models/                  # Database models
├── transformers/            # Data transformers
└── utils/                   # Utilities (including email_notifier.py!)

config/                       # Configuration files
├── config.py
├── pipeline_config.yaml     # ⭐ CRITICAL: Has rate limits & settings
└── __init__.py

dashboard/                    # Web dashboard (Flask app)
├── app.py
├── templates/
├── static/
└── README.md
```

### **✅ MUST COPY - Pipeline Scripts**
```
unified_pipeline.py           # Main orchestrator ⭐ MAIN ENTRY POINT
crypto_etl_pipeline.py        # Cryptocurrency pipeline
bond_etl_pipeline.py          # Bond pipeline
commodity_etl_pipeline.py     # Commodity pipeline
economic_etl_pipeline.py      # Economic indicators pipeline
sec_etl_pipeline.py           # SEC filings pipeline
pipeline.py                   # Legacy pipeline runner
```

### **✅ MUST COPY - Configuration Files**
```
requirements.txt              # ⭐ CRITICAL: All dependencies
.env                          # ⭐ CRITICAL: SMTP credentials & API keys
.env.example                  # Template for reference
```

### **✅ SHOULD COPY - Documentation**
```
README.md                     # Project overview
QUICKSTART.md                 # Quick start guide
DEPLOYMENT_CHECKLIST.md       # This file
EMAIL_NOTIFICATIONS.md        # Email setup docs
EMAIL_SETUP_DEPLOYMENT.md     # Email deployment guide
MCP_SERVER_README.md          # MCP server docs
TESTING_GUIDE.md              # Testing procedures
```

### **❌ DO NOT COPY - Development Only**
```
venv/                         # Virtual environments
venv_test/
__pycache__/                  # Python caches
*.pyc, *.pyo                  # Compiled Python

test_*.py                     # Local test scripts (optional - for testing on server)
  ├── test_all_sources.py
  ├── test_bonds.py
  ├── test_crypto.py
  ├── test_email_notifications.py  # Keep for server verification!
  ├── test_economic_indicators.py
  └── test_mcp_client.py

debug_*.py                    # Debug scripts (optional)
*_example.py                  # Example scripts (optional)
rag_*.py                      # RAG demo files (optional)

Resume.md                     # Personal resume
logs/                         # Log files (will be created)
data/*.db                     # Database files (will be created)
data/chromadb/               # Chroma database (will be created)

Markdown docs (optional):
  ├── CURRENT_STATUS.md
  ├── UPDATES.md
  ├── overview-2025-12-11.md
  └── ETL-Pipeline.txt
```

---

## 📦 Deployment Commands

### **Option 1: Copy Everything Needed (Recommended)**
```bash
# Create directory on server
ssh user@your-server 'mkdir -p /opt/financial-data'

# Copy project (excludes git history and pycache)
scp -r \
  --exclude=venv \
  --exclude=venv_test \
  --exclude=__pycache__ \
  --exclude=.git \
  --exclude=.pytest_cache \
  --exclude=.coverage \
  --exclude='*.pyc' \
  --exclude='*.db' \
  --exclude='*.sqlite' \
  --exclude='logs/*' \
  --exclude='Resume.md' \
  /home/archy/Desktop/Server/FinancialData/financial_data_aggregator \
  user@your-server:/opt/financial-data/
```

### **Option 2: Minimal Deployment**
If you want only production files:
```bash
# Create on server
ssh user@your-server 'mkdir -p /opt/financial-data/{src,config,dashboard}'

# Copy essentials only
scp -r src/ config/, requirements.txt, unified_pipeline.py, \
    crypto_etl_pipeline.py, bond_etl_pipeline.py, \
    commodity_etl_pipeline.py, economic_etl_pipeline.py \
    user@your-server:/opt/financial-data/

# Copy config files (MANUALLY set .env with actual credentials)
scp .env.example user@your-server:/opt/financial-data/.env
```

---

## 🔐 Post-Deployment Setup

### **1. Install Dependencies**
```bash
ssh user@your-server
cd /opt/financial-data

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install packages
pip install -r requirements.txt
```

### **2. Configure Environment**
```bash
# CRITICAL: Edit .env with actual credentials
nano .env

# Must set:
# SENDER_EMAIL=your-email@gmail.com
# SENDER_PASSWORD=your-app-password
# RECIPIENT_EMAIL=your-email@gmail.com
# API keys (ALPHA_VANTAGE_KEY, FRED_API_KEY, etc.)

# Set restrictive permissions
chmod 600 .env
```

### **3. Test on Server**
```bash
source venv/bin/activate

# Test email notifications first
python test_email_notifications.py

# Test bonds pipeline
python unified_pipeline.py --bonds

# Test all pipelines
python unified_pipeline.py --all
```

### **4. Set Up Cron Jobs**
```bash
crontab -e

# Add these lines:
0 1 * * * cd /opt/financial-data && source venv/bin/activate && python unified_pipeline.py --crypto 2>&1
0 3 * * * cd /opt/financial-data && source venv/bin/activate && python unified_pipeline.py --bonds --economic 2>&1
0 5 * * * cd /opt/financial-data && source venv/bin/activate && python unified_pipeline.py --commodities 2>&1
0 6 * * * cd /opt/financial-data && source venv/bin/activate && python unified_pipeline.py --stocks 2>&1
```

---

## 📊 File Size Reference

| Item | Size | Required? |
|------|------|-----------|
| `src/` | ~200 KB | ✅ YES |
| `config/` | ~50 KB | ✅ YES |
| `dashboard/` | ~100 KB | ✅ YES |
| `requirements.txt` | ~5 KB | ✅ YES |
| `.env` | ~1 KB | ✅ YES |
| `venv/` | ~500+ MB | ❌ NO |
| `venv_test/` | ~500+ MB | ❌ NO |
| `__pycache__/` | ~50+ MB | ❌ NO |
| `data/chromadb/` | ~100 MB | ❌ NO |
| `*.db` files | Variable | ❌ NO (created on server) |

**Total minimal deployment: ~400 KB**  
**Total with docs: ~500 KB**  
**DO NOT copy: ~1+ GB** ← Save bandwidth!

---

## ✅ Verification Checklist

After deployment on server, verify:

- [ ] `src/` directory exists with all modules
- [ ] `config/pipeline_config.yaml` present and readable
- [ ] `.env` file exists with credentials (chmod 600)
- [ ] `unified_pipeline.py` is executable
- [ ] `requirements.txt` installed in venv
- [ ] `test_email_notifications.py` runs successfully
- [ ] `unified_pipeline.py --bonds` completes without errors
- [ ] Email notifications received
- [ ] Cron jobs created and showing in `crontab -l`
- [ ] Logs directory created with permissions
- [ ] Database created (`data/financial_data.db`)

---

## 🆘 Troubleshooting

**Error: "ModuleNotFoundError: No module named 'src'"**
- Solution: Make sure you're in `/opt/financial-data/` when running
- Check: `ls -la src/` should show subdirectories

**Error: ".env file not found"**
- Solution: Copy `.env.example` to `.env` and edit
- Command: `cp .env.example .env && nano .env`

**Error: "Email not sending"**
- Solution: Run `python test_email_notifications.py`
- Check: `.env` has correct SENDER_PASSWORD (App Password, not main password)

**Error: "ModuleNotFoundError" for dependencies**
- Solution: Reinstall requirements.txt
- Command: `pip install -r requirements.txt`

---

## 📝 Summary

**Minimum for production:** ~400 KB
```
✅ src/                       (source code)
✅ config/                    (settings)
✅ dashboard/                 (web interface)
✅ *.py files                 (pipelines)
✅ requirements.txt           (dependencies)
✅ .env                       (credentials)
```

**NOT needed:** venv/, __pycache__, *.db, logs/
