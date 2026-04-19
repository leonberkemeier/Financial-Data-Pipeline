# Target System Architecture: Context & Overview

**Overall Project Summary:**
This project is a hybrid AI-driven Robo-Advisory and Portfolio Management system. It strictly separates high-frequency numerical data from unstructured qualitative intelligence to prevent LLM hallucinations. The architecture is divided into 6 core pillars:
1. **Nervous System (financial_data_aggregator):** Data aggregation via PostgreSQL, RAG, and an MCP layer.
2. **Regime Brain (model_regime_comparison):** HMM-based market state detection and Monte Carlo VaR simulations.
3. **Conviction Synthesis (model_regime_comparison):** LLM analysis fusing quantitative data and qualitative narratives.
4. **Risk-Factor Envelopes (model_regime_comparison):** Portfolio creation using strict Strategic Asset Allocation (SAA) and Factor filters.
5. **Gap-Filler Engine (model_regime_comparison):** Priority queue system handling practical recurring deposits (DCA) and fee-efficient rebalancing.
6. **Mirror Ledger (Trading_Simulator):** High-fidelity trading simulation app offering AI-driven monthly post-mortems.

---

## 1. Data Aggregation: The "Nervous System"
*(Housed in this module)*

We implement a hybrid architecture separating high-frequency numerical data from unstructured intelligence.

### Quantitative Store (SQL/MCP)
*   **Scope:** End-of-Day (EOD) data for 650 stocks, commodities, and crypto.
*   **Structure:** PostgreSQL handles OHLCV data, dividends, and corporate actions.
*   **The MCP Layer:** An MCP Server exposes tools like `get_current_metrics(ticker)` and `get_regime_state()`. This acts as a protective layer allowing the LLM to query "Ground Truth" without direct SQL access, preventing data hallucination.

### Qualitative Store (Structured RAG)
*   **Ingestion:** Filings (10-K/Q) and transcripts are first processed by an LLM to extract a Standardized Fact Sheet (JSON).
*   **Storage:** Structured summaries are stored in a Vector Database (e.g., Pinecone, Milvus, or pgvector).
*   **Benefit:** Ensures that when the LLM compares two stocks, it compares "Apples to Apples" based on a central prompt logic.