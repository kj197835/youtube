import os
from database import DB_NAME, init_db

def reset_database():
    if os.path.exists(DB_NAME):
        print(f"Removing existing database: {DB_NAME}")
        os.remove(DB_NAME)
    
    print("Creating new database schema...")
    init_db()
    print("Database reset complete.")

if __name__ == "__main__":
    reset_database()
