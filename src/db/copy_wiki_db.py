#!/usr/bin/env python3
import oracledb
import sys
import os

# Configuration
SOURCE_USER = "sys"
SOURCE_PASSWORD = "cyvsi5-vapzUk-qizveb"
SOURCE_DSN = "localhost:1521/XE"
SOURCE_MODE = oracledb.AUTH_MODE_SYSDBA

TARGET_USER = "WIKI_COPY"
TARGET_PASSWORD = "wiki_copy_pwd123"

def connect_to_source():
    """Connect to the source database"""
    try:
        connection = oracledb.connect(
            user=SOURCE_USER,
            password=SOURCE_PASSWORD,
            dsn=SOURCE_DSN,
            mode=SOURCE_MODE
        )
        print(f"Connected to source database as {SOURCE_USER}")
        return connection
    except oracledb.Error as e:
        print(f"Error connecting to source database: {e}")
        return None

def create_target_user(source_conn):
    """Create the target user if it doesn't exist"""
    cursor = source_conn.cursor()
    
    try:
        # Check if user already exists
        cursor.execute("""
            SELECT COUNT(*) FROM DBA_USERS WHERE USERNAME = :username
        """, username=TARGET_USER.upper())
        
        count = cursor.fetchone()[0]
        
        if count > 0:
            print(f"User {TARGET_USER} already exists")
            
            # Drop existing tables if they exist
            try:
                cursor.execute(f"DROP TABLE {TARGET_USER}.WIKI_PATH_NODES")
                print(f"Dropped existing {TARGET_USER}.WIKI_PATH_NODES table")
            except oracledb.Error:
                pass  # Table doesn't exist
                
            try:
                cursor.execute(f"DROP TABLE {TARGET_USER}.WIKI_PATHS")
                print(f"Dropped existing {TARGET_USER}.WIKI_PATHS table")
            except oracledb.Error:
                pass  # Table doesn't exist
        else:
            # Create new user
            print(f"Creating user {TARGET_USER}...")
            cursor.execute(f"CREATE USER {TARGET_USER} IDENTIFIED BY {TARGET_PASSWORD}")
            cursor.execute(f"GRANT CONNECT, RESOURCE, DBA TO {TARGET_USER}")
            cursor.execute(f"ALTER USER {TARGET_USER} QUOTA UNLIMITED ON USERS")
            source_conn.commit()
            print(f"User {TARGET_USER} created successfully")
            
        return True
    except oracledb.Error as e:
        print(f"Error creating target user: {e}")
        return False
    finally:
        cursor.close()

def check_tables(source_conn):
    """Check what tables exist and their structure"""
    cursor = source_conn.cursor()
    try:
        cursor.execute("""
            SELECT OWNER, TABLE_NAME 
            FROM ALL_TABLES 
            WHERE TABLE_NAME IN ('WIKI_PATHS', 'WIKI_PATH_NODES')
            ORDER BY OWNER, TABLE_NAME
        """)
        
        tables = cursor.fetchall()
        print(f"Found tables: {tables}")
        
        # Check first 5 rows of WIKI_PATHS
        try:
            cursor.execute("SELECT * FROM WIKI_COPY.WIKI_PATHS WHERE ROWNUM <= 5")
            rows = cursor.fetchall()
            print(f"Sample WIKI_PATHS data: {rows}")
            
            # Get column info
            cursor.execute("""
                SELECT COLUMN_NAME, DATA_TYPE
                FROM ALL_TAB_COLUMNS
                WHERE TABLE_NAME = 'WIKI_PATHS'
                AND OWNER = 'SYS'
                ORDER BY COLUMN_ID
            """)
            
            columns = cursor.fetchall()
            print(f"WIKI_PATHS columns: {columns}")
            
        except oracledb.Error as e:
            print(f"Error checking WIKI_PATHS: {e}")
        
        # Check first 5 rows of WIKI_PATH_NODES
        try:
            cursor.execute("SELECT * FROM WIKI_COPY.WIKI_PATH_NODES WHERE ROWNUM <= 5")
            rows = cursor.fetchall()
            print(f"Sample WIKI_PATH_NODES data: {rows}")
            
            # Get column info
            cursor.execute("""
                SELECT COLUMN_NAME, DATA_TYPE
                FROM ALL_TAB_COLUMNS
                WHERE TABLE_NAME = 'WIKI_PATH_NODES'
                AND OWNER = 'SYS'
                ORDER BY COLUMN_ID
            """)
            
            columns = cursor.fetchall()
            print(f"WIKI_PATH_NODES columns: {columns}")
            
        except oracledb.Error as e:
            print(f"Error checking WIKI_PATH_NODES: {e}")
            
        return True
    except oracledb.Error as e:
        print(f"Error checking tables: {e}")
        return False
    finally:
        cursor.close()

def create_tables_and_copy_data(source_conn):
    """Create tables and copy data in one go using CREATE TABLE AS SELECT"""
    cursor = source_conn.cursor()
    
    try:
        # Step 1: Create WIKI_PATHS table with data
        print(f"Creating {TARGET_USER}.WIKI_PATHS and copying data...")
        cursor.execute(f"""
            CREATE TABLE {TARGET_USER}.WIKI_PATHS AS
            SELECT * FROM WIKI_COPY.WIKI_PATHS
        """)
        source_conn.commit()
        
        # Step 2: Create WIKI_PATH_NODES table with data
        print(f"Creating {TARGET_USER}.WIKI_PATH_NODES and copying data...")
        cursor.execute(f"""
            CREATE TABLE {TARGET_USER}.WIKI_PATH_NODES AS
            SELECT * FROM WIKI_COPY.WIKI_PATH_NODES
        """)
        source_conn.commit()
        
        # Step 3: Add primary key to WIKI_PATHS
        print("Adding primary key to WIKI_PATHS...")
        cursor.execute(f"""
            ALTER TABLE {TARGET_USER}.WIKI_PATHS
            ADD CONSTRAINT WIKI_PATHS_PK PRIMARY KEY (PATH_ID)
        """)
        source_conn.commit()
        
        # Step 4: Add primary key to WIKI_PATH_NODES
        print("Adding primary key to WIKI_PATH_NODES...")
        cursor.execute(f"""
            ALTER TABLE {TARGET_USER}.WIKI_PATH_NODES
            ADD CONSTRAINT WIKI_PATH_NODES_PK PRIMARY KEY (NODE_ID)
        """)
        source_conn.commit()
        
        # Step 5: Add foreign key constraint
        print("Adding foreign key constraint...")
        try:
            cursor.execute(f"""
                ALTER TABLE {TARGET_USER}.WIKI_PATH_NODES
                ADD CONSTRAINT FK_WIKI_PATH_ID
                FOREIGN KEY (PATH_ID) REFERENCES {TARGET_USER}.WIKI_PATHS(PATH_ID)
            """)
            source_conn.commit()
        except oracledb.Error as e:
            print(f"Warning: Could not add foreign key constraint: {e}")
            print("This might be due to data inconsistency. Continuing without the constraint.")
            source_conn.rollback()
        
        print("Tables created and data copied successfully")
        return True
    except oracledb.Error as e:
        print(f"Error creating tables and copying data: {e}")
        source_conn.rollback()
        return False
    finally:
        cursor.close()

def main():
    """Main function to copy database tables"""
    print("=== Oracle Database Tables Copy Script ===")
    print("This script will copy the wiki tables to a new schema in the same database.")
    
    # Connect to source database
    source_conn = connect_to_source()
    if not source_conn:
        print("Failed to connect to source database. Exiting.")
        return 1
    
    try:
        # Create target user
        if not create_target_user(source_conn):
            print("Failed to create target user. Exiting.")
            return 1
        
        # Check tables
        if not check_tables(source_conn):
            print("Failed to check tables. Exiting.")
            return 1
        
        # Create tables and copy data
        if not create_tables_and_copy_data(source_conn):
            print("Failed to create tables and copy data. Exiting.")
            return 1
        
        # Get row counts for verification
        cursor = source_conn.cursor()
        
        cursor.execute(f"SELECT COUNT(*) FROM {TARGET_USER}.WIKI_PATHS")
        paths_count = cursor.fetchone()[0]
        
        cursor.execute(f"SELECT COUNT(*) FROM {TARGET_USER}.WIKI_PATH_NODES")
        nodes_count = cursor.fetchone()[0]
        
        cursor.execute(f"SELECT COUNT(*) FROM {SOURCE_USER}.WIKI_PATHS")
        source_paths_count = cursor.fetchone()[0]
        
        cursor.execute(f"SELECT COUNT(*) FROM {SOURCE_USER}.WIKI_PATH_NODES")
        source_nodes_count = cursor.fetchone()[0]
        
        print("\nVerification:")
        print(f"{TARGET_USER}.WIKI_PATHS: {paths_count} records")
        print(f"{TARGET_USER}.WIKI_PATH_NODES: {nodes_count} records")
        print(f"{SOURCE_USER}.WIKI_PATHS: {source_paths_count} records")
        print(f"{SOURCE_USER}.WIKI_PATH_NODES: {source_nodes_count} records")
        
        paths_match = paths_count == source_paths_count
        nodes_match = nodes_count == source_nodes_count
        
        print(f"WIKI_PATHS counts match: {'✓' if paths_match else '✗'}")
        print(f"WIKI_PATH_NODES counts match: {'✓' if nodes_match else '✗'}")
        
        print("\nDatabase tables copy completed successfully.")
        print(f"You can now connect to the {TARGET_USER} schema and modify the data while the original continues growing.")
        print(f"Connection details: user: {TARGET_USER}, password: {TARGET_PASSWORD}")
        
        print("\nUpdate your Python code with this connection string:")
        print("------------------------------------------------------------")
        print("connection = oracledb.connect(")
        print(f'    user="{TARGET_USER}",')
        print(f'    password="{TARGET_PASSWORD}",')
        print(f'    dsn="{SOURCE_DSN}"')
        print(")")
        print("------------------------------------------------------------")
        
        return 0
    except Exception as e:
        print(f"Unexpected error: {e}")
        return 1
    finally:
        if source_conn:
            source_conn.close()

if __name__ == "__main__":
    sys.exit(main()) 