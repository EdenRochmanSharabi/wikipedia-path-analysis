#!/usr/bin/env python3
import oracledb
import argparse
from tabulate import tabulate

def main():
    parser = argparse.ArgumentParser(description="Check Wikipedia Data in Oracle")
    parser.add_argument("--host", type=str, default="localhost", help="Database host")
    parser.add_argument("--port", type=int, default=1521, help="Database port")
    parser.add_argument("--service", type=str, default="XEPDB1", help="Database service name")
    parser.add_argument("--user", type=str, default="system", help="Database username")
    parser.add_argument("--password", type=str, default="Oracle21c", help="Database password")
    
    args = parser.parse_args()
    
    print(f"Connecting to {args.user}@{args.host}:{args.port}/{args.service}")
    
    try:
        # Connect to the database
        connection_string = f"{args.user}/{args.password}@{args.host}:{args.port}/{args.service}"
        conn = oracledb.connect(connection_string)
        cursor = conn.cursor()
        
        # Get count of paths
        cursor.execute("SELECT COUNT(*) FROM WIKI_PATHS")
        path_count = cursor.fetchone()[0]
        print(f"Total wiki paths: {path_count}")
        
        # Get count of nodes
        cursor.execute("SELECT COUNT(*) FROM WIKI_PATH_NODES")
        node_count = cursor.fetchone()[0]
        print(f"Total wiki path nodes: {node_count}")
        
        # Get latest paths
        cursor.execute("""
            SELECT path_id, start_article, end_article, steps 
            FROM WIKI_PATHS 
            ORDER BY path_id DESC 
            FETCH FIRST 5 ROWS ONLY
        """)
        
        paths = cursor.fetchall()
        if paths:
            print("\nLatest paths:")
            headers = ["Path ID", "Start Article", "End Article", "Steps"]
            print(tabulate(paths, headers=headers, tablefmt="grid"))
        
        # Get sample path nodes for the first path
        cursor.execute("""
            SELECT path_id, step_number, article_title 
            FROM WIKI_PATH_NODES 
            WHERE path_id = 1
            ORDER BY step_number
        """)
        
        nodes = cursor.fetchall()
        if nodes:
            print("\nNodes for path 1:")
            headers = ["Path ID", "Step Number", "Article"]
            print(tabulate(nodes, headers=headers, tablefmt="grid"))
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    main() 