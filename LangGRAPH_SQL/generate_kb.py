import pandas as pd
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableMap
from sqlalchemy import create_engine
import tqdm
import time
import pickle
import os
from dotenv import load_dotenv

load_dotenv()

# Finance Database Schema Description
table_description = {
    'transactions': '''Contains details of all financial transactions, including expenses and income. 
    Includes date, merchant name, amount, and category (e.g., Food, Transport, Income, Shopping, Utilities).''',
    'budgets': '''Stores monthly spending limits set by the user for various categories. 
    Crucial for identifying where someone is over-spending.''',
    'recurring_subscriptions': '''Tracks fixed monthly or yearly costs for digital services like Netflix, Spotify, or Prime. 
    Helps identify forgotten or unexpected cost increases.'''
}

# Connect to finance.db (SQLite)
# Assuming run from root: e:\sql_crew
db_path = os.path.join(os.getcwd(), 'finance.db')
engine = create_engine(f'sqlite:///{db_path}')

def read_sql(table):
    # SQLite uses RANDOM(), MySQL uses RAND()
    query = f"SELECT * FROM {table} ORDER BY RANDOM() LIMIT 5;"
    df_sample = pd.read_sql(query, con=engine)
    return df_sample


model = ChatGoogleGenerativeAI(temperature=0.4, model='gemini-2.5-flash')

template = ChatPromptTemplate.from_messages([
    ("system", """
You are an intelligent data annotator. Please annotate data as mentioned by human and give output without any verbose and without any additional explanation.
You will be given a SQL table description and sample rows from the table. 
The description you generate will be the 'context' for a Text-to-SQL system.
Make sure your description is precise and highlights the relationship between columns.
"""),

    ("human", '''
- Generate a high-level description for the entire table.
- Generate detailed descriptions for each column, including the inferred datatype and 1-2 sample values.
- Look at the provided Table Description for context and include relevant nuances.

Context: 
This database tracks personal financial health. 
Users want to know if they are spending too much on coffee/food vs their budget, 
or if their subscriptions are getting expensive.

Output Format (Strict List):
["<table description>", [["<column 1>: description, type, <samples>"], ["<column 2>: description, type, <samples>"]]]
     
SQL Table Metadata:
{description}

Sample Rows:
{data_sample}     
     ''')
])

chain = (
    RunnableMap({
        "description": lambda x: x["description"],
        "data_sample": lambda x: x["data_sample"]
    })
    | template
    | model
    | StrOutputParser()
)

kb_final = {}
print("🚀 Building Financial Knowledge Base...")

for table_name, desc in tqdm.tqdm(table_description.items()):
    try:
        sample_df = read_sql(table_name)
        sample_dict = str(sample_df.to_dict())

        response = chain.invoke({"description": desc, "data_sample": sample_dict}).replace('```', '')
        print(f"\n✅ Annotated {table_name}")
        cleaned_response = response.replace('```json', '').replace('```', '').strip()
        import ast
        try:
            kb_final[table_name] = ast.literal_eval(cleaned_response)
        except Exception as e:
            print(f"❌ Error parsing response for {table_name}: {e}")
            kb_final[table_name] = []
        time.sleep(1) # Rate limiting respect
    except Exception as e:
        print(f"❌ Error on table {table_name}: {e}")

# Save to kb.pkl
kb_output_path = os.path.join(os.getcwd(), 'LangGRAPH_SQL', 'kb.pkl')
with open(kb_output_path, 'wb') as f:
    pickle.dump(kb_final, f)

print(f"\n✨ SUCCESS: Knowledge Base saved to {kb_output_path}")
