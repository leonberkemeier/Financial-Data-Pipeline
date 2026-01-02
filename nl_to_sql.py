"""
Natural Language to SQL Query Engine.

Converts natural language questions into SQL queries against the star schema.
"""
import os
import requests
from sqlalchemy import create_engine, text
import pandas as pd
from typing import Dict, List, Tuple
from loguru import logger

from config.config import DATABASE_URL, OLLAMA_HOST, RAG_LLM_MODEL


class NLToSQLEngine:
    """Convert natural language to SQL queries."""
    
    def __init__(self):
        """Initialize the NL to SQL engine."""
        self.engine = create_engine(DATABASE_URL)
        self.ollama_host = OLLAMA_HOST.rstrip('/')
        
        # Database schema information for the LLM
        self.schema_info = """
# Star Schema Database Structure

## Dimension Tables:

### dim_company (Stocks)
- company_id (PK), ticker, company_name, sector, industry, country

### dim_crypto_asset (Cryptocurrencies)  
- crypto_id (PK), symbol, name, chain, description

### dim_commodity (Commodities)
- commodity_id (PK), symbol, name, category, unit, exchange, source

### dim_bond (Bonds)
- bond_id (PK), isin, issuer_id, bond_type, maturity_date, coupon_rate

### dim_economic_indicator (Economic Data)
- indicator_id (PK), indicator_code, indicator_name, category, unit, frequency

### dim_date (Dates)
- date_id (PK), date, year, month, day, quarter, day_of_week, day_name

### dim_data_source (Data Sources)
- source_id (PK), source_name, source_type

## Fact Tables:

### fact_stock_price (Stock Prices)
- price_id (PK), company_id (FK), date_id (FK), source_id (FK)
- open_price, high_price, low_price, close_price, adjusted_close, volume
- price_change, price_change_percent

### fact_crypto_price (Crypto Prices)
- crypto_price_id (PK), crypto_id (FK), date_id (FK), source_id (FK)
- price (NOT close_price!), market_cap, trading_volume, circulating_supply, total_supply
- price_change_24h, price_change_7d

### fact_commodity_price (Commodity Prices)
- commodity_price_id (PK), commodity_id (FK), date_id (FK), source_id (FK)
- open_price, high_price, low_price, close_price, volume
- price_change, price_change_percent

### fact_bond_price (Bond Prices)
- bond_price_id (PK), bond_id (FK), date_id (FK), source_id (FK)
- price, yield_percent, spread, duration

### fact_economic_indicator (Economic Indicators)
- economic_data_id (PK), indicator_id (FK), date_id (FK), source_id (FK)
- value

## Important Notes:
- Always JOIN fact tables with dim_date to get actual dates
- Use appropriate JOINs to get ticker/symbol/name from dimension tables
- For time ranges, filter on dim_date.date
- SQLite syntax (use date() function, LIMIT not TOP)
"""
    
    def generate_sql(self, question: str) -> Dict:
        """
        Generate SQL query from natural language question.
        
        Args:
            question: Natural language question
            
        Returns:
            Dict with 'sql', 'explanation', and 'success' keys
        """
        logger.info(f"Converting to SQL: {question}")
        
        prompt = f"""You are a SQL expert. Convert this natural language question into a SQL query for a financial data warehouse.

Database Schema:
{self.schema_info}

Question: {question}

Requirements:
1. Generate ONLY valid SQLite SQL (no PostgreSQL/MySQL specific syntax)
2. Use proper JOINs between fact and dimension tables
3. Always include column names in SELECT (no SELECT *)
4. Use meaningful aliases for readability - BE CONSISTENT! If you alias a table, use that alias everywhere
5. For date filtering, use dim_date.date with proper date format
6. Limit results to reasonable amounts (use LIMIT)
7. Order results by date DESC for time series
8. CRITICAL: Check your aliases! Make sure every column reference uses the correct table alias
9. Example correct aliases: fact_stock_price AS f, dim_company AS c, dim_date AS d

Example with CORRECT alias usage:
"Show recent Apple stock prices"
SELECT c.company_name, d.date, f.close_price, f.volume 
FROM fact_stock_price f 
JOIN dim_company c ON f.company_id = c.company_id 
JOIN dim_date d ON f.date_id = d.date_id 
WHERE c.ticker = 'AAPL' 
ORDER BY d.date DESC 
LIMIT 10;
Note: fact_stock_price is aliased as 'f' and ALL references to it use 'f' (f.close_price, f.volume, f.company_id, f.date_id).

Respond in this EXACT format:
SQL:
<your SQL query here>

EXPLANATION:
<brief explanation of what the query does>

Do not include any other text, formatting, or code blocks. Start directly with "SQL:" followed by the query."""

        try:
            response = requests.post(
                f"{self.ollama_host}/api/generate",
                json={"model": RAG_LLM_MODEL, "prompt": prompt, "stream": False},
                timeout=60
            )
            response.raise_for_status()
            
            result_text = response.json()['response']
            
            # Parse the response
            sql_query = ""
            explanation = ""
            
            if "SQL:" in result_text and "EXPLANATION:" in result_text:
                parts = result_text.split("EXPLANATION:")
                sql_part = parts[0].replace("SQL:", "").strip()
                explanation = parts[1].strip()
                
                # Clean up SQL (remove markdown code blocks if present)
                sql_query = sql_part.replace("```sql", "").replace("```", "").strip()
            else:
                logger.warning("Could not parse LLM response properly")
                return {
                    'success': False,
                    'error': 'Failed to parse LLM response',
                    'raw_response': result_text
                }
            
            logger.info(f"Generated SQL: {sql_query[:100]}...")
            
            return {
                'success': True,
                'sql': sql_query,
                'explanation': explanation
            }
            
        except Exception as e:
            logger.error(f"Failed to generate SQL: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def execute_sql(self, sql_query: str, limit: int = 100) -> Dict:
        """
        Execute SQL query and return results.
        
        Args:
            sql_query: SQL query to execute
            limit: Maximum number of rows to return
            
        Returns:
            Dict with 'success', 'data', 'columns', and 'row_count' keys
        """
        try:
            # Safety check: only allow SELECT queries
            sql_lower = sql_query.lower().strip()
            if not sql_lower.startswith('select'):
                return {
                    'success': False,
                    'error': 'Only SELECT queries are allowed for security'
                }
            
            # Add LIMIT if not present
            if 'limit' not in sql_lower:
                sql_query = f"{sql_query.rstrip(';')} LIMIT {limit}"
            
            logger.info(f"Executing SQL: {sql_query}")
            
            # Execute query
            with self.engine.connect() as conn:
                result = pd.read_sql(text(sql_query), conn)
            
            logger.info(f"Query returned {len(result)} rows")
            
            return {
                'success': True,
                'data': result.to_dict('records'),
                'columns': result.columns.tolist(),
                'row_count': len(result)
            }
            
        except Exception as e:
            logger.error(f"SQL execution error: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def query(self, question: str) -> Dict:
        """
        Full pipeline: Generate SQL from question and execute it.
        
        Args:
            question: Natural language question
            
        Returns:
            Dict with complete results including SQL, data, and explanation
        """
        # Generate SQL
        sql_result = self.generate_sql(question)
        
        if not sql_result['success']:
            return sql_result
        
        # Execute SQL
        exec_result = self.execute_sql(sql_result['sql'])
        
        # Combine results
        return {
            'success': exec_result['success'],
            'question': question,
            'sql': sql_result['sql'],
            'explanation': sql_result['explanation'],
            'data': exec_result.get('data', []),
            'columns': exec_result.get('columns', []),
            'row_count': exec_result.get('row_count', 0),
            'error': exec_result.get('error')
        }


def main():
    """Test the NL to SQL engine."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Natural Language to SQL')
    parser.add_argument('question', type=str, help='Natural language question')
    parser.add_argument('--sql-only', action='store_true', help='Only generate SQL, do not execute')
    
    args = parser.parse_args()
    
    engine = NLToSQLEngine()
    
    if args.sql_only:
        result = engine.generate_sql(args.question)
        if result['success']:
            print("SQL Query:")
            print(result['sql'])
            print("\nExplanation:")
            print(result['explanation'])
        else:
            print(f"Error: {result.get('error')}")
    else:
        result = engine.query(args.question)
        if result['success']:
            print(f"\nQuestion: {result['question']}")
            print(f"\nGenerated SQL:\n{result['sql']}")
            print(f"\nExplanation:\n{result['explanation']}")
            print(f"\nResults ({result['row_count']} rows):")
            
            # Print as table
            if result['data']:
                df = pd.DataFrame(result['data'])
                print(df.to_string(index=False))
        else:
            print(f"Error: {result.get('error')}")


if __name__ == '__main__':
    main()
