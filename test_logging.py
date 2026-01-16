"""
Quick test script to verify logging system works.
This runs the LangGraph pipeline directly to test node execution logging.
"""
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from LangGRAPH_SQL.graph_entry import run_sql_pipeline

if __name__ == "__main__":
    # Test query
    test_query = "Show me all transactions from last month"
    
    print("\n" + "="*70)
    print("TESTING LOGGING SYSTEM")
    print("="*70)
    print(f"\nQuery: {test_query}\n")
    
    # Run the pipeline
    result = run_sql_pipeline(test_query)
    
    print("\n" + "="*70)
    print("RESULT:")
    print("="*70)
    print(result)
    print("\n\nCheck the logs/ directory for the timestamped log file!")
