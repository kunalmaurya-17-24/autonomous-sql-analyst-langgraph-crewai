from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough, RunnableMap, RunnableLambda
import pickle
import re
import ast
import logging

logger = logging.getLogger(__name__)
from LangGRAPH_SQL.rate_limiter_utils import rate_limiter

from langgraph.graph import StateGraph, START, END
from typing import Dict, Any, TypedDict, Annotated
from operator import add

from LangGRAPH_SQL.customer_helper import *
from IPython.display import Image

from dotenv import load_dotenv

load_dotenv()

with open('E:\\sql_crew\\LangGRAPH_SQL\\kb.pkl', 'rb') as f:
    loaded_dict = pickle.load(f)

d_store = {
    "customer" : ['customer', 'sellers'],
    "orders" : ['order_items', 'order_payments', 'order_reviews', 'orders'],
    "product": ["products", "category_translation"]
}

class overallstate(TypedDict):
    user_query: str
    table_lst: list[str]
    table_extract : Annotated[list[str], add]
    column_extract : Annotated[list[str], add]


def agent_subquestion(q,v):
    rate_limiter.check_and_wait()
    response = chain_subquestion.invoke({"tables": v, "user_query": q}).replace('```', '')
    match = re.search(r"\[\s*\[.*?\]\s*(,\s*\[.*?\]\s*)*\]", response, re.DOTALL)
    if match:
        result = match.group(0)
    return result

def solve_subquestion(q, lst):
    final = []
    for tab in lst:
        desc = loaded_dict[tab][0]
        final.append([tab, desc])
    
    result_dict = {item[0]: item[1] for item in final}

    subquestion = agent_subquestion(q, str(result_dict))
    return subquestion



def agent_column_selection(mq, q,c):
    rate_limiter.check_and_wait()
    response = chain_column_extractor.invoke({"columns": c, "query": q, "main_question":mq}).replace('```', '')

    match = re.search(r"\[\s*\[.*?\]\s*(,\s*\[.*?\]\s*)*\]", response, re.DOTALL)
    if match:
        result = match.group(0)
    else:
        result = '[[]]'
    return result


def solve_column_selection(main_q, list_sub):
    final_col = []
    inter = []
    for tab in list_sub:
        if len(tab)==0:
            continue
        table_name = tab[1]
        question = tab[0]
        columns = loaded_dict[table_name][1]
        out_column = agent_column_selection(main_q, question, str(columns))
        # clean the output if it has markdown code blocks
        cleaned_out = out_column.replace('```json', '').replace('```', '').strip()
        try:
            trans_col = ast.literal_eval(cleaned_out)
        except Exception as e:
            logger.error(f"Failed to parse column selection output: {out_column}. Error: {e}")
            trans_col = []

        for col_selec in trans_col:
            new_col = ["name of table:" + table_name] + col_selec
            inter.append(new_col)
        final_col.extend(inter)
    return final_col


def sq_node(state: overallstate):
    q = state['user_query']
    lst = state['table_lst']
    o = solve_subquestion(q, lst)
    # clean the output if it has markdown code blocks
    cleaned_o = o.replace('```json', '').replace('```', '').strip()
    try:
        parsed_o = ast.literal_eval(cleaned_o)
    except Exception as e:
        logger.error(f"Failed to parse subquestion output: {o}. Error: {e}")
        parsed_o = []
        
    return {"table_extract": parsed_o}

def column_node(state: overallstate):
    subq = state['table_extract']
    mq = state['user_query']
    
    o = solve_column_selection(mq, subq)
    return {"column_extract": o}


builder_final = StateGraph(overallstate)
builder_final.add_node("subquestion", sq_node)
builder_final.add_node("column_e", column_node)

builder_final.add_edge(START, "subquestion")
builder_final.add_edge("subquestion", "column_e")

builder_final.add_edge("column_e", END)
graph_final = builder_final.compile()


