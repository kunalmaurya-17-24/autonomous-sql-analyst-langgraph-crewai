import sys
import os
from dotenv import load_dotenv
load_dotenv()

print("--- Start Comprehensive Import Test ---")

def test_import(module_path, name):
    try:
        print(f"Testing {name} ({module_path})...")
        __import__(module_path)
        print(f"✅ {name} imported successfully")
        return True
    except Exception as e:
        print(f"❌ {name} failed: {e}")
        import traceback
        traceback.print_exc()
        return False

# Test the chain
modules = [
    ("LangGRAPH_SQL.customer_helper", "Customer Helper"),
    ("LangGRAPH_SQL.router_agent", "Router Agent"),
    ("LangGRAPH_SQL.customer_agent", "Customer Agent"),
    ("LangGRAPH_SQL.graph_entry", "Graph Entry"),
    ("CrewAI.sql_tools", "SQL Tools"),
    ("CrewAI.crew", "Sql Crew"),
]

all_success = True
for path, name in modules:
    if not test_import(path, name):
        all_success = False
        break

if all_success:
    print("\n🎉 ALL IMPORTS SUCCESSFUL!")
else:
    print("\n⚠️ SOME IMPORTS FAILED.")

print("\n--- End Import Test ---")
