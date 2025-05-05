#!/usr/bin/env python3
import sys
import os
import time
import subprocess
import argparse

# Add the project root to the Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

def main():
    parser = argparse.ArgumentParser(description="Continuous Wikipedia Crawler")
    parser.add_argument("-w", "--workers", type=int, default=8, help="Number of parallel workers")
    parser.add_argument("-b", "--batch-size", type=int, default=100, help="Number of random articles per batch")
    parser.add_argument("-d", "--depth", type=int, default=10, help="Target path depth")
    parser.add_argument("-m", "--max-steps", type=int, default=50, help="Maximum steps per path")
    parser.add_argument("--max-size", type=float, default=10, help="Maximum database size in GB")
    parser.add_argument("--host", type=str, default="localhost", help="Database host")
    parser.add_argument("--port", type=int, default=1521, help="Database port")
    parser.add_argument("--service", type=str, default="XE", help="Database service name")
    parser.add_argument("--user", type=str, default="system", help="Database username")
    parser.add_argument("--password", type=str, default="oracle", help="Database password")
    parser.add_argument("--sysdba", action="store_true", help="Connect as SYSDBA")
    parser.add_argument("--delay", type=int, default=5, help="Delay between batches in seconds")
    
    args = parser.parse_args()
    
    print(f"Starting continuous Wikipedia crawler with {args.workers} workers")
    print(f"Each batch will crawl {args.batch_size} random articles")
    print(f"Target depth: {args.depth}, Max steps: {args.max_steps}")
    print(f"Database size limit: {args.max_size} GB")
    print(f"Press Ctrl+C to stop the crawler")
    
    batch_count = 0
    total_articles = 0
    
    try:
        while True:
            batch_count += 1
            print(f"\n=== Starting batch #{batch_count} ===")
            
            # Construct the command to run the crawler
            cmd = [
                sys.executable, "-m", "src.crawlers.parallel_wiki_crawler",
                "-w", str(args.workers),
                "-r", str(args.batch_size),
                "-d", str(args.depth),
                "-m", str(args.max_steps),
                "--max-size", str(args.max_size),
                "--host", args.host,
                "--port", str(args.port),
                "--service", args.service,
                "--user", args.user,
                "--password", args.password
            ]
            
            if args.sysdba:
                cmd.append("--sysdba")
            
            # Run the crawler
            result = subprocess.run(cmd, capture_output=False)
            
            if result.returncode != 0:
                print(f"Crawler process exited with code {result.returncode}")
                
            # Count articles crawled in this batch
            # This is approximate since we don't capture the crawler's output
            total_articles += args.batch_size
            print(f"Approximately {total_articles} articles crawled so far")
            
            # Sleep before the next batch
            print(f"Waiting {args.delay} seconds before starting next batch...")
            time.sleep(args.delay)
            
    except KeyboardInterrupt:
        print("\nCrawling stopped by user")
        print(f"Completed {batch_count} batches with approximately {total_articles} articles")
        
if __name__ == "__main__":
    main() 