#!/usr/bin/env python3
import sys
import os
import time
import argparse
import oracledb
from urllib.parse import unquote
from collections import defaultdict

# Add the project root to the Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from src.wiki_core import WikiCrawler

def get_article_url(title):
    """Convert an article title to its URL."""
    encoded_title = title.replace(' ', '_')
    return f"https://en.wikipedia.org/wiki/{encoded_title}"

def process_path(path_id, db_conn, crawler, dry_run=True):
    """Process a single path to identify and correct wrong links."""
    cursor = db_conn.cursor()
    
    # Get all nodes in this path
    cursor.execute("""
        SELECT node_id, step_number, article_title, article_url 
        FROM WIKI_PATH_NODES 
        WHERE path_id = :path_id
        ORDER BY step_number
    """, {'path_id': path_id})
    
    nodes = cursor.fetchall()
    if not nodes:
        print(f"Path {path_id}: No nodes found")
        return 0
    
    changes_needed = 0
    corrections = []
    
    # Process each node except the last one
    for i in range(len(nodes) - 1):
        current_node = nodes[i]
        next_node = nodes[i + 1]
        
        node_id = current_node[0]
        step_number = current_node[1]
        article_title = current_node[2]
        article_url = current_node[3]
        
        next_title = next_node[2]
        
        # Skip if the article title is "Unknown"
        if article_title == "Unknown":
            print(f"Path {path_id}, Step {step_number}: Skipping 'Unknown' article")
            continue
        
        # Use the crawler to find the correct first link
        print(f"Path {path_id}, Step {step_number}: Checking '{article_title}'")
        
        try:
            correct_url, _ = crawler.extract_first_link(article_url)
            
            if not correct_url:
                print(f"  No valid link found, skipping")
                continue
                
            correct_title = crawler.get_title_from_url(correct_url)
            
            # Check if the next article in our path matches what we expect
            if correct_title != next_title:
                changes_needed += 1
                print(f"  INCORRECT: Should link to '{correct_title}', currently links to '{next_title}'")
                
                # Store the correction
                corrections.append({
                    'path_id': path_id,
                    'step': step_number,
                    'current_title': article_title,
                    'incorrect_next': next_title,
                    'correct_next': correct_title,
                    'correct_url': correct_url,
                    'node_to_update': next_node[0]  # The node_id of the next node
                })
            else:
                print(f"  CORRECT: Links to '{next_title}'")
                
            # Add a small delay to be nice to Wikipedia
            time.sleep(0.5)
            
        except Exception as e:
            print(f"  ERROR: {e}")
            continue
    
    # Apply corrections if not in dry run mode
    if not dry_run and corrections:
        for correction in corrections:
            try:
                cursor.execute("""
                    UPDATE WIKI_PATH_NODES
                    SET article_title = :correct_title,
                        article_url = :correct_url
                    WHERE node_id = :node_id
                """, {
                    'correct_title': correction['correct_next'],
                    'correct_url': correction['correct_url'],
                    'node_id': correction['node_to_update']
                })
                
                print(f"Updated node {correction['node_to_update']} in path {path_id} to {correction['correct_next']}")
            except Exception as e:
                print(f"Failed to update node {correction['node_to_update']}: {e}")
        
        # Commit the changes
        db_conn.commit()
    
    return changes_needed

def main():
    parser = argparse.ArgumentParser(description="Correct wrong links in Wikipedia paths")
    parser.add_argument("-l", "--limit", type=int, default=50, help="Number of paths to process")
    parser.add_argument("-s", "--start", type=int, default=1, help="Path ID to start from")
    parser.add_argument("--host", type=str, default="localhost", help="Database host")
    parser.add_argument("--port", type=int, default=1521, help="Database port")
    parser.add_argument("--service", type=str, default="XE", help="Database service name")
    parser.add_argument("--user", type=str, default="system", help="Database username")
    parser.add_argument("--password", type=str, default="oracle", help="Database password")
    parser.add_argument("--dry-run", action="store_true", help="Check paths without making changes")
    
    args = parser.parse_args()
    
    print(f"Starting path correction process")
    print(f"Connecting to database {args.user}@{args.host}:{args.port}/{args.service}")
    
    if args.dry_run:
        print("DRY RUN MODE: No changes will be made to the database")
    
    # Initialize the crawler
    crawler = WikiCrawler()
    
    try:
        # Connect to the database
        connection_string = f"{args.user}/{args.password}@{args.host}:{args.port}/{args.service}"
        conn = oracledb.connect(connection_string)
        cursor = conn.cursor()
        
        # Get the paths to process
        cursor.execute("""
            SELECT path_id FROM WIKI_PATHS
            WHERE path_id >= :start_id
            ORDER BY path_id
            FETCH FIRST :limit ROWS ONLY
        """, {'start_id': args.start, 'limit': args.limit})
        
        path_ids = [row[0] for row in cursor.fetchall()]
        
        if not path_ids:
            print(f"No paths found starting from ID {args.start}")
            return
            
        print(f"Found {len(path_ids)} paths to process")
        
        # Process each path
        total_changes = 0
        for path_id in path_ids:
            changes = process_path(path_id, conn, crawler, args.dry_run)
            total_changes += changes
            print(f"Path {path_id}: {changes} changes needed")
            
        print(f"\nSummary: {total_changes} total changes needed across {len(path_ids)} paths")
        
        if not args.dry_run and total_changes > 0:
            print(f"Applied all corrections to database")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        # Close database connections
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    main() 