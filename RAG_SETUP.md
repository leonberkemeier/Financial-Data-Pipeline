# RAG Demo Setup Guide

## 🔧 Configuration

### 1. Update Your `.env` File

Copy `.env.example` if you haven't already:
```bash
cp .env.example .env
```

Edit `.env` and add your Ollama host:
```bash
# Ollama Configuration (for RAG demo)
# Point to your Ollama server (local or via Tailscale)
OLLAMA_HOST=http://100.x.x.x:11434  # <-- Replace with your Tailscale IP

# RAG Configuration
RAG_LLM_MODEL=llama3.1:8b
RAG_EMBEDDING_MODEL=nomic-embed-text
RAG_TOP_K_RESULTS=3
```

**Finding Your Ollama Tailscale IP:**
```bash
# On your dev machine
tailscale status | grep ai-server
# Or
ping ai-server.tail12345.ts.net
```

### 2. Ensure Ollama is Accessible

**On your AI server (RTX 3060):**
```bash
# Make sure Ollama listens on all interfaces
# Check/edit: /etc/systemd/system/ollama.service
# Should have: OLLAMA_HOST=0.0.0.0:11434

# Restart if needed
sudo systemctl restart ollama

# Pull required models
ollama pull llama3.1:8b
ollama pull nomic-embed-text

# Test
ollama list
```

**From your dev machine:**
```bash
# Test connection (replace with your Tailscale IP)
curl http://100.x.x.x:11434/api/tags

# Should return JSON with list of models
```

### 3. Install RAG Dependencies

```bash
cd /home/archy/Desktop/Server/FinancialData/financial_data_aggregator
source venv/bin/activate

pip install chromadb ollama
```

## 🚀 Usage

### Initialize (Create Embeddings)
```bash
# This fetches all SEC filings from your database and creates embeddings
python rag_demo.py --init

# Expected output:
# Creating embeddings for 12 filings...
# [█████████████████████] 12/12 filings processed
# Embeddings saved to ./data/chromadb/
```

### Ask Questions
```bash
# Single question
python rag_demo.py --query "What are Apple's main cybersecurity risks?"

# Interactive mode
python rag_demo.py --interactive
```

## 📊 Example Session

```bash
$ python rag_demo.py --query "What are Apple's main risks?"

🔍 Searching SEC filings...
✓ Found 3 relevant sections from AAPL 10-K (2024-10-31)

🤖 Generating answer...

Answer:
According to Apple's 2024 10-K filing, their main risks include:

1. **Competition**: Intense competition in the smartphone, tablet, and 
   personal computer markets from companies with significant resources.

2. **Supply Chain**: Dependencies on single-source suppliers and 
   component shortages, particularly for semiconductors.

3. **Geopolitical Risks**: Exposure to trade tensions and regulatory 
   changes, especially related to China operations.

4. **Cybersecurity**: Risks from increasingly sophisticated attacks 
   targeting customer data and intellectual property.

5. **Regulatory Compliance**: Increasing scrutiny on app store practices,
   privacy policies, and antitrust concerns across multiple jurisdictions.

📚 Sources:
- AAPL 10-K 2024-10-31, Item 1A: Risk Factors
- Filing URL: https://www.sec.gov/...
```

## 🛡️ Security Notes

✅ **Your `.env` file is gitignored** - Tailscale IPs won't be committed  
✅ **Tailscale provides encrypted tunnel** - Traffic is secure  
✅ **No cloud APIs needed** - Everything runs on your infrastructure  

## 🔧 Troubleshooting

### "Connection refused" error
```bash
# Check Ollama is running on AI server
ssh ai-server
systemctl status ollama

# Check firewall (Tailscale usually handles this)
sudo ufw status
```

### "Model not found" error
```bash
# On AI server, pull the model
ollama pull llama3.1:8b
ollama pull nomic-embed-text
```

### Embeddings taking too long
```bash
# Start with fewer filings for testing
python rag_demo.py --init --limit 3

# Or process specific ticker
python rag_demo.py --init --ticker AAPL
```

## 📈 Performance

**Embedding Generation:**
- ~5-10 seconds per filing (depends on text length)
- One-time cost (reuse embeddings)
- ~10MB disk space for 10 filings

**Question Answering:**
- Vector search: <100ms
- LLM generation: 2-5 seconds (depends on GPU)
- Total: ~3-6 seconds per question

## 🎯 Next Steps

After the basic demo works:
1. Add web UI for RAG queries
2. Implement conversation history
3. Add multi-document comparison
4. Build sentiment analysis on top of RAG

---

**Note:** Keep your `.env` file secure and never commit it to Git!
