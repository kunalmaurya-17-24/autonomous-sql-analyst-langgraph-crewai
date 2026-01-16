import sqlite3
import pandas as pd
import random
from datetime import datetime, timedelta

def create_complete_database():
    print("🚀 Initializing Finance Database Build...")
    conn = sqlite3.connect('finance.db')
    c = conn.cursor()
    
    # --- STEP 1: DROP OLD TABLES ---
    c.execute('DROP TABLE IF EXISTS transactions')
    c.execute('DROP TABLE IF EXISTS budgets')
    c.execute('DROP TABLE IF EXISTS recurring_subscriptions')

    # --- STEP 2: CREATE TABLES ---
    # Table 1: The Raw Logs
    c.execute('''
    CREATE TABLE transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date DATE NOT NULL,
        merchant TEXT NOT NULL,
        amount DECIMAL(10, 2) NOT NULL,
        category TEXT NOT NULL
    )
    ''')

    # Table 2: The Rules (Budgets)
    c.execute('''
    CREATE TABLE budgets (
        category TEXT PRIMARY KEY,
        monthly_limit DECIMAL(10, 2) NOT NULL
    )
    ''')

    # Table 3: The Expectations (Subscriptions)
    c.execute('''
    CREATE TABLE recurring_subscriptions (
        service_name TEXT PRIMARY KEY,
        expected_amount DECIMAL(10, 2)
    )
    ''')

    # --- STEP 3: INJECT DATA ---
    
    # A. Insert Budgets
    budgets = [
        ('Food', 10000.00),
        ('Transport', 5000.00),
        ('Shopping', 8000.00),
        ('Utilities', 5000.00)
    ]
    c.executemany('INSERT INTO budgets VALUES (?, ?)', budgets)
    print("✅ Budgets set.")

    # B. Insert Expected Subscriptions
    subs = [
        ('Netflix', 649.00),
        ('Spotify', 119.00),
        ('Amazon Prime', 299.00)
    ]
    c.executemany('INSERT INTO recurring_subscriptions VALUES (?, ?)', subs)
    print("✅ Subscription baselines set.")

    # C. Inject Synthetic Transactions
    print("... Injecting Transaction History...")
    merchants = {
        'Food': ['Starbucks', 'Tim Hortons', 'Zomato', 'Swiggy', 'Burger King'],
        'Transport': ['Uber', 'Ola', 'Rapido'],
        'Utilities': ['Netflix', 'Spotify', 'Electricity Bill'],
        'Shopping': ['Amazon', 'Myntra', 'Zara']
    }
    
    start_date = datetime.now() - timedelta(days=90)
    
    for i in range(150):
        random_date = start_date + timedelta(days=random.randint(0, 90))
        category = random.choice(list(merchants.keys()))
        merchant = random.choice(merchants[category])
        
        # Trigger: Make Coffee & Uber expensive
        if category == 'Food': amount = round(random.uniform(200.00, 1500.00), 2)
        elif category == 'Transport': amount = round(random.uniform(150.00, 800.00), 2)
        else: amount = round(random.uniform(100.00, 3000.00), 2)

        c.execute('INSERT INTO transactions (date, merchant, amount, category) VALUES (?, ?, ?, ?)',
                  (random_date.strftime('%Y-%m-%d'), merchant, amount, category))

    # D. Inject Salary (Income)
    salary_dates = [
        start_date.replace(day=1), 
        (start_date + timedelta(days=32)).replace(day=1), 
        (start_date + timedelta(days=64)).replace(day=1)
    ]
    for pay_day in salary_dates:
        c.execute('INSERT INTO transactions (date, merchant, amount, category) VALUES (?, ?, ?, ?)', 
                  (pay_day.strftime('%Y-%m-%d'), 'Tech Corp Inc.', 150000.00, 'Income'))

    # E. Import Real CSV
    try:
        df = pd.read_csv('bank_statements.csv')
        count = 0
        for index, row in df.iterrows():
            if pd.isna(row['amount']): continue
            
            # Simple keyword mapper
            n = str(row['narration']).upper() if pd.notna(row['narration']) else "Unknown"
            cat = 'Transport' if ('GAS' in n or 'FUEL' in n) else \
                  'Food' if ('FOOD' in n or 'ZOMATO' in n) else \
                  'Uncategorized'
            
            # Date handling
            try: d = row['transactionTimestamp'].split('T')[0]
            except: d = datetime.now().strftime('%Y-%m-%d')
            
            if row['type'] == 'DEBIT':
                c.execute('INSERT INTO transactions (date, merchant, amount, category) VALUES (?, ?, ?, ?)',
                          (d, n, float(row['amount']), cat))
                count += 1
        print(f"✅ Merged {count} real transactions from CSV.")
    except Exception as e:
        print(f"⚠️ CSV Warning: {e} (Continuing with synthetic data only)")

    # --- VERIFICATION STEP ---
    c.execute("SELECT COUNT(*) FROM transactions")
    total_rows = c.fetchone()[0]
    c.execute("SELECT SUM(amount) FROM transactions WHERE category='Income'")
    total_income = c.fetchone()[0]
    
    conn.commit()
    conn.close()
    
    print(f"\n🎉 DATABASE COMPLETE.")
    print(f"   -> Total Transactions: {total_rows}")
    print(f"   -> Total Income Logged: ₹{total_income:,.2f}")

if __name__ == "__main__":
    create_complete_database()