import sqlite3

def migrate():
    conn = sqlite3.connect('sales_bot.db')
    cursor = conn.cursor()
    
    # 1. Add commission_rate to users table if not exists
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN commission_rate FLOAT;")
        print("Added commission_rate column to users table.")
    except sqlite3.OperationalError:
        print("Column commission_rate already exists or users table does not exist.")
    
    # 2. Create settings table if not exists
    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                id INTEGER PRIMARY KEY,
                key TEXT UNIQUE,
                value TEXT
            );
        """)
        print("Settings table created or already exists.")
    except Exception as e:
        print(f"Error creating settings table: {e}")
        
    conn.commit()
    conn.close()

if __name__ == "__main__":
    migrate()
