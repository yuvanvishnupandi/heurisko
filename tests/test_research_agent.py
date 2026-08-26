"""
Test script to run the Web Research Agent with example queries.
"""

import sys
import os
import json
import asyncio
from typing import Union

project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

try:
    from research_system.agent import run_web_research
    from research_system.schemas import ResearchReport, ErrorResponse
except ImportError as e:
    print(f"Error importing research system: {e}")
    print("Please ensure you are running this script from the project root directory,")
    print("and that the 'research_system' directory is present.")
    sys.exit(1)

def main():
    queries_to_test = [
        "What are the main challenges and opportunities for vertical farming in urban environments?",
        "Explain the concept of Retrieval-Augmented Generation (RAG) in LLMs.",
        "What are the latest developments in fusion energy research?"
    ]

    results = []
    for query in queries_to_test:
        print(f"\n--- Running Research for: '{query}' ---")
        try:
            result: Union[ResearchReport, ErrorResponse] = asyncio.run(run_web_research(query))

            print("\n--- Research Result ---")
            if isinstance(result, ResearchReport):
                print(result.model_dump_json(indent=2))
                results.append(result.model_dump())

                print("\n--- Sources ---")
                if result.sources:
                    for i, source in enumerate(result.sources):
                        print(f"{i+1}. [{source.title or 'N/A'}]({source.url}) - via {source.tool_used}")
                        print(f"   Snippet: {(source.snippet or 'N/A')[:150]}...")
                else:
                    print("No sources were found or retained in the report.")
            elif isinstance(result, ErrorResponse):
                print(f"Error Response: {result.model_dump_json(indent=2)}")
                results.append({"query": query, "error": result.error, "details": result.details})
            else:
                print(f"Unexpected result type: {type(result)}")
                results.append({"query": query, "error": "Unexpected result type", "details": str(result)})

        except Exception as e:
            print(f"\n--- ERROR Running Research for: '{query}' ---")
            print(f"An error occurred: {e}")
            import traceback
            traceback.print_exc()
            results.append({"query": query, "error": str(e)})
        print("-----------------------------------------")

    try:
        with open("research_results.json", "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False, default=str)
        print("\nResults saved to research_results.json")
    except Exception as e:
        print(f"\nError saving results to JSON file: {e}")

if __name__ == "__main__":
    main() 