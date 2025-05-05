#!/usr/bin/env python3
import concurrent.futures
import argparse
import time
import random
import sys
import os
import threading
import oracledb
from urllib.parse import unquote
from wiki_core import WikiCrawler

class DeepWikiCrawler(WikiCrawler):
    """A deep crawler for building a large graph of Wikipedia articles"""
    
    def __init__(self, max_steps=1000):
        """
        Initialize a deep Wikipedia crawler that follows paths until encountering loops
        or previously explored articles.
        
        Args:
            max_steps: Hard limit on steps to prevent infinite crawls in case of issues
        """
        super().__init__()
        self.max_steps = max_steps
        
    def crawl_deeply(self, start_url=None, visited_global=None):
        """
        Follow a deep path from a starting URL, stopping when hitting loops or 
        previously visited articles in the global set
        
        Args:
            start_url: Starting Wikipedia URL
            visited_global: Set of globally visited article titles
            
        Returns:
            path: List of URLs in the path
            titles: Dictionary mapping URLs to article titles
            visited_articles: Set of article titles visited in this crawl
        """
        if not start_url:
            start_url = self.get_random_article()
            
        # Track articles visited in this crawl separately from the global set
        visited_articles = set()
        current_url = start_url
        path = [current_url]
        titles = {}
        steps = 0
        visited_in_path = set([current_url])
        
        # Get starting title
        start_title = self.get_title_from_url(start_url)
        print(f"Starting deep crawl from: {start_title}")
        
        # Check if we've already visited this article globally
        if visited_global is not None and start_title in visited_global:
            print(f"Article {start_title} already in database, skipping")
            return path, titles, visited_articles
            
        # Add starting article to visited sets
        visited_articles.add(start_title)
        if visited_global is not None:
            visited_global.add(start_title)
        
        while steps < self.max_steps:
            # Get the next link and current page title
            next_url, current_title = self.extract_first_link(current_url)
            titles[current_url] = current_title
            
            # If no link found, we're at a dead end
            if not next_url:
                print(f"Step {steps}: {current_title} -> Dead end!")
                break
                
            # Get the title of the next article
            next_title = self.get_title_from_url(next_url)
            
            # Loop detection within this path
            if next_url in visited_in_path:
                print(f"Loop detected at step {steps}")
                loop_index = path.index(next_url) if next_url in path else -1
                if loop_index != -1:
                    loop = path[loop_index:] + [next_url]
                    loop_titles = [titles.get(u, self.get_title_from_url(u)) for u in loop]
                    print(f"Loop: {' -> '.join(loop_titles)}")
                break
                
            # Check if we've already visited this article globally
            if visited_global is not None and next_title in visited_global:
                print(f"Step {steps}: {current_title} -> {next_title} (already in database)")
                # Still add this link to our current path for storage
                path.append(next_url)
                titles[next_url] = next_title
                break
                
            # Print the current step
            print(f"Step {steps}: {current_title} -> {next_title}")
            
            # Add to graph and visited sets
            self.graph.add_edge(current_title, next_title)
            visited_articles.add(next_title)
            if visited_global is not None:
                visited_global.add(next_title)
            
            # Move to next URL
            current_url = next_url
            path.append(current_url)
            visited_in_path.add(current_url)
            steps += 1
            
            # Add a slight delay to be nice to Wikipedia servers
            time.sleep(0.5)
            
        # Return the collected path and visited articles
        return path, titles, visited_articles


class LargeWikiGraphController:
    """Controller for large-scale Wikipedia graph crawling operations"""
    
    def __init__(self, num_workers=6, db_host="localhost", db_port=1521, 
                 db_service="XE", db_user="sys", db_password="cyvsi5-vapzUk-qizveb",
                 db_mode=oracledb.AUTH_MODE_SYSDBA, max_steps=1000,
                 max_size_gb=10):
        """
        Initialize the large-scale crawler controller
        
        Args:
            num_workers: Number of parallel worker threads
            db_*: Database connection parameters
            max_steps: Maximum steps per path to prevent infinite crawls
            max_size_gb: Maximum database size in GB before stopping
        """
        self.num_workers = num_workers
        self.db_host = db_host
        self.db_port = db_port
        self.db_service = db_service
        self.db_user = db_user
        self.db_password = db_password
        self.db_mode = db_mode
        self.max_steps = max_steps
        self.max_size_gb = max_size_gb
        self.results = []
        self.stop_flag = threading.Event()
        self.size_check_interval = 30  # Check database size every 30 seconds
        
        # Thread-safe set of globally visited articles
        self.visited_articles_lock = threading.Lock()
        self.visited_articles = set()
        
    def load_existing_articles(self):
        """Load all existing article titles from the database into the visited set"""
        try:
            print("Loading existing article titles from database...")
            db = self.connect_to_database()
            if not db:
                print("Failed to connect to database to load existing articles")
                return
                
            cursor = db.connection.cursor()
            
            # Get starting articles
            cursor.execute("""
                SELECT start_article FROM WIKI_PATHS
            """)
            start_articles = [row[0] for row in cursor.fetchall()]
            
            # Get all articles from path nodes
            cursor.execute("""
                SELECT DISTINCT article_title FROM WIKI_PATH_NODES
            """)
            article_titles = [row[0] for row in cursor.fetchall()]
            
            # Update visited articles set
            with self.visited_articles_lock:
                self.visited_articles.update(start_articles)
                self.visited_articles.update(article_titles)
                
            cursor.close()
            db.close()
            
            print(f"Loaded {len(self.visited_articles)} existing articles from database")
            
        except Exception as e:
            print(f"Error loading existing articles: {e}")
        
    def crawl_article(self, start_url=None):
        """
        Crawl a single article deeply and store its path in the database
        
        Args:
            start_url: Starting article URL or None for random article
            
        Returns:
            Dictionary with crawl results or None if stopped
        """
        # Check if we should stop
        if self.stop_flag.is_set():
            print(f"Skipping crawl due to stop flag")
            return None
            
        # Initialize crawler
        crawler = DeepWikiCrawler(self.max_steps)
        
        # Use random article if none provided
        if not start_url:
            start_url = crawler.get_random_article()
            
        # Get a thread-safe reference to the global visited set
        with self.visited_articles_lock:
            visited_global = self.visited_articles.copy()
        
        # Execute the deep crawl
        path, titles, visited_in_crawl = crawler.crawl_deeply(start_url, visited_global)
        
        # Update the global visited set with newly visited articles
        with self.visited_articles_lock:
            self.visited_articles.update(visited_in_crawl)
        
        # Get start and end titles
        start_title = titles.get(path[0], crawler.get_title_from_url(path[0]))
        end_title = titles.get(path[-1], crawler.get_title_from_url(path[-1])) if path else "Unknown"
        
        # Check stop flag again before database operations
        if self.stop_flag.is_set():
            print(f"Not storing results for {start_title} due to stop flag")
            return None
            
        # Store results in database
        db = self.connect_to_database()
        if db:
            path_id = self.store_path_in_db(db, path, titles, start_title, True)
            db.close()
        else:
            path_id = None
            print(f"Failed to store path for {start_title} due to database connection error")
            
        # Return result information
        result = {
            "start_url": start_url,
            "start_title": start_title,
            "end_title": end_title,
            "steps": len(path) - 1,
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
            
    def store_path_in_db(self, db, path, titles, start_article, success=True):
        """Store a path in the database using the provided connection"""
        try:
            # Get end article
            steps = len(path) - 1 if len(path) > 0 else 0
            end_article = titles.get(path[-1], "Unknown") if path else "Unknown"
            
            # Store the path
            path_id = db.store_path(path, titles, start_article, success)
            
            return path_id
        except Exception as e:
            print(f"Error storing path: {e}")
            return None
            
    def check_database_size(self):
        """Check the current database size and set stop flag if it exceeds the limit"""
        try:
            # Connect to the database
            connection = oracledb.connect(
                user=self.db_user,
                password=self.db_password,
                dsn=f"{self.db_host}:{self.db_port}/{self.db_service}",
                mode=self.db_mode
            )
            
            cursor = connection.cursor()
            
            # Query to get database size in GB
            cursor.execute("""
                SELECT 
                    SUM(bytes) / (1024 * 1024 * 1024) as size_gb
                FROM 
                    dba_data_files
            """)
            
            result = cursor.fetchone()
            if result and result[0]:
                current_size_gb = result[0]
                
                # Print current size
                print(f"Current database size: {current_size_gb:.2f} GB / {self.max_size_gb} GB limit")
                
                # Set stop flag if size exceeds limit
                if current_size_gb >= self.max_size_gb:
                    print(f"Database size limit of {self.max_size_gb} GB reached, stopping crawlers")
                    self.stop_flag.set()
                    return True
            
            cursor.close()
            connection.close()
            
        except Exception as e:
            print(f"Error checking database size: {e}")
            
        return False
        
    def size_monitor_thread(self):
        """Thread that monitors database size periodically"""
        while not self.stop_flag.is_set():
            if self.check_database_size():
                break
            
            # Sleep for interval
            time.sleep(self.size_check_interval)
            
    def run_large_graph_crawl(self, num_initial_articles=6):
        """
        Run a large graph crawl with the specified number of workers
        
        Args:
            num_initial_articles: Number of initial random articles to start from
        """
        # First load existing articles from the database to avoid duplicates
        self.load_existing_articles()
        
        # Start size monitoring thread
        monitor_thread = threading.Thread(target=self.size_monitor_thread)
        monitor_thread.daemon = True
        monitor_thread.start()
        
        print(f"Starting large graph crawl with {self.num_workers} workers")
        print(f"Database size limit: {self.max_size_gb} GB")
        print(f"Starting from {num_initial_articles} random articles")
        
        # Start with initial random articles
        initial_articles = []
        for _ in range(num_initial_articles):
            initial_crawl = self.crawl_article()
            if initial_crawl:
                initial_articles.append(initial_crawl)
            
            # Check stop flag after each initial crawl
            if self.stop_flag.is_set():
                print("Stop flag set, aborting initial crawls")
                break
        
        # Continue with worker threads for continuous crawling
        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=self.num_workers) as executor:
                # Keep submitting new tasks until we reach the size limit
                future_to_crawl = {}
                
                # Initial batch of tasks
                for _ in range(self.num_workers):
                    if not self.stop_flag.is_set():
                        future = executor.submit(self.crawl_article)
                        future_to_crawl[future] = None
                
                # Keep adding new tasks as old ones complete
                while future_to_crawl and not self.stop_flag.is_set():
                    # Wait for the first task to complete
                    done, not_done = concurrent.futures.wait(
                        future_to_crawl, 
                        return_when=concurrent.futures.FIRST_COMPLETED
                    )
                    
                    # Process completed tasks
                    for future in done:
                        try:
                            result = future.result()
                            if result:
                                self.results.append(result)
                                
                            # Remove from tracking dict
                            future_to_crawl.pop(future, None)
                            
                            # Start a new task if not stopped
                            if not self.stop_flag.is_set():
                                new_future = executor.submit(self.crawl_article)
                                future_to_crawl[new_future] = None
                                
                        except Exception as e:
                            print(f"Error processing crawl result: {e}")
                            
        except KeyboardInterrupt:
            print("Keyboard interrupt received, stopping crawlers")
            self.stop_flag.set()
            
        # Wait for monitor thread to finish
        monitor_thread.join(timeout=5)
        
        # Print summary
        total_paths = len(self.results)
        total_articles = len(self.visited_articles)
        print(f"\nCrawl completed or stopped")
        print(f"Total paths crawled: {total_paths}")
        print(f"Total unique articles: {total_articles}")
        
        # Final size check
        self.check_database_size()


class WikiDatabaseStorage:
    """Class to store Wikipedia paths in an Oracle database"""
    
    def __init__(self, host="localhost", port=1521, service_name="XE", 
                 user="sys", password="cyvsi5-vapzUk-qizveb", mode=oracledb.AUTH_MODE_SYSDBA):
        """Initialize database connection"""
        self.host = host
        self.port = port
        self.service_name = service_name
        self.user = user
        self.password = password
        self.mode = mode
        self.connection = None
        self.cursor = None
    
    def connect(self):
        """Connect to the Oracle database"""
        try:
            self.connection = oracledb.connect(
                user=self.user,
                password=self.password,
                dsn=f"{self.host}:{self.port}/{self.service_name}",
                mode=self.mode
            )
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
                        IF SQLCODE = -955 THEN
                            NULL; -- Index already exists
                        ELSE
                            RAISE;
                        END IF;
                END;
            """)
            
            # Create an index on article_title for faster lookups
            self.cursor.execute("""
                BEGIN
                    EXECUTE IMMEDIATE 'CREATE INDEX idx_article_title ON WIKI_PATH_NODES(article_title)';
                EXCEPTION
                    WHEN OTHERS THEN
                        IF SQLCODE = -955 THEN
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
                title = titles.get(url, "Unknown")
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
    parser = argparse.ArgumentParser(description="Build a large Wikipedia graph database")
    parser.add_argument("-w", "--workers", type=int, default=6, help="Number of worker threads")
    parser.add_argument("-s", "--max-steps", type=int, default=1000, help="Maximum steps per path")
    parser.add_argument("-m", "--max-size", type=float, default=10, help="Maximum database size in GB")
    parser.add_argument("-i", "--initial", type=int, default=6, help="Number of initial random articles")
    
    # Database connection parameters
    parser.add_argument("--host", type=str, default="localhost", help="Database host")
    parser.add_argument("--port", type=int, default=1521, help="Database port")
    parser.add_argument("--service", type=str, default="XE", help="Database service name")
    parser.add_argument("--user", type=str, default="sys", help="Database username")
    parser.add_argument("--password", type=str, default="cyvsi5-vapzUk-qizveb", help="Database password")
    parser.add_argument("--sysdba", action="store_true", help="Connect as SYSDBA")
    
    args = parser.parse_args()
    
    # Set up the controller
    db_mode = oracledb.AUTH_MODE_SYSDBA if args.sysdba else oracledb.DEFAULT_AUTH
    controller = LargeWikiGraphController(
        num_workers=args.workers,
        db_host=args.host,
        db_port=args.port,
        db_service=args.service,
        db_user=args.user,
        db_password=args.password,
        db_mode=db_mode,
        max_steps=args.max_steps,
        max_size_gb=args.max_size
    )
    
    # Run the crawl
    controller.run_large_graph_crawl(args.initial)


if __name__ == "__main__":
    main() 