from database import engine
from sqlalchemy import text

def test_connection():
    try:
        # We attempt to connect and run a simple "SELECT 1" 
        # This just asks the database to send back the number 1.
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1"))
            print("---------------------------------------")
            print("✅ CONNECTION SUCCESSFUL!")
            print(f"Database responded with: {result.fetchone()}")
            print("---------------------------------------")
    except Exception as e:
        print("---------------------------------------")
        print("❌ CONNECTION FAILED")
        print(f"Error: {e}")
        print("---------------------------------------")

if __name__ == "__main__":
    test_connection()