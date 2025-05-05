#!/usr/bin/env python3
import concurrent.futures
import argparse
import time
import random
from urllib.parse import unquote
import sys
import os
import oracledb
import threading
from src.wiki_core import WikiCrawler
from collections import defaultdict

class GeneralWikiCrawler(WikiCrawler):
    def __init__(self, target_depth=10, max_steps=50):
        """
        Initialize a general Wikipedia crawler that follows paths to any depth
        
        Args:
            target_depth: The desired path length to aim for
            max_steps: Maximum number of steps to prevent infinite loops
        """
        super().__init__()
        self.target_depth = target_depth
        self.max_steps = max_steps
        self.philosophy_url = None  # Not targeting Philosophy specifically
        
    def follow_general_path(self, start_url=None):
        """
        Follow a general path from a starting URL to collect data
        
        Returns:
            path: List of URLs in the path
            titles: Dictionary mapping URLs to article titles
            reached_depth: Boolean indicating if target depth was reached
        """
        if not start_url:
            start_url = self.get_random_article()
            
        current_url = start_url
        path = [current_url]
        titles = {}
        steps = 0
        visited_in_path = set([current_url])
        
        print(f"Starting from: {current_url}")
        
        while steps < self.max_steps:
            # Get the next link and current page title
            next_url, current_title = self.extract_first_link(current_url)
            titles[current_url] = current_title
            
            # If we've reached our target depth, we can stop
            if steps >= self.target_depth - 1:
                print(f"Reached target depth of {self.target_depth} steps")
                return path, titles, True
                
            # If no link found, we're at a dead end
            if not next_url:
                print(f"Step {steps}: {current_title} -> Dead end!")
                break
                
            # Loop detection
            if next_url in visited_in_path:
                print(f"Loop detected at step {steps}")
                loop_index = path.index(next_url) if next_url in path else -1
                if loop_index != -1:
                    loop = path[loop_index:] + [next_url]
                    loop_titles = [titles.get(u, self.get_title_from_url(u)) for u in loop]
                    print(f"Loop: {' -> '.join(loop_titles)}")
                break
                
            # Print the current step
            next_title = self.get_title_from_url(next_url)
            print(f"Step {steps}: {current_title} -> {next_title}")
            
            # Add to graph
            self.graph.add_edge(current_title, next_title)
            
            # Move to next URL
            current_url = next_url
            path.append(current_url)
            visited_in_path.add(current_url)
            steps += 1
            
            # Add a slight delay to be nice to Wikipedia servers
            time.sleep(0.5)
            
        # Return the collected path
        return path, titles, (steps >= self.target_depth - 1)


class ParallelWikiController:
    """Controller for parallel Wikipedia crawling operations"""
    
    def __init__(self, num_workers=4, db_host="localhost", db_port=1521, 
                 db_service="XE", db_user="sys", db_password="cyvsi5-vapzUk-qizveb",
                 db_mode=oracledb.AUTH_MODE_SYSDBA, target_depth=10, max_steps=50,
                 max_size_gb=2):
        """
        Initialize the parallel crawler controller
        
        Args:
            num_workers: Number of parallel worker threads
            db_*: Database connection parameters
            target_depth: Target path depth for each crawl
            max_steps: Maximum steps to prevent infinite loops
            max_size_gb: Maximum database size in GB before stopping
        """
        self.num_workers = num_workers
        self.db_host = db_host
        self.db_port = db_port
        self.db_service = db_service
        self.db_user = db_user
        self.db_password = db_password
        self.db_mode = db_mode
        self.target_depth = target_depth
        self.max_steps = max_steps
        self.max_size_gb = max_size_gb
        self.results = []
        self.stop_flag = threading.Event()
        self.size_check_interval = 10  # Check database size every 10 seconds
        self.mapped_articles = set()  # Track already mapped articles
        self.mapped_articles_lock = threading.Lock()  # Lock for thread-safe access
        
    def crawl_article(self, article_or_url):
        """
        Crawl a single article and store its path in the database
        
        Args:
            article_or_url: Article title or full Wikipedia URL
            
        Returns:
            Dictionary with crawl results or None if stopped
        """
        # Check if we should stop
        if self.stop_flag.is_set():
            print(f"Skipping crawl of {article_or_url} due to stop flag")
            return None
            
        # Initialize crawler
        crawler = GeneralWikiCrawler(self.target_depth, self.max_steps)
        
        # Determine start URL
        if article_or_url.startswith("http"):
            start_url = article_or_url
        else:
            # Normalize article title
            article_title = article_or_url.strip().replace(" ", "_")
            start_url = f"https://en.wikipedia.org/wiki/{article_title}"
            
        # Get article title
        start_title = crawler.get_title_from_url(start_url)
        
        # Check if this article has already been mapped
        with self.mapped_articles_lock:
            if start_title in self.mapped_articles:
                print(f"Article '{start_title}' has already been mapped. Getting a new random article...")
                # Try to get a new random article that hasn't been mapped yet
                max_retries = 5
                for _ in range(max_retries):
                    new_url = crawler.get_random_article()
                    new_title = crawler.get_title_from_url(new_url)
                    if new_title not in self.mapped_articles:
                        start_url = new_url
                        start_title = new_title
                        print(f"Using new random article: {start_title}")
                        break
        
        print(f"Worker starting crawl from: {start_title}")
        
        # Execute the crawl
        path, titles, reached_target = crawler.follow_general_path(start_url)
        
        # Check stop flag again before database operations
        if self.stop_flag.is_set():
            print(f"Not storing results for {start_title} due to stop flag")
            return None
            
        # Store results in database
        db = self.connect_to_database()
        if db:
            path_id = self.store_path_in_db(db, path, titles, start_title, reached_target)
            db.close()
            
            # Add all articles in the path to our mapped set
            with self.mapped_articles_lock:
                for url in path:
                    title = titles.get(url, crawler.get_title_from_url(url))
                    self.mapped_articles.add(title)
        else:
            path_id = None
            print(f"Failed to store path for {start_title} due to database connection error")
            
        # Return result information
        result = {
            "start_url": start_url,
            "start_title": start_title,
            "steps": len(path) - 1,
            "reached_target": reached_target,
            "path": path,
            "path_titles": [titles.get(url, crawler.get_title_from_url(url)) for url in path],
            "path_id": path_id
        }
        
        return result
        
    def connect_to_database(self):
        """Connect to the Oracle database"""
        try:
            # Create a new database storage object
            db = WikiDatabaseStorage(
                host=self.db_host,
                port=self.db_port,
                service_name=self.db_service,
                user=self.db_user,
                password=self.db_password,
                mode=self.db_mode
            )
            
            # Connect and setup schema
            if db.connect():
                db.setup_schema()
                return db
            else:
                return None
        except Exception as e:
            print(f"Error setting up database connection: {e}")
            return None
            
    def store_path_in_db(self, db, path, titles, start_article, reached_target):
        """Store a path in the database using the provided connection"""
        try:
            # Get end article
            steps = len(path) - 1 if len(path) > 0 else 0
            end_article = titles.get(path[-1], "Unknown") if path else "Unknown"
            
            # Store the path
            path_id = db.store_path(path, titles, start_article, reached_target)
            
            return path_id
        except Exception as e:
            print(f"Error storing path: {e}")
            return None
    
    def check_database_size(self):
        """
        Monitor database size and set stop flag if it exceeds the limit
        """
        try:
            while not self.stop_flag.is_set():
                # Connect to database
                connection_string = f"{self.db_user}/{self.db_password}@{self.db_host}:{self.db_port}/{self.db_service}"
                connection = oracledb.connect(connection_string, mode=self.db_mode)
                cursor = connection.cursor()
                
                # Query database size
                cursor.execute("""
                    SELECT SUM(bytes)/1024/1024/1024 as GB_SIZE 
                    FROM DBA_SEGMENTS 
                    WHERE OWNER='SYS'
                """)
                
                size_gb = cursor.fetchone()[0] or 0
                print(f"Current database size: {size_gb:.2f} GB / {self.max_size_gb} GB limit")
                
                if size_gb >= self.max_size_gb:
                    print(f"Database size limit of {self.max_size_gb} GB reached! Setting stop flag.")
                    self.stop_flag.set()
                
                # Close connections
                cursor.close()
                connection.close()
                
                # Wait before next check
                time.sleep(self.size_check_interval)
                
        except Exception as e:
            print(f"Error in database size monitoring: {e}")
            # Don't set stop flag for monitoring errors
    
    def load_mapped_articles(self):
        """Load already mapped articles from the database"""
        try:
            # Connect to database
            connection_string = f"{self.db_user}/{self.db_password}@{self.db_host}:{self.db_port}/{self.db_service}"
            connection = oracledb.connect(connection_string, mode=self.db_mode)
            cursor = connection.cursor()
            
            # Query unique article titles
            cursor.execute("""
                SELECT DISTINCT article_title FROM WIKI_PATH_NODES
            """)
            
            # Add to set
            with self.mapped_articles_lock:
                for row in cursor:
                    self.mapped_articles.add(row[0])
            
            article_count = len(self.mapped_articles)
            print(f"Loaded {article_count} already mapped articles from database")
            
            # Close connections
            cursor.close()
            connection.close()
            
        except Exception as e:
            print(f"Error loading mapped articles: {e}")
            
    def run_parallel_crawls(self, start_points=None, num_random=0):
        """
        Run parallel crawls from specified start points
        
        Args:
            start_points: List of article titles or URLs to start from
            num_random: Number of random articles to crawl in addition to start_points
        """
        start_time = time.time()
        all_start_points = []
        
        # Load already mapped articles
        self.load_mapped_articles()
        
        # Start the database size monitor in a background thread
        monitor_thread = threading.Thread(
            target=self.check_database_size, 
            daemon=True
        )
        monitor_thread.start()
        
        # Add specified start points
        if start_points:
            all_start_points.extend(start_points)
            
        # Add random articles if requested
        if num_random > 0:
            temp_crawler = WikiCrawler()
            for _ in range(num_random):
                if self.stop_flag.is_set():
                    break
                random_url = temp_crawler.get_random_article()
                all_start_points.append(random_url)
                time.sleep(0.5)  # Be nice to Wikipedia's servers
                
        # If no start points provided, use random articles
        if not all_start_points:
            temp_crawler = WikiCrawler()
            for _ in range(max(5, self.num_workers)):
                if self.stop_flag.is_set():
                    break
                random_url = temp_crawler.get_random_article()
                all_start_points.append(random_url)
                time.sleep(0.5)
                
        if self.stop_flag.is_set():
            print("Stopping before crawling due to database size limit")
            return self.results
                
        print(f"Starting parallel crawls with {self.num_workers} workers for {len(all_start_points)} articles")
        print(f"Database size limit: {self.max_size_gb} GB")
        
        # Use ThreadPoolExecutor for parallel execution
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.num_workers) as executor:
            # Submit all tasks
            future_to_article = {
                executor.submit(self.crawl_article, article): article
                for article in all_start_points
            }
            
            # Collect results as they complete
            for future in concurrent.futures.as_completed(future_to_article):
                article = future_to_article[future]
                try:
                    # Check if we should stop processing
                    if self.stop_flag.is_set():
                        # Cancel any remaining futures if possible
                        for f in future_to_article:
                            if not f.done():
                                f.cancel()
                        break
                        
                    result = future.result()
                    if result:  # Could be None if stopped
                        self.results.append(result)
                        
                        # Print short summary for this result
                        article_title = result["start_title"]
                        steps = result["steps"]
                        status = "✓" if result["reached_target"] else "✗"
                        path_id = result["path_id"] or "not stored"
                        
                        print(f"\nCompleted: [{status}] {article_title} - {steps} steps (DB ID: {path_id})")
                except Exception as e:
                    print(f"\nError crawling {article}: {e}")
        
        # Calculate and print summary
        end_time = time.time()
        total_time = end_time - start_time
        
        print(f"\n=== CRAWL SUMMARY ===")
        if self.stop_flag.is_set():
            print("Crawl stopped early due to database size limit")
            
        print(f"Completed {len(self.results)} crawls in {total_time:.2f} seconds")
        
        # Stats
        successful = [r for r in self.results if r["reached_target"]]
        success_rate = len(successful) / len(self.results) if self.results else 0
        avg_steps = sum(r["steps"] for r in self.results) / len(self.results) if self.results else 0
        
        print(f"Target depth reached: {success_rate:.2%}")
        print(f"Average path length: {avg_steps:.2f} steps")
        
        # Show total unique articles now
        print(f"Total unique articles in database: approximately {len(self.mapped_articles)}")
        
        # Show a few example paths
        if self.results:
            print("\nSample paths:")
            for i, result in enumerate(self.results[:3]):
                path_str = " -> ".join(result["path_titles"])
                print(f"{i+1}. {result['start_title']} ({result['steps']} steps): {path_str[:150]}...")
        
        return self.results


class WikiDatabaseStorage:
    """Class to store Wikipedia paths in an Oracle database"""
    
    def __init__(self, host="localhost", port=1521, service_name="XE", 
                 user="sys", password="cyvsi5-vapzUk-qizveb", mode=oracledb.AUTH_MODE_SYSDBA):
        """Initialize database connection"""
        self.connection_string = f"{user}/{password}@{host}:{port}/{service_name}"
        self.mode = mode
        self.connection = None
        self.cursor = None
    
    def connect(self):
        """Connect to the Oracle database"""
        try:
            if self.mode:
                self.connection = oracledb.connect(self.connection_string, mode=self.mode)
            else:
                self.connection = oracledb.connect(self.connection_string)
                
            self.cursor = self.connection.cursor()
            print("Connected to Oracle Database")
            return True
        except oracledb.Error as e:
            print(f"Error connecting to Oracle Database: {e}")
            return False
    
    def setup_schema(self):
        """Create the necessary tables if they don't exist"""
        try:
            # Create WIKI_PATHS table to store path metadata
            self.cursor.execute("""
                BEGIN
                    EXECUTE IMMEDIATE 'CREATE TABLE WIKI_PATHS (
                        path_id NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                        start_article VARCHAR2(500),
                        end_article VARCHAR2(500),
                        steps NUMBER,
                        succeeded NUMBER(1),
                        creation_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )';
                EXCEPTION
                    WHEN OTHERS THEN
                        IF SQLCODE = -955 THEN
                            NULL; -- Table already exists
                        ELSE
                            RAISE;
                        END IF;
                END;
            """)
            
            # Create WIKI_PATH_NODES table to store individual nodes in the path
            self.cursor.execute("""
                BEGIN
                    EXECUTE IMMEDIATE 'CREATE TABLE WIKI_PATH_NODES (
                        node_id NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                        path_id NUMBER,
                        step_number NUMBER,
                        article_title VARCHAR2(500),
                        article_url VARCHAR2(2000),
                        CONSTRAINT fk_path_id FOREIGN KEY (path_id) REFERENCES WIKI_PATHS(path_id)
                    )';
                EXCEPTION
                    WHEN OTHERS THEN
                        IF SQLCODE = -955 THEN
                            NULL; -- Table already exists
                        ELSE
                            RAISE;
                        END IF;
                END;
            """)
            
            # Create an index for faster queries
            self.cursor.execute("""
                BEGIN
                    EXECUTE IMMEDIATE 'CREATE INDEX idx_path_id ON WIKI_PATH_NODES(path_id)';
                EXCEPTION
                    WHEN OTHERS THEN
                        IF SQLCODE = -955 OR SQLCODE = -1408 THEN
                            NULL; -- Index already exists
                        ELSE
                            RAISE;
                        END IF;
                END;
            """)
            
            self.connection.commit()
            print("Database schema initialized successfully")
            return True
        except oracledb.Error as e:
            print(f"Error setting up schema: {e}")
            self.connection.rollback()
            return False
    
    def store_path(self, path, titles, start_article, reached_target):
        """Store a path in the database"""
        try:
            # Insert path metadata
            steps = len(path) - 1 if len(path) > 0 else 0
            end_article = titles.get(path[-1], "Unknown") if path else "Unknown"
            
            # Create a variable to store the returned path_id
            path_id_var = self.cursor.var(int)
            
            self.cursor.execute("""
                INSERT INTO WIKI_PATHS (START_ARTICLE, END_ARTICLE, STEPS, SUCCEEDED)
                VALUES (:start_article, :end_article, :steps, :succeeded)
                RETURNING PATH_ID INTO :path_id
            """, {
                'start_article': start_article,
                'end_article': end_article,
                'steps': steps,
                'succeeded': 1 if reached_target else 0,
                'path_id': path_id_var
            })
            
            # Get the path_id from the variable
            path_id = path_id_var.getvalue()[0]
            
            # Insert each node in the path
            for i, url in enumerate(path):
                title = titles.get(url, unquote(url.split('/')[-1].replace('_', ' ')))
                self.cursor.execute("""
                    INSERT INTO WIKI_PATH_NODES (PATH_ID, STEP_NUMBER, ARTICLE_TITLE, ARTICLE_URL)
                    VALUES (:path_id, :step_number, :article_title, :article_url)
                """, {
                    'path_id': path_id,
                    'step_number': i,
                    'article_title': title,
                    'article_url': url
                })
            
            self.connection.commit()
            print(f"Stored path with ID {path_id} in the database")
            return path_id
        except oracledb.Error as e:
            print(f"Error storing path: {e}")
            self.connection.rollback()
            return None
    
    def close(self):
        """Close database connections"""
        if self.cursor:
            self.cursor.close()
        if self.connection:
            self.connection.close()
            print("Database connection closed")


def main():
    parser = argparse.ArgumentParser(description="Parallel Wikipedia Crawler")
    parser.add_argument("-w", "--workers", type=int, default=4, help="Number of parallel workers")
    parser.add_argument("-d", "--depth", type=int, default=10, help="Target path depth")
    parser.add_argument("-m", "--max-steps", type=int, default=50, help="Maximum steps per path")
    parser.add_argument("-a", "--articles", type=str, nargs='+', help="Specific articles to start from")
    parser.add_argument("-r", "--random", type=int, default=0, help="Number of random articles to include")
    
    # Database connection options
    parser.add_argument("--host", type=str, default="localhost", help="Database host")
    parser.add_argument("--port", type=int, default=1521, help="Database port")
    parser.add_argument("--service", type=str, default="XE", help="Database service name")
    parser.add_argument("--user", type=str, default="sys", help="Database username")
    parser.add_argument("--password", type=str, default="cyvsi5-vapzUk-qizveb", help="Database password")
    parser.add_argument("--sysdba", action="store_true", help="Connect as SYSDBA")
    parser.add_argument("--max-size", type=float, default=2, help="Maximum database size in GB")
    
    args = parser.parse_args()
    
    # Determine connection mode
    db_mode = oracledb.AUTH_MODE_SYSDBA if args.sysdba else None
    
    # Create controller
    controller = ParallelWikiController(
        num_workers=args.workers,
        db_host=args.host,
        db_port=args.port,
        db_service=args.service,
        db_user=args.user,
        db_password=args.password,
        db_mode=db_mode,
        target_depth=args.depth,
        max_steps=args.max_steps,
        max_size_gb=args.max_size
    )
    
    # Run the parallel crawls
    controller.run_parallel_crawls(args.articles, args.random)


if __name__ == "__main__":
    main() 