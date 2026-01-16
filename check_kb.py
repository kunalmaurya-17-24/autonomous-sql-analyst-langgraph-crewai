import pickle

with open('LangGRAPH_SQL/kb.pkl', 'rb') as f:
    kb = pickle.load(f)

print("=" * 50)
print("KB.PKL CONTENTS")
print("=" * 50)
print(f"Total tables: {len(kb)}")
print(f"Table names: {list(kb.keys())}")
print("\n'transactions' exists:", 'transactions' in kb)
print("'budgets' exists:", 'budgets' in kb)
print("'recurring_subscriptions' exists:", 'recurring_subscriptions' in kb)

if len(kb) == 0:
    print("\n⚠️  KB IS EMPTY!")
else:
    print("\n✅ KB is populated with", len(kb), "tables")
