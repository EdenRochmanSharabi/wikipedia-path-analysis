#!/usr/bin/env python3
import oracledb
import argparse

class WikiDatabaseQuery:
    """Class to query Wikipedia paths from the Oracle database"""
    
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
    
    def list_all_paths(self):
        """List all stored paths"""
        try:
            self.cursor.execute("""
                SELECT path_id, start_article, end_article, steps, 
                       CASE WHEN succeeded = 1 THEN 'Yes' ELSE 'No' END as reached_philosophy,
                       TO_CHAR(creation_date, 'YYYY-MM-DD HH24:MI:SS') as creation_date
                FROM WIKI_PATHS
                ORDER BY creation_date DESC
            """)
            
            rows = self.cursor.fetchall()
            if not rows:
                print("No paths found in the database.")
                return []
            
            print("\n=== ALL WIKIPEDIA PATHS ===")
            print(f"{'ID':<5} {'Start Article':<20} {'End Article':<20} {'Steps':<6} {'Reached Philosophy':<20} {'Created On':<20}")
            print("-" * 90)
            
            for row in rows:
                path_id, start_article, end_article, steps, reached_philosophy, creation_date = row
                print(f"{path_id:<5} {start_article[:20]:<20} {end_article[:20]:<20} {steps:<6} {reached_philosophy:<20} {creation_date:<20}")
            
            return rows
        except oracledb.Error as e:
            print(f"Error querying paths: {e}")
            return []
    
    def show_path_details(self, path_id):
        """Show details of a specific path"""
        try:
            # Get path metadata
            self.cursor.execute("""
                SELECT path_id, start_article, end_article, steps, 
                       CASE WHEN succeeded = 1 THEN 'Yes' ELSE 'No' END as reached_philosophy,
                       TO_CHAR(creation_date, 'YYYY-MM-DD HH24:MI:SS') as creation_date
                FROM WIKI_PATHS
                WHERE path_id = :path_id
            """, {'path_id': path_id})
            
            path_info = self.cursor.fetchone()
            if not path_info:
                print(f"No path found with ID {path_id}.")
                return None
            
            path_id, start_article, end_article, steps, reached_philosophy, creation_date = path_info
            
            print(f"\n=== PATH {path_id} DETAILS ===")
            print(f"Start Article: {start_article}")
            print(f"End Article: {end_article}")
            print(f"Steps: {steps}")
            print(f"Reached Philosophy: {reached_philosophy}")
            print(f"Created On: {creation_date}")
            
            # Get path nodes
            self.cursor.execute("""
                SELECT step_number, article_title, article_url
                FROM WIKI_PATH_NODES
                WHERE path_id = :path_id
                ORDER BY step_number
            """, {'path_id': path_id})
            
            nodes = self.cursor.fetchall()
            
            if nodes:
                print("\n=== PATH SEQUENCE ===")
                print(f"{'Step':<5} {'Article Title':<40} {'URL':<50}")
                print("-" * 95)
                
                for node in nodes:
                    step_number, article_title, article_url = node
                    print(f"{step_number:<5} {article_title[:40]:<40} {article_url[:50]:<50}")
            
            return path_info, nodes
        except oracledb.Error as e:
            print(f"Error querying path details: {e}")
            return None
    
    def get_statistics(self):
        """Get statistics about stored paths"""
        try:
            # Get general statistics
            self.cursor.execute("""
                SELECT 
                    COUNT(*) as total_paths,
                    SUM(CASE WHEN succeeded = 1 THEN 1 ELSE 0 END) as successful_paths,
                    AVG(steps) as avg_steps,
                    MIN(steps) as min_steps,
                    MAX(steps) as max_steps
                FROM WIKI_PATHS
            """)
            
            general_stats = self.cursor.fetchone()
            if not general_stats:
                print("No data available for statistics.")
                return None
            
            total_paths, successful_paths, avg_steps, min_steps, max_steps = general_stats
            
            print("\n=== WIKIPEDIA PATH STATISTICS ===")
            print(f"Total Paths: {total_paths}")
            print(f"Successful Paths: {successful_paths} ({(successful_paths/total_paths)*100 if total_paths > 0 else 0:.2f}%)")
            print(f"Average Steps: {avg_steps:.2f}")
            print(f"Minimum Steps: {min_steps}")
            print(f"Maximum Steps: {max_steps}")
            
            # Get most common intermediate articles
            self.cursor.execute("""
                SELECT article_title, COUNT(*) as occurrence_count
                FROM WIKI_PATH_NODES n
                JOIN WIKI_PATHS p ON n.path_id = p.path_id
                WHERE p.succeeded = 1
                GROUP BY article_title
                ORDER BY occurrence_count DESC
            """)
            
            common_articles = self.cursor.fetchmany(10)
            
            if common_articles:
                print("\n=== MOST COMMON ARTICLES IN PATHS TO PHILOSOPHY ===")
                print(f"{'Article Title':<40} {'Occurrences':<15}")
                print("-" * 55)
                
                for article in common_articles:
                    article_title, count = article
                    print(f"{article_title[:40]:<40} {count:<15}")
            
            return general_stats, common_articles
        except oracledb.Error as e:
            print(f"Error getting statistics: {e}")
            return None
    
    def close(self):
        """Close database connections"""
        if self.cursor:
            self.cursor.close()
        if self.connection:
            self.connection.close()
            print("\nDatabase connection closed")

def main():
    parser = argparse.ArgumentParser(description="Query Wikipedia paths from Oracle Database")
    parser.add_argument("--host", type=str, default="localhost", help="Oracle database host")
    parser.add_argument("--port", type=int, default=1522, help="Oracle database port")
    parser.add_argument("--service", type=str, default="XE", help="Oracle database service name")
    parser.add_argument("--user", type=str, default="sys", help="Oracle database username")
    parser.add_argument("--password", type=str, default="wikipaths", help="Oracle database password")
    parser.add_argument("--list", action="store_true", help="List all paths")
    parser.add_argument("--path", type=int, help="Show details for a specific path ID")
    parser.add_argument("--stats", action="store_true", help="Show statistics about stored paths")
    
    args = parser.parse_args()
    
    db = WikiDatabaseQuery(
        host=args.host, 
        port=args.port, 
        service_name=args.service,
        user=args.user,
        password=args.password
    )
    
    if db.connect():
        if args.list:
            db.list_all_paths()
        elif args.path is not None:
            db.show_path_details(args.path)
        elif args.stats:
            db.get_statistics()
        else:
            # If no specific query is requested, show all paths and statistics
            db.list_all_paths()
            db.get_statistics()
        
        db.close()

if __name__ == "__main__":
    main() 