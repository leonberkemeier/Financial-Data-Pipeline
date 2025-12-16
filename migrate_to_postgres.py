#!/usr/bin/env python3
"""
Migrate SQLite database to remote PostgreSQL server
"""
import sys
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker
import pandas as pd

# Configuration
SQLITE_DB = 'sqlite:///./financial_data.db'
POSTGRES_DB = 'postgresql://financial_user:secure_password@100.102.213.61:5432/financial_data'

print("="*70)
print("SQLite → PostgreSQL Migration")
print("="*70)
print(f"Source: {SQLITE_DB}")
print(f"Target: {POSTGRES_DB}\n")

try:
    # Connect to both databases
    print("1. Connecting to databases...")
    sqlite_engine = create_engine(SQLITE_DB)
    postgres_engine = create_engine(POSTGRES_DB)
    
    # Verify connections
    with sqlite_engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    print("   ✓ SQLite connected")
    
    with postgres_engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    print("   ✓ PostgreSQL connected")
    
    # Get list of tables
    print("\n2. Inspecting SQLite schema...")
    inspector = inspect(sqlite_engine)
    tables = inspector.get_table_names()
    print(f"   Found {len(tables)} tables: {', '.join(tables)}\n")
    
    # Migrate each table
    print("3. Migrating tables...")
    for i, table in enumerate(tables, 1):
        try:
            print(f"   ({i}/{len(tables)}) Migrating {table}...", end=" ", flush=True)
            
            # Read from SQLite
            df = pd.read_sql_table(table, sqlite_engine)
            
            # Write to PostgreSQL (replace if exists)
            df.to_sql(table, postgres_engine, if_exists='replace', index=False)
            
            print(f"✓ ({len(df)} rows)")
        except Exception as e:
            print(f"✗ Error: {str(e)}")
    
    # Verify migration
    print("\n4. Verifying migration...")
    sqlite_inspector = inspect(sqlite_engine)
    postgres_inspector = inspect(postgres_engine)
    
    for table in tables:
        sqlite_count = pd.read_sql_query(f"SELECT COUNT(*) FROM {table}", sqlite_engine).iloc[0, 0]
        postgres_count = pd.read_sql_query(f"SELECT COUNT(*) FROM {table}", postgres_engine).iloc[0, 0]
        
        status = "✓" if sqlite_count == postgres_count else "✗"
        print(f"   {status} {table}: SQLite={sqlite_count}, PostgreSQL={postgres_count}")
    
    print("\n" + "="*70)
    print("✅ Migration complete!")
    print("="*70)
    print("\nNext steps:")
    print("1. Update .env with new DATABASE_URL:")
    print(f"   DATABASE_URL=postgresql://financial_user:secure_password@100.102.213.61:5432/financial_data")
    print("\n2. Test connection:")
    print("   python rag_demo.py --query 'What is Apple?'")
    
except Exception as e:
    print(f"\n❌ Migration failed: {str(e)}")
    sys.exit(1)
