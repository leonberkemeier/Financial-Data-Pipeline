#!/usr/bin/env python3
"""
Simple MCP client to test the financial server with Ollama.
This demonstrates how an LLM can use the MCP tools.
"""
import asyncio
import json
import requests
from mcp_financial_server import (
    get_latest_price,
    get_price_statistics,
    compare_stocks,
    list_available_tickers,
    get_sec_filings
)
from config.config import OLLAMA_HOST, RAG_LLM_MODEL

async def call_mcp_tool(tool_name: str, **kwargs):
    """Call an MCP tool and return the result."""
    tools = {
        'get_latest_price': get_latest_price,
        'get_price_statistics': get_price_statistics,
        'compare_stocks': compare_stocks,
        'list_available_tickers': list_available_tickers,
        'get_sec_filings': get_sec_filings
    }
    
    if tool_name not in tools:
        return f"Unknown tool: {tool_name}"
    
    result = await tools[tool_name](**kwargs)
    return json.loads(result[0].text)

def ask_llm_with_tools(question: str):
    """
    Ask the LLM a question and let it use MCP tools.
    This is a simplified version - real MCP clients handle tool calling automatically.
    """
    print(f"\n🤔 Question: {question}\n")
    
    # Define available tools for the LLM
    tools_description = """
You have access to these financial data tools:

1. get_latest_price(ticker) - Get current stock price
2. get_price_statistics(ticker, days=30) - Get price statistics over a period
3. compare_stocks(tickers, days=30) - Compare multiple stocks
4. list_available_tickers() - List all available tickers
5. get_sec_filings(ticker, filing_type=None, limit=10) - Get SEC filings

To use a tool, respond with JSON in this format:
{"tool": "tool_name", "arguments": {"param": "value"}}

If you don't need a tool, just answer directly.
"""
    
    prompt = f"""{tools_description}

User question: {question}

What tool should you use (if any) to answer this question? Respond with JSON if using a tool, or answer directly if you can."""
    
    # Ask LLM
    try:
        response = requests.post(
            f"{OLLAMA_HOST}/api/generate",
            json={
                "model": RAG_LLM_MODEL,
                "prompt": prompt,
                "stream": False
            },
            timeout=30
        )
        response.raise_for_status()
        llm_response = response.json()['response'].strip()
        
        print(f"🤖 LLM Response:\n{llm_response}\n")
        
        # Check if LLM wants to use a tool
        if llm_response.startswith('{') and '"tool"' in llm_response:
            try:
                # Extract JSON (handle markdown code blocks)
                json_str = llm_response
                if '```json' in json_str:
                    json_str = json_str.split('```json')[1].split('```')[0].strip()
                elif '```' in json_str:
                    json_str = json_str.split('```')[1].split('```')[0].strip()
                
                tool_call = json.loads(json_str)
                tool_name = tool_call['tool']
                arguments = tool_call.get('arguments', {})
                
                print(f"🔧 Calling tool: {tool_name}({arguments})\n")
                
                # Call the tool
                result = asyncio.run(call_mcp_tool(tool_name, **arguments))
                print(f"📊 Tool Result:\n{json.dumps(result, indent=2)}\n")
                
                # Give result back to LLM for final answer
                final_prompt = f"""User asked: {question}

You called the tool {tool_name} and got this result:
{json.dumps(result, indent=2)}

Now provide a natural language answer to the user's question based on this data."""
                
                response = requests.post(
                    f"{OLLAMA_HOST}/api/generate",
                    json={
                        "model": RAG_LLM_MODEL,
                        "prompt": final_prompt,
                        "stream": False
                    },
                    timeout=30
                )
                response.raise_for_status()
                final_answer = response.json()['response'].strip()
                
                print(f"💬 Final Answer:\n{final_answer}\n")
                
            except json.JSONDecodeError:
                print("⚠️  LLM response wasn't valid JSON, treating as direct answer")
        
    except Exception as e:
        print(f"❌ Error: {e}")

def main():
    """Run demo questions."""
    print("=" * 60)
    print("MCP Financial Server + LLM Demo")
    print("=" * 60)
    
    questions = [
        "What is Apple's current stock price?",
        "Compare the performance of AAPL and MSFT over the last 30 days",
        "What SEC filings does NVDA have?",
    ]
    
    for question in questions:
        ask_llm_with_tools(question)
        print("-" * 60)
    
    print("\n✅ Demo completed!")
    print("\nNote: This is a simplified demo. Real MCP clients (like Claude Desktop)")
    print("handle tool calling automatically and more intelligently.")

if __name__ == "__main__":
    main()
