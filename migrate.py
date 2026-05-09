import sqlite3
import os

db_path = "sales_bot.db"

if os.path.exists(db_path):
    print(f"Connecting to {db_path}...")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # 1. Add voucher_id to orders
        print("Adding voucher_id to orders table...")
        try:
            cursor.execute("ALTER TABLE orders ADD COLUMN voucher_id INTEGER REFERENCES vouchers(id)")
            print("Successfully added voucher_id column.")
        except: print("Column voucher_id exists.")
        
        # 2. Add qr_message_id to transactions
        print("Adding qr_message_id to transactions table...")
        try:
            cursor.execute("ALTER TABLE transactions ADD COLUMN qr_message_id INTEGER")
            print("Successfully added qr_message_id column.")
        except: print("Column qr_message_id exists.")

        # 3. Add referral fields to users
        print("Adding referral fields to users table...")
        try:
            cursor.execute("ALTER TABLE users ADD COLUMN referral_code TEXT")
            print("Successfully added referral_code column.")
        except: print("Column referral_code may already exist.")
        
        try:
            cursor.execute("ALTER TABLE users ADD COLUMN referred_by_id INTEGER")
            print("Successfully added referred_by_id column.")
        except: print("Column referred_by_id may already exist.")
        
        try:
            cursor.execute("ALTER TABLE users ADD COLUMN api_key TEXT")
            print("Successfully added api_key column.")
        except: print("Column api_key may already exist.")
        # 4. Add reseller fields to products
        print("Adding reseller fields to products table...")
        columns_to_add = [
            ("is_partner", "BOOLEAN DEFAULT 0"),
            ("partner_id", "TEXT"),
            ("price_mode", "TEXT DEFAULT 'auto'"),
            ("markup_percent", "FLOAT DEFAULT 10.0"),
            ("manual_price", "FLOAT")
        ]
        for col_name, col_type in columns_to_add:
            try:
                cursor.execute(f"ALTER TABLE products ADD COLUMN {col_name} {col_type}")
                print(f"Successfully added {col_name} column to products.")
            except: print(f"Column {col_name} exists.")
            
        # 5. Add reseller fields to orders
        print("Adding reseller fields to orders table...")
        try:
            cursor.execute("ALTER TABLE orders ADD COLUMN partner_order_code TEXT")
            print("Successfully added partner_order_code column to orders.")
        except: print("Column partner_order_code exists.")
        
        # 6. Add is_hidden to categories and products
        print("Adding is_hidden fields...")
        try:
            cursor.execute("ALTER TABLE categories ADD COLUMN is_hidden BOOLEAN DEFAULT 0")
            print("Successfully added is_hidden to categories.")
        except: print("Column is_hidden exists in categories.")
        
        try:
            cursor.execute("ALTER TABLE products ADD COLUMN is_hidden BOOLEAN DEFAULT 0")
            print("Successfully added is_hidden to products.")
        except: print("Column is_hidden exists in products.")
        
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e).lower():
            print("Column already exists.")
        else:
            print(f"Error adding column: {e}")
            
    conn.commit()
    conn.close()
    print("Migration finished.")
else:
    print("Database file not found. Nothing to migrate.")
