# db_setup.py
import database

if __name__ == "__main__":
    print("This script will set up your database tables.")
    database.init_db()
    print("Setup complete.")