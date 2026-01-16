
import ast
import logging

# Setup basic logging
logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)

def parse_llm_output(output_str):
    print(f"Testing input: {repr(output_str)}")
    cleaned = output_str.replace('```json', '').replace('```', '').strip()
    try:
        parsed = ast.literal_eval(cleaned)
        print(f"✅ Success: {parsed}")
        return parsed
    except Exception as e:
        print(f"❌ Error caught: {e}")
        return []

# Test cases
test_cases = [
    '["table_name"]', 
    '```json\n["table_name"]\n```',
    '["table", "name"]', 
    '[',  # Malformed
    'some random text' # Invalid
]

print("--- STARTING VERIFICATION ---")
for case in test_cases:
    parse_llm_output(case)
print("--- END VERIFICATION ---")
