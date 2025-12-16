#!/usr/bin/env python3
"""
Unified Financial Assistant

Combines MCP tools (price data) and RAG (SEC filing analysis) into one interface.
The LLM automatically decides which tools to use based on your question.
"""
import asyncio
import json
import sys
import argparse
import requests
from typing import Dict, Any

from mcp_financial_server import (
    get_latest_price,
    get_price_statistics,
    compare_stocks,
    list_available_tickers,
    get_sec_filings,
    search_companies
)
from rag_demo import RAGSystem
from config.config import OLLAMA_HOST, RAG_LLM_MODEL

# Available tools
TOOLS = {
    'get_latest_price': {
        'function': get_latest_price,
        'description': 'Get the most recent stock price for a ticker',
        'params': ['ticker']
    },
    'get_price_statistics': {
        'function': get_price_statistics,
        'description': 'Get price statistics (avg, min, max, volatility, returns) for a period',
        'params': ['ticker', 'days (optional, default 30)']
    },
    'compare_stocks': {
        'function': compare_stocks,
        'description': 'Compare multiple stocks side-by-side',
        'params': ['tickers (list)', 'days (optional, default 30)']
    },
    'list_available_tickers': {
        'function': list_available_tickers,
        'description': 'List all available stock tickers in the database',
        'params': []
    },
    'get_sec_filings': {
        'function': get_sec_filings,
        'description': 'Get SEC filing metadata (dates, types, URLs)',
        'params': ['ticker', 'filing_type (optional)', 'limit (optional)']
    },
    'search_companies': {
        'function': search_companies,
        'description': 'Search for companies by name, ticker, sector, or industry',
        'params': ['query']
    },
    'query_sec_filings': {
        'function': None,  # Special case - uses RAG
        'description': 'Search SEC filing text content for detailed business information, risks, MD&A, etc.',
        'params': ['question']
    }
}

async def call_tool(tool_name: str, **kwargs) -> Dict[str, Any]:
    """Call a tool and return the result."""
    if tool_name == 'query_sec_filings':
        # Use RAG system
        rag = RAGSystem()
        result = rag.query(kwargs.get('question', ''), verbose=False)
        return result
    
    if tool_name not in TOOLS:
        return {"error": f"Unknown tool: {tool_name}"}
    
    tool = TOOLS[tool_name]
    result = await tool['function'](**kwargs)
    return json.loads(result[0].text)

def build_tools_prompt() -> str:
    """Build the tools description for the LLM."""
    tools_list = []
    for name, info in TOOLS.items():
        params = ', '.join(info['params']) if info['params'] else 'none'
        tools_list.append(f"- {name}({params}): {info['description']}")
    
    return '\n'.join(tools_list)

def ask_assistant(question: str, verbose: bool = True) -> str:
    """
    Ask the financial assistant a question.
    It will automatically use MCP tools or RAG as needed.
    """
    if verbose:
        print(f"\n💬 Question: {question}\n")
    
    tools_prompt = build_tools_prompt()
    
    # First, ask LLM which tool(s) to use
    decision_prompt = f"""You are a financial data assistant with access to these tools:

{tools_prompt}

User question: {question}

Analyze the question and determine which tool(s) to use:
- For PRICE/STOCK DATA (current prices, statistics, comparisons): use MCP tools (get_latest_price, get_price_statistics, compare_stocks)
- For SEC FILING CONTENT (business risks, MD&A, detailed filing analysis): use query_sec_filings
- For LISTING/SEARCHING companies: use list_available_tickers or search_companies
- For SEC FILING METADATA (dates, types): use get_sec_filings

Respond with JSON in this format (you can call multiple tools):
{{
  "tools": [
    {{"tool": "tool_name", "arguments": {{"param": "value"}}}},
    {{"tool": "another_tool", "arguments": {{}}}}
  ],
  "reasoning": "Brief explanation of why you chose these tools"
}}

If no tools are needed, respond with: {{"tools": [], "reasoning": "..."}}"""
    
    try:
        # Get tool selection from LLM
        response = requests.post(
            f"{OLLAMA_HOST}/api/generate",
            json={
                "model": RAG_LLM_MODEL,
                "prompt": decision_prompt,
                "stream": False
            },
            timeout=30
        )
        response.raise_for_status()
        llm_response = response.json()['response'].strip()
        
        # Extract JSON
        json_str = llm_response
        if '```json' in json_str:
            json_str = json_str.split('```json')[1].split('```')[0].strip()
        elif '```' in json_str:
            json_str = json_str.split('```')[1].split('```')[0].strip()
        
        decision = json.loads(json_str)
        
        if verbose:
            print(f"🤖 Assistant reasoning: {decision['reasoning']}\n")
        
        # Execute tools
        tool_results = []
        for tool_call in decision['tools']:
            tool_name = tool_call['tool']
            arguments = tool_call.get('arguments', {})
            
            if verbose:
                print(f"🔧 Using tool: {tool_name}({arguments})")
            
            result = asyncio.run(call_tool(tool_name, **arguments))
            tool_results.append({
                'tool': tool_name,
                'result': result
            })
            
            if verbose:
                print(f"✓ Result received\n")
        
        # If no tools were used, LLM answers directly
        if not tool_results:
            if verbose:
                print("ℹ️  No tools needed, generating direct answer...\n")
            
            response = requests.post(
                f"{OLLAMA_HOST}/api/generate",
                json={
                    "model": RAG_LLM_MODEL,
                    "prompt": f"User question: {question}\n\nProvide a helpful answer:",
                    "stream": False
                },
                timeout=30
            )
            response.raise_for_status()
            answer = response.json()['response'].strip()
            
            if verbose:
                print(f"💡 Answer:\n{answer}\n")
            return answer
        
        # Generate final answer from tool results
        results_text = "\n\n".join([
            f"Tool: {r['tool']}\nResult: {json.dumps(r['result'], indent=2)}"
            for r in tool_results
        ])
        
        final_prompt = f"""User asked: {question}

You used these tools and got these results:

{results_text}

Now provide a clear, natural language answer to the user's question based on these results.
Be specific and cite the data. Format numbers nicely."""
        
        response = requests.post(
            f"{OLLAMA_HOST}/api/generate",
            json={
                "model": RAG_LLM_MODEL,
                "prompt": final_prompt,
                "stream": False
            },
            timeout=60
        )
        response.raise_for_status()
        answer = response.json()['response'].strip()
        
        if verbose:
            print(f"💡 Answer:\n{answer}\n")
        
        return answer
        
    except json.JSONDecodeError as e:
        error_msg = f"Error parsing LLM response: {e}\nResponse was: {llm_response}"
        if verbose:
            print(f"❌ {error_msg}")
        return error_msg
    except Exception as e:
        error_msg = f"Error: {e}"
        if verbose:
            print(f"❌ {error_msg}")
        return error_msg

def interactive_mode():
    """Run interactive Q&A session."""
    print("\n" + "=" * 60)
    print("💼 Financial Assistant - Interactive Mode")
    print("=" * 60)
    print("Ask questions about stock prices, SEC filings, or companies.")
    print("I'll automatically use the right tools to answer.")
    print("\nExamples:")
    print("  • What's Apple's current stock price?")
    print("  • Compare AAPL and MSFT performance")
    print("  • What are NVDA's main business risks?")
    print("  • Show me Tesla's recent SEC filings")
    print("\nType 'exit' or 'quit' to end.\n")
    
    while True:
        try:
            question = input("❓ Your question: ").strip()
            
            if question.lower() in ['exit', 'quit', 'q']:
                print("\n👋 Goodbye!")
                break
            
            if not question:
                continue
            
            ask_assistant(question, verbose=True)
            print("-" * 60 + "\n")
            
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}\n")

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Unified Financial Assistant - Combines MCP tools and RAG",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Interactive mode
  python financial_assistant.py
  
  # Single question
  python financial_assistant.py --query "What's Apple's stock price?"
  
  # Ask about SEC filings
  python financial_assistant.py --query "What are NVDA's business risks?"
  
  # Compare stocks
  python financial_assistant.py --query "Compare AAPL and MSFT performance"
        """
    )
    
    parser.add_argument(
        '--query', '-q',
        help='Ask a single question'
    )
    
    parser.add_argument(
        '--interactive', '-i',
        action='store_true',
        help='Start interactive mode (default if no query provided)'
    )
    
    args = parser.parse_args()
    
    if args.query:
        ask_assistant(args.query, verbose=True)
    else:
        interactive_mode()

if __name__ == "__main__":
    main()
