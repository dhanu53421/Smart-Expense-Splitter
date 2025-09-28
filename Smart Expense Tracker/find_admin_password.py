import sqlite3
import os

def find_admin_password():
    # Look for the database file
    possible_db_files = ['app.db', 'smart_expense.db', 'instance/app.db', 'instance/smart_expense.db']
    
    db_path = None
    for file in possible_db_files:
        if os.path.exists(file):
            db_path = file
            break
    
    if not db_path:
        print("Could not find database file")
        return
    
    print(f"Found database: {db_path}")
    
    # Connect to the database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Query for the admin user
        cursor.execute("SELECT id, username, email, password_hash FROM user WHERE username = 'admin'")
        admin_user = cursor.fetchone()
        
        if admin_user:
            print(f"Admin user found:")
            print(f"  ID: {admin_user[0]}")
            print(f"  Username: {admin_user[1]}")
            print(f"  Email: {admin_user[2]}")
            print(f"  Password Hash: {admin_user[3]}")
            
            # Try to find other users
            cursor.execute("SELECT id, username, email FROM user")
            all_users = cursor.fetchall()
            print(f"\nAll users in database:")
            for user in all_users:
                print(f"  ID: {user[0]}, Username: {user[1]}, Email: {user[2]}")
        else:
            print("No admin user found")
            
            # Check what's in the user table
            cursor.execute("SELECT id, username, email FROM user")
            all_users = cursor.fetchall()
            if all_users:
                print(f"Users found:")
                for user in all_users:
                    print(f"  ID: {user[0]}, Username: {user[1]}, Email: {user[2]}")
            else:
                print("No users found in database")
    
    except sqlite3.OperationalError as e:
        print(f"Database error: {e}")
        
        # Try to see what tables exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        print(f"Tables in database: {[table[0] for table in tables]}")
    
    finally:
        conn.close()

if __name__ == "__main__":
    find_admin_password()