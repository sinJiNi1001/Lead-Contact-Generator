import os
import sys
from sqlalchemy import text

# Ensure the script can find your database file
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import Base, engine
from database import Company, Contact, SearchHistory

def reset_database():
    print("=========================================")
    print("⚠️ WARNING: FORCED DATABASE RESET ⚠️")
    print("=========================================")
    print("This will forcefully drop all tables (including ghost tables) and completely wipe your current leads.")
    print("It will then recreate the tables with the new CRM schema.\n")
    
    confirm = input("Type 'YES' to permanently wipe and update the database: ")
    
    if confirm == 'YES':
        try:
            print("\n🗑️ Forcing CASCADE drop on all tables...")
            
            # Use raw SQL to force PostgreSQL to drop the tables and anything depending on them
            with engine.begin() as conn:
                conn.execute(text("DROP TABLE IF EXISTS activities CASCADE;"))
                conn.execute(text("DROP TABLE IF EXISTS contacts CASCADE;"))
                conn.execute(text("DROP TABLE IF EXISTS companies CASCADE;"))
                conn.execute(text("DROP TABLE IF EXISTS search_history CASCADE;"))
            
            print("✨ Recreating tables with the new CRM schema...")
            Base.metadata.create_all(bind=engine)
            
            print("✅ Database updated successfully! You are ready to launch.")
        except Exception as e:
            print(f"❌ Error updating database: {e}")
    else:
        print("\n🚫 Operation cancelled. Your database was not touched.")

if __name__ == "__main__":
    reset_database()