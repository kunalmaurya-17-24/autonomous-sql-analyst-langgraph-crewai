from langgraph.graph import StateGraph, START, END
from LangGRAPH_SQL.rate_limiter_utils import rate_limiter
from typing import Dict, Any, TypedDict, Annotated, List, Optional
from operator import add
import pickle
import os
import re
import logging
import ast # Added for safe parsing
import time
import pandas as pd
from sqlalchemy import create_engine, text
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# Configure Logging
LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, f"sql_pipeline_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.log")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),
        logging.StreamHandler()  # Also print to console
    ]
)
logger = logging.getLogger(__name__)


# Import components from existing scripts
from LangGRAPH_SQL.router_agent import agent_2
from LangGRAPH_SQL.customer_agent import graph_final
from LangGRAPH_SQL.customer_helper import chain_filter_extractor, chain_query_extractor, chain_query_validator
from LangGRAPH_SQL.fuzzy_wuzzy import call_match

# Configuration and Initialization
# Simplified for Finance DB
d_store = {
    "finance": ['transactions', 'budgets', 'recurring_subscriptions']
}

# Get current directory to load relative files
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))

# Load Knowledge Base
kb_path = os.path.join(CURRENT_DIR, 'kb.pkl')
with open(kb_path, 'rb') as f:
    loaded_dict = pickle.load(f)

# SQLite Engine for Finance DB
db_path = os.path.join(os.path.dirname(CURRENT_DIR), 'finance.db')
engine = create_engine(f'sqlite:///{db_path}')

# State Definition
class FinalState(TypedDict):
    user_query: str
    router_out: List[str]
    cust_out: Optional[Dict[str, Any]]
    order_out: Optional[Dict[str, Any]]
    product_out: Optional[Dict[str, Any]]
    filtered_col: str
    filter_extractor: List[Any]
    fuzz_match: List[Any]
    sql_query: str
    final_query: str

def remove_duplicates(f: Dict[str, Any]) -> List[Any]:
    s = set()
    final = []
    for k, v in f.items():
        if k in ('cust_out', 'order_out', 'product_out') and v:
            # Domain graphs return a state containing 'column_extract'
            for item in v.get('column_extract', []):
                key = tuple(item)
                if key not in s:
                    final.append(item)
                    s.add(key)
    return final

# --- Nodes ---

def router_node(state: FinalState):
    start_time = time.time()
    q = state['user_query']
    logger.info(f"Router Node: Starting execution")
    logger.info(f"User Query: '{q}'")
    
    try:
        rate_limiter.check_and_wait()
        o = agent_2(q)
        # clean the output if it has markdown code blocks
        cleaned_o = o.replace('```json', '').replace('```', '').strip()
        try:
            parsed_o = ast.literal_eval(cleaned_o)
        except Exception as e:
            logger.error(f"Failed to parse router output: {o}. Error: {e}", exc_info=True)
            parsed_o = [] # Fallback to empty list or default
            
        res = {"router_out": parsed_o}
        logger.info(f"Router Node: Routed to {res['router_out']}")
        logger.info(f"[SUCCESS] Router Node: Completed in {time.time() - start_time:.2f}s")
        return res
    except Exception as e:
        logger.error(f"[ERROR] Router Node failed: {str(e)}", exc_info=True)
        raise

def route_request(state: FinalState):
    routes = state['router_out']
    logger.info(f"Routing to agents: {routes}")
    return routes

def filter_condition(state: FinalState):
    if len(state.get('filter_extractor', [])) <= 1: # Adjusting logic based on observed behavior
        # Note: router output check logic might vary based on how 'yes/no' is returned
        # In the notebook it was len(...) == 1.
        return "no"
    else:
        return "yes"

def finance_node(state: FinalState):
    start_time = time.time()
    q = state['user_query']
    logger.info("Finance Node: Starting table/column extraction")
    
    try:
        sub = graph_final.invoke({"user_query": q, "table_lst": d_store['finance']})
        res = {"order_out": sub}
        logger.info(f"Finance Node: Extracted {len(sub.get('column_extract', []))} columns")
        logger.info(f"[SUCCESS] Finance Node: Completed in {time.time() - start_time:.2f}s")
        return res
    except Exception as e:
        logger.error(f"[ERROR] Finance Node failed: {str(e)}", exc_info=True)
        raise

def filter_check_node(state: FinalState):
    start_time = time.time()
    q = state['user_query']
    logger.info("Filter Check Node: Starting filter analysis")
    
    try:
        f = {}
        for key in ['order_out', 'cust_out', 'product_out']:
            if key in state and state[key]:
                f[key] = state[key]
                
        col_details = remove_duplicates(f)
        logger.info(f"Filter Check Node: Analyzing {len(col_details)} columns")
        rate_limiter.check_and_wait()
        response = chain_filter_extractor.invoke({"columns": str(col_details), "query": q})
        # clean the output if it has markdown code blocks
        cleaned_response = response.replace('```json', '').replace('```', '').strip()
        
        try:
            parsed_response = ast.literal_eval(cleaned_response)
        except:
            parsed_response = ["no"]
            logger.warning(f"Filter Check Node: Failed to parse response: {response}, using default 'no'", exc_info=True)
            
        res = {'filter_extractor': parsed_response, 'filtered_col': str(col_details)}
        logger.info(f"Filter Check Node: Filter needed = {len(parsed_response) > 1}")
        logger.info(f"[SUCCESS] Filter Check Node: Completed in {time.time() - start_time:.2f}s")
        return res
    except Exception as e:
        logger.error(f"[ERROR] Filter Check Node failed: {str(e)}", exc_info=True)
        raise

def fuzz_match_node(state: FinalState):
    start_time = time.time()
    val = state['filter_extractor']
    logger.info("Fuzz Match Node: Starting fuzzy matching for filters")
    
    try:
        lst = call_match(val)
        logger.info(f"Fuzz Match Node: Matched {len(lst)} filter values")
        logger.info(f"[SUCCESS] Fuzz Match Node: Completed in {time.time() - start_time:.2f}s")
        return {"fuzz_match": lst}
    except Exception as e:
        logger.error(f"[ERROR] Fuzz Match Node failed: {str(e)}", exc_info=True)
        raise

def query_generation_node(state: FinalState):
    start_time = time.time()
    q = state['user_query']
    tab_cols = state['filtered_col']
    filters = state.get('fuzz_match', '')
    logger.info("Query Generation Node: Generating SQL query")
    
    try:
        rate_limiter.check_and_wait()
        final_query = chain_query_extractor.invoke({"columns": tab_cols, "query": q, "filters": filters})
        logger.info(f"Query Generation Node: Generated query (first 100 chars): {final_query[:100]}...")
        logger.info(f"[SUCCESS] Query Generation Node: Completed in {time.time() - start_time:.2f}s")
        return {"sql_query": final_query}
    except Exception as e:
        logger.error(f"[ERROR] Query Generation Node failed: {str(e)}", exc_info=True)
        raise

def query_validation_node(state: FinalState):
    start_time = time.time()
    logger.info("Query Validation Node: Validating SQL query")
    
    try:
        # Load KB for validation context
        import pickle
        import os
        # kb.pkl is generated in LangGRAPH_SQL folder
        kb_path = os.path.join('LangGRAPH_SQL', 'kb.pkl')
        with open(kb_path, 'rb') as f:
            kb = pickle.load(f)

        rate_limiter.check_and_wait()
        o = chain_query_validator.invoke({
            "columns": state['filtered_col'], 
            "user_query": state['user_query'], 
            "filters": state.get('fuzz_match'), 
            "sql_query": state['sql_query'],
            "all_table_info": str(kb) # Pass full schema
        })
        
        # PERMANENT FIX: Extract SQL code block if present
        import re
        def clean_sql_output(text):
            # Regex to find content inside ```sql ... ``` (case insensitive)
            match = re.search(r"```sql\s*(.*?)\s*```", text, re.DOTALL | re.IGNORECASE)
            if match:
                return match.group(1).strip()
            # Fallback: check for just ``` ... ```
            match_generic = re.search(r"```\s*(.*?)\s*```", text, re.DOTALL)
            if match_generic:
                return match_generic.group(1).strip()
            return text.strip()

        cleaned_query = clean_sql_output(o)
        
        if cleaned_query != o.strip():
             logger.warning("Query Validation Node: Cleaned markdown formatting from SQL output.")

        logger.info(f"Query Validation Node: Query validated successfully")
        logger.info(f"[SUCCESS] Query Validation Node: Completed in {time.time() - start_time:.2f}s")
        return {'final_query': cleaned_query}
    except Exception as e:
        logger.error(f"[ERROR] Query Validation Node failed: {str(e)}", exc_info=True)
        raise

def safe_executor_node(state: FinalState):
    """
    Executes the validated SQL query safely.
    """
    start_time = time.time()
    query = state['final_query']
    logger.info("Safe Executor Node: Starting SQL execution")
    
    import re
    # Aggressive cleaning of the SQL query
    # 1. Extract block from ```sql ... ``` or ```mysql ... ```
    sql_match = re.search(r'```(?:sql|mysql)?\n(.*?)\n```', query, re.DOTALL | re.IGNORECASE)
    if sql_match:
        sql_to_run = sql_match.group(1)
    else:
        sql_to_run = query

    # 2. Strip "mysql" word if it appears at the start (common 2.5 flash quirk)
    sql_to_run = re.sub(r'(?i)^\s*mysql\s*', '', sql_to_run)
    
    # 3. If there is still conversational text, try to find the first WITH/SELECT
    # This is a fallback if the regex above failed or if there were no code blocks
    match_start = re.search(r'(?i)\b(WITH|SELECT)\b', sql_to_run)
    if match_start:
         sql_to_run = sql_to_run[match_start.start():]

    # 4. Final Cleanup
    sql_to_run = sql_to_run.replace('```', '').strip()
    
    logger.info(f"Executing SQL: {sql_to_run[:200]}...")

    try:
        with engine.connect() as connection:
            # Execute and fetch limit (e.g., 50 rows)
            result = connection.execute(text(sql_to_run))
            columns = result.keys()
            rows = result.fetchmany(50)
            
            if not rows:
                logger.warning("Safe Executor Node: Query executed but returned no results")
                return {"sql_query": "No results found for this query."}
            
            # Format as Markdown Table
            md_table = f"| {' | '.join(columns)} |\n"
            md_table += f"| {' | '.join(['---'] * len(columns))} |\n"
            for row in rows:
                md_table += f"| {' | '.join(map(str, row))} |\n"
            
            logger.info(f"Safe Executor Node: Successfully retrieved {len(rows)} rows")
            logger.info(f"[SUCCESS] Safe Executor Node: Completed in {time.time() - start_time:.2f}s")
            return {"sql_query": md_table}
    except Exception as e:
        logger.error(f"[ERROR] Safe Executor Node failed during SQL execution: {str(e)}", exc_info=True)
        return {"sql_query": f"Error during execution: {str(e)}"}

# --- Graph Construction ---

builder_final = StateGraph(FinalState)

builder_final.add_node("finance", finance_node)
builder_final.add_node("filter_check", filter_check_node)
builder_final.add_node("fuzz_filter", fuzz_match_node)
builder_final.add_node("query_generator", query_generation_node)
builder_final.add_node("query_validation", query_validation_node)
builder_final.add_node("safe_executor", safe_executor_node)

builder_final.add_edge(START, "finance") # Bypassing router for now as it's a specialized finance bot
builder_final.add_edge("finance", "filter_check")

builder_final.add_conditional_edges(
    "filter_check",
    filter_condition,
    {
        "no": "query_generator",
        "yes": "fuzz_filter"
    }
)

builder_final.add_edge("fuzz_filter", "query_generator")
builder_final.add_edge("query_generator", "query_validation")
builder_final.add_edge("query_validation", "safe_executor")
builder_final.add_edge("safe_executor", END)

# Compile the graph
sql_pipeline_app = builder_final.compile()

def run_sql_pipeline(query: str) -> str:
    """
    Entry point for the SQL generation and execution pipeline.
    """
    pipeline_start = time.time()
    logger.info("="*70)
    logger.info("SQL PIPELINE STARTED")
    logger.info("="*70)
    logger.info(f"User Query: '{query}'")
    logger.info(f"Log File: {LOG_FILE}")
    
    try:
        result = sql_pipeline_app.invoke({"user_query": query})
        execution_time = time.time() - pipeline_start
        
        logger.info("="*70)
        logger.info(f"[SUCCESS] PIPELINE COMPLETED in {execution_time:.2f}s")
        logger.info("="*70)
        
        return result.get('sql_query', "Failed to retrieve data.")
    except Exception as e:
        execution_time = time.time() - pipeline_start
        logger.error("="*70)
        logger.error(f"[FAILURE] PIPELINE FAILED after {execution_time:.2f}s")
        logger.error("="*70)
        logger.error(f"Error: {str(e)}", exc_info=True)
        return f"Error in SQL pipeline: {str(e)}"

if __name__ == "__main__":
    # Test call
    test_query = "Who are the top 5 customers from São Paulo?"
    print(run_sql_pipeline(test_query))
