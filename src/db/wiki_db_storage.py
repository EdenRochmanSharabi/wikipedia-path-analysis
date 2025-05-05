#!/usr/bin/env python3
import oracledb
import os
import argparse
from wiki_core import WikiCrawler

class WikiDatabaseStorage:
    """Class to store Wikipedia paths in an Oracle database"""
    
    def __init__(self, host="localhost", port=1522, service_name="XE", 
                 user="WIKI_COPY", password="wikipaths"):
        """Initialize database connection"""
        self.connection_string = f"{user}/{password}@{host}:{port}/{service_name}"
        self.mode = mode
        self.connection = None
        self.cursor = None
    
    def connect(self):
        """Connect to the Oracle database"""
        try:
            self.connection = oracledb.connect(self.connection_string, mode=self.mode)
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
            
            self.connection.commit()
            print("Database schema initialized successfully")
            return True
        except oracledb.Error as e:
            print(f"Error setting up schema: {e}")
            self.connection.rollback()
            return False
    
    def store_path(self, path, titles, start_article, reached_philosophy):
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
                'succeeded': 1 if reached_philosophy else 0,
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

def crawl_and_store(article_title, max_steps=100, db_host="localhost", db_port=1522, 
                   db_service="XE", db_user="WIKI_COPY", db_password="wikipaths"):
    """Crawl Wikipedia starting from article_title and store the path in the database"""
    # Initialize the crawler
    crawler = WikiCrawler()
    
    # Normalize article title
    article_title = article_title.strip().replace(" ", "_")
    start_url = f"https://en.wikipedia.org/wiki/{article_title}"
    
    # Follow the path
    print(f"Starting crawl from: {article_title}")
    path, steps, titles = crawler.follow_path(start_url, max_steps)
    
    # Determine if we reached Philosophy
    reached_philosophy = any(title == "Philosophy" for title in titles.values())
    
    # Store the results in the database
    db = WikiDatabaseStorage(
        host=db_host, 
        port=db_port, 
        service_name=db_service,
        user=db_user,
        password=db_password
    )
    
    if db.connect():
        db.setup_schema()
        path_id = db.store_path(path, titles, article_title, reached_philosophy)
        db.close()
        
        if path_id:
            print(f"Successfully stored path from '{article_title}' in database with ID {path_id}")
        
    # Visualize the path
    crawler.visualize_graph(f"{article_title}_to_philosophy.png")
    
    return path, titles, reached_philosophy

def main():
    parser = argparse.ArgumentParser(description="Crawl Wikipedia and store paths in Oracle Database")
    parser.add_argument("article", type=str, help="Title of the Wikipedia article to start from")
    parser.add_argument("-s", "--steps", type=int, default=100, help="Maximum steps to take")
    parser.add_argument("--host", type=str, default="localhost", help="Oracle database host")
    parser.add_argument("--port", type=int, default=1522, help="Oracle database port")
    parser.add_argument("--service", type=str, default="XE", help="Oracle database service name")
    parser.add_argument("--user", type=str, default="sys", help="Oracle database username")
    parser.add_argument("--password", type=str, default="wikipaths", help="Oracle database password")
    
    args = parser.parse_args()
    
    crawl_and_store(
        args.article, 
        args.steps, 
        args.host, 
        args.port, 
        args.service, 
        args.user, 
        args.password
    )

if __name__ == "__main__":
    main() 