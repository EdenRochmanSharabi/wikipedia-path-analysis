#!/usr/bin/env python3
import oracledb
import argparse
from tabulate import tabulate
import matplotlib.pyplot as plt
import networkx as nx
from collections import Counter
import os
import json

def connect_to_database(args):
    """Connect to the Oracle database"""
    try:
        connection_string = f"{args.user}/{args.password}@{args.host}:{args.port}/{args.service}"
        conn = oracledb.connect(connection_string)
        print(f"Connected to {args.user}@{args.host}:{args.port}/{args.service}")
        return conn
    except oracledb.Error as e:
        print(f"Error connecting to database: {e}")
        return None

def get_path_stats(conn):
    """Get basic statistics about the paths"""
    cursor = conn.cursor()
    
    # Get counts of paths and nodes
    cursor.execute("SELECT COUNT(*) FROM WIKI_PATHS")
    path_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM WIKI_PATH_NODES")
    node_count = cursor.fetchone()[0]
    
    # Get average path length
    cursor.execute("SELECT AVG(steps) FROM WIKI_PATHS")
    avg_length = cursor.fetchone()[0]
    
    # Get success rate
    cursor.execute("SELECT COUNT(*) FROM WIKI_PATHS WHERE succeeded = 1")
    success_count = cursor.fetchone()[0]
    success_rate = (success_count / path_count) * 100 if path_count > 0 else 0
    
    print("\n=== WIKI PATH STATISTICS ===")
    print(f"Total paths: {path_count}")
    print(f"Total nodes: {node_count}")
    print(f"Average path length: {avg_length:.2f} steps")
    print(f"Success rate: {success_rate:.2f}%")
    
    cursor.close()
    return path_count

def get_most_common_articles(conn, limit=10):
    """Get the most common articles in the paths"""
    cursor = conn.cursor()
    
    cursor.execute(f"""
        SELECT article_title, COUNT(*) as frequency
        FROM WIKI_PATH_NODES
        GROUP BY article_title
        ORDER BY frequency DESC
        FETCH FIRST {limit} ROWS ONLY
    """)
    
    results = cursor.fetchall()
    
    if results:
        print(f"\n=== TOP {limit} MOST COMMON ARTICLES ===")
        headers = ["Article", "Frequency"]
        print(tabulate(results, headers=headers, tablefmt="grid"))
    
    cursor.close()
    return results

def get_latest_paths(conn, limit=5):
    """Get the latest paths added to the database"""
    cursor = conn.cursor()
    
    cursor.execute(f"""
        SELECT path_id, start_article, end_article, steps, 
               CASE WHEN succeeded = 1 THEN 'Yes' ELSE 'No' END as succeeded
        FROM WIKI_PATHS
        ORDER BY path_id DESC
        FETCH FIRST {limit} ROWS ONLY
    """)
    
    results = cursor.fetchall()
    
    if results:
        print(f"\n=== LATEST {limit} PATHS ===")
        headers = ["Path ID", "Start Article", "End Article", "Steps", "Target Reached"]
        print(tabulate(results, headers=headers, tablefmt="grid"))
    
    cursor.close()
    return results

def get_path_details(conn, path_id):
    """Get details for a specific path"""
    cursor = conn.cursor()
    
    # Get path metadata
    cursor.execute("""
        SELECT path_id, start_article, end_article, steps, 
               CASE WHEN succeeded = 1 THEN 'Yes' ELSE 'No' END as succeeded,
               creation_date
        FROM WIKI_PATHS
        WHERE path_id = :path_id
    """, {'path_id': path_id})
    
    path_info = cursor.fetchone()
    
    if not path_info:
        print(f"Path with ID {path_id} not found")
        cursor.close()
        return None
    
    # Get path nodes
    cursor.execute("""
        SELECT step_number, article_title, article_url
        FROM WIKI_PATH_NODES
        WHERE path_id = :path_id
        ORDER BY step_number
    """, {'path_id': path_id})
    
    nodes = cursor.fetchall()
    
    print(f"\n=== PATH {path_id} DETAILS ===")
    print(f"Start: {path_info[1]}")
    print(f"End: {path_info[2]}")
    print(f"Steps: {path_info[3]}")
    print(f"Target Reached: {path_info[4]}")
    print(f"Created: {path_info[5]}")
    
    if nodes:
        print("\nPath sequence:")
        headers = ["Step", "Article", "URL"]
        print(tabulate(nodes, headers=headers, tablefmt="grid"))
    
    cursor.close()
    return path_info, nodes

def export_to_json(conn, output_file='wiki_data.json'):
    """Export all paths to a JSON file"""
    cursor = conn.cursor()
    
    # Get all paths
    cursor.execute("""
        SELECT path_id, start_article, end_article, steps, 
               succeeded, creation_date
        FROM WIKI_PATHS
        ORDER BY path_id
    """)
    
    paths = []
    for row in cursor.fetchall():
        path_id, start, end, steps, succeeded, created = row
        
        # Get nodes for this path
        cursor.execute("""
            SELECT step_number, article_title, article_url
            FROM WIKI_PATH_NODES
            WHERE path_id = :path_id
            ORDER BY step_number
        """, {'path_id': path_id})
        
        nodes = []
        for node_row in cursor.fetchall():
            step, title, url = node_row
            nodes.append({
                'step': step,
                'title': title,
                'url': url
            })
        
        paths.append({
            'path_id': path_id,
            'start_article': start,
            'end_article': end,
            'steps': steps,
            'succeeded': bool(succeeded),
            'created': str(created),
            'nodes': nodes
        })
    
    # Write to JSON file
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({'paths': paths}, f, indent=2, ensure_ascii=False)
    
    print(f"\nExported {len(paths)} paths to {output_file}")
    
    cursor.close()
    return len(paths)

def main():
    parser = argparse.ArgumentParser(description="Analyze Wikipedia Paths")
    parser.add_argument("--host", type=str, default="localhost", help="Database host")
    parser.add_argument("--port", type=int, default=1521, help="Database port")
    parser.add_argument("--service", type=str, default="XEPDB1", help="Database service name")
    parser.add_argument("--user", type=str, default="system", help="Database username")
    parser.add_argument("--password", type=str, default="Oracle21c", help="Database password")
    parser.add_argument("--path-id", type=int, help="Show details for a specific path ID")
    parser.add_argument("--export", action="store_true", help="Export all paths to JSON")
    parser.add_argument("--output", type=str, default="wiki_data.json", help="Output file for JSON export")
    
    args = parser.parse_args()
    
    # Connect to the database
    conn = connect_to_database(args)
    if not conn:
        return
    
    try:
        if args.path_id:
            # Get details for a specific path
            get_path_details(conn, args.path_id)
        elif args.export:
            # Export all paths to JSON
            export_to_json(conn, args.output)
        else:
            # General statistics
            path_count = get_path_stats(conn)
            
            if path_count > 0:
                get_most_common_articles(conn)
                get_latest_paths(conn)
                
    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    main() 