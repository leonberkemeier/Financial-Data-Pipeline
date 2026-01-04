"""Migration script to add exchange_id column to dim_company table."""
import sqlite3
from pathlib import Path

# Path to database
DB_PATH = Path(__file__).parent / "financial_data.db"

def migrate():
    """Add exchange_id column to dim_company if it doesn't exist."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        print("=" * 80)
        print("MIGRATING: Adding exchange_id column to dim_company")
        print("=" * 80)
        
        # Check if exchange_id column already exists
        cursor.execute("PRAGMA table_info(dim_company)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if "exchange_id" in columns:
            print("✓ exchange_id column already exists")
            return
        
        # Add the column
        print("Adding exchange_id column...")
        cursor.execute("""
            ALTER TABLE dim_company 
            ADD COLUMN exchange_id INTEGER
        """)
        
        # Create foreign key relationship (SQLite doesn't enforce it, but for documentation)
        print("✓ Added exchange_id column to dim_company")
        
        conn.commit()
        print("\n" + "=" * 80)
        print("MIGRATION COMPLETE")
        print("=" * 80)
        
    except sqlite3.OperationalError as e:
        print(f"✗ Error: {str(e)}")
        conn.rollback()
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
