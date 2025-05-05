#!/usr/bin/env python3
import os
import argparse
import oracledb
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import networkx as nx
from collections import Counter

def connect_to_database(host, port, service, user, password, sysdba=False):
    """Connect to the Oracle database"""
    mode=None if sysdba else oracledb.DEFAULT_AUTH
    connection = oracledb.connect(
        user=user,
        password=password,
        dsn=f"{host}:{port}/{service}",
        mode=mode
    )
    return connection

def execute_query(connection, query):
    """Execute SQL query and return results as pandas DataFrame"""
    cursor = connection.cursor()
    cursor.execute(query)
    columns = [col[0] for col in cursor.description]
    data = cursor.fetchall()
    cursor.close()
    return pd.DataFrame(data, columns=columns)

def plot_path_length_distribution(connection):
    """Plot distribution of path lengths"""
    query = """
    SELECT 
        path_id, 
        steps as path_length 
    FROM WIKI_PATHS 
    ORDER BY path_length DESC
    """
    
    df = execute_query(connection, query)
    
    plt.figure(figsize=(10, 6))
    sns.histplot(df['PATH_LENGTH'], kde=True, bins=20)
    plt.title('Distribution of Wikipedia Path Lengths')
    plt.xlabel('Path Length (Number of Steps)')
    plt.ylabel('Frequency')
    plt.grid(True, alpha=0.3)
    plt.savefig('path_length_distribution.png')
    plt.close()
    
    print(f"Average path length: {df['PATH_LENGTH'].mean():.2f} steps")
    print(f"Longest path: {df['PATH_LENGTH'].max()} steps")
    print(f"Shortest path: {df['PATH_LENGTH'].min()} steps")
    
    return df

def plot_common_articles(connection, top_n=20):
    """Plot most common articles that appear in paths"""
    query = f"""
    SELECT 
        article_title, 
        COUNT(*) as frequency
    FROM WIKI_PATH_NODES
    GROUP BY article_title
    ORDER BY frequency DESC
    FETCH FIRST {top_n} ROWS ONLY
    """
    
    df = execute_query(connection, query)
    
    plt.figure(figsize=(12, 8))
    bars = plt.barh(df['ARTICLE_TITLE'][::-1], df['FREQUENCY'][::-1])
    plt.xlabel('Frequency')
    plt.ylabel('Article Title')
    plt.title(f'Top {top_n} Most Common Articles in Paths')
    plt.grid(True, alpha=0.3, axis='x')
    
    # Add frequency labels
    for bar in bars:
        width = bar.get_width()
        plt.text(width + 0.5, bar.get_y() + bar.get_height()/2, 
                f'{int(width)}', ha='left', va='center')
    
    plt.tight_layout()
    plt.savefig('common_articles.png')
    plt.close()
    
    return df

def analyze_common_endpoints(connection):
    """Analyze common endpoints in paths"""
    query = """
    SELECT 
        end_article as endpoint, 
        COUNT(*) as frequency
    FROM WIKI_PATHS
    GROUP BY end_article
    ORDER BY frequency DESC
    """
    
    df = execute_query(connection, query)
    
    plt.figure(figsize=(12, 8))
    if len(df) > 15:
        df = df.head(15)  # Limit to top 15 for readability
        
    bars = plt.barh(df['ENDPOINT'][::-1], df['FREQUENCY'][::-1])
    plt.xlabel('Frequency')
    plt.ylabel('Endpoint Article')
    plt.title('Most Common Endpoints in Wikipedia Paths')
    plt.grid(True, alpha=0.3, axis='x')
    
    # Add frequency labels
    for bar in bars:
        width = bar.get_width()
        plt.text(width + 0.5, bar.get_y() + bar.get_height()/2, 
                f'{int(width)}', ha='left', va='center')
    
    plt.tight_layout()
    plt.savefig('common_endpoints.png')
    plt.close()
    
    return df

def create_path_graph(connection, limit=100):
    """Create a network graph of path connections"""
    query = f"""
    SELECT 
        s1.article_title as source,
        s2.article_title as target,
        COUNT(*) as weight
    FROM 
        WIKI_PATH_NODES s1
    JOIN 
        WIKI_PATH_NODES s2 ON s1.path_id = s2.path_id 
                          AND s1.step_number = s2.step_number - 1
    GROUP BY 
        s1.article_title, s2.article_title
    ORDER BY 
        weight DESC
    FETCH FIRST {limit} ROWS ONLY
    """
    
    df = execute_query(connection, query)
    
    # Create graph
    G = nx.DiGraph()
    
    # Add edges with weights
    for _, row in df.iterrows():
        G.add_edge(row['SOURCE'], row['TARGET'], weight=row['WEIGHT'])
    
    # Limit to most significant nodes if too large
    if len(G.nodes) > 50:
        # Keep only nodes with degree > 1
        to_remove = [node for node, degree in dict(G.degree()).items() if degree <= 1]
        G.remove_nodes_from(to_remove)
    
    # Plot the graph
    plt.figure(figsize=(14, 10))
    
    # Use weight to determine edge thickness and node size based on degree centrality
    edge_weights = [G[u][v]['weight'] * 0.5 for u, v in G.edges()]
    centrality = nx.degree_centrality(G)
    node_sizes = [centrality[node] * 3000 + 100 for node in G.nodes()]
    
    pos = nx.spring_layout(G, k=0.15, iterations=50)
    
    nx.draw_networkx_nodes(G, pos, node_size=node_sizes, node_color='skyblue', alpha=0.8)
    nx.draw_networkx_edges(G, pos, width=edge_weights, alpha=0.5, 
                          edge_color='gray', arrows=True, arrowsize=10)
    
    # Add labels to significant nodes (by centrality)
    significant_nodes = sorted(centrality.items(), key=lambda x: x[1], reverse=True)[:20]
    node_labels = {node: node for node, _ in significant_nodes}
    nx.draw_networkx_labels(G, pos, labels=node_labels, font_size=8)
    
    plt.title('Wikipedia Path Network (Directed)')
    plt.axis('off')
    plt.tight_layout()
    plt.savefig('wiki_path_network.png', dpi=300)
    plt.close()
    
    # Additional network stats
    print(f"Network Analysis:")
    print(f"Number of nodes: {len(G.nodes)}")
    print(f"Number of edges: {len(G.edges)}")
    if len(G.nodes) > 0:
        print(f"Most central articles:")
        for node, cent in sorted(centrality.items(), key=lambda x: x[1], reverse=True)[:5]:
            print(f"  - {node}: {cent:.4f}")
    
    return G

def analyze_loop_patterns(connection):
    """Analyze patterns where loops occur in paths"""
    query = """
    SELECT 
        p.start_article,
        p.path_id,
        n.article_title,
        COUNT(*) as appearances
    FROM 
        WIKI_PATHS p
    JOIN 
        WIKI_PATH_NODES n ON p.path_id = n.path_id
    GROUP BY 
        p.start_article, p.path_id, n.article_title
    HAVING 
        COUNT(*) > 1
    ORDER BY 
        appearances DESC
    """
    
    df = execute_query(connection, query)
    
    if not df.empty:
        # Group by path_id and analyze loop points
        loop_points = df.groupby('PATH_ID')['ARTICLE_TITLE'].apply(list).reset_index()
        
        print("\nLoop Analysis:")
        print(f"Found {len(loop_points)} paths with loops")
        
        # Get the most common loop articles
        all_loop_articles = []
        for articles in df['ARTICLE_TITLE']:
            all_loop_articles.append(articles)
        
        loop_counter = Counter(all_loop_articles)
        print("\nMost common loop articles:")
        for article, count in loop_counter.most_common(10):
            print(f"  - {article}: {count} appearances")
    
    else:
        print("No loops detected in the paths")
    
    return df

def create_html_report(connection):
    """Create an HTML report with all visualizations"""
    path_length_df = plot_path_length_distribution(connection)
    common_articles_df = plot_common_articles(connection)
    endpoint_df = analyze_common_endpoints(connection)
    G = create_path_graph(connection)
    loop_df = analyze_loop_patterns(connection)
    
    # Generate additional statistics using separate queries
    total_paths_query = "SELECT COUNT(*) as total_paths FROM WIKI_PATHS"
    unique_articles_query = "SELECT COUNT(DISTINCT article_title) as unique_articles FROM WIKI_PATH_NODES"
    total_steps_query = "SELECT COUNT(*) as total_steps FROM WIKI_PATH_NODES"
    
    total_paths_df = execute_query(connection, total_paths_query)
    unique_articles_df = execute_query(connection, unique_articles_query)
    total_steps_df = execute_query(connection, total_steps_query)
    
    total_paths = total_paths_df.iloc[0]['TOTAL_PATHS']
    unique_articles = unique_articles_df.iloc[0]['UNIQUE_ARTICLES'] 
    total_steps = total_steps_df.iloc[0]['TOTAL_STEPS']
    
    # Create HTML report
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Wikipedia Path Analysis Report</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; }}
            h1, h2 {{ color: #333366; }}
            .container {{ max-width: 1200px; margin: 0 auto; }}
            .stats {{ background-color: #f5f5f5; padding: 15px; border-radius: 5px; margin-bottom: 20px; }}
            .visualization {{ margin-bottom: 30px; }}
            table {{ border-collapse: collapse; width: 100%; }}
            th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
            th {{ background-color: #f2f2f2; }}
            tr:nth-child(even) {{ background-color: #f9f9f9; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Wikipedia Path Analysis Report</h1>
            
            <div class="stats">
                <h2>Overview Statistics</h2>
                <p>Total Paths: {total_paths}</p>
                <p>Unique Articles: {unique_articles}</p>
                <p>Total Steps: {total_steps}</p>
                <p>Average Path Length: {path_length_df['PATH_LENGTH'].mean():.2f} steps</p>
                <p>Longest Path: {path_length_df['PATH_LENGTH'].max()} steps</p>
                <p>Shortest Path: {path_length_df['PATH_LENGTH'].min()} steps</p>
            </div>
            
            <div class="visualization">
                <h2>Path Length Distribution</h2>
                <img src="path_length_distribution.png" alt="Path Length Distribution" style="max-width:100%;">
            </div>
            
            <div class="visualization">
                <h2>Most Common Articles</h2>
                <img src="common_articles.png" alt="Most Common Articles" style="max-width:100%;">
                
                <h3>Top 10 Most Common Articles</h3>
                <table>
                    <tr>
                        <th>Article Title</th>
                        <th>Frequency</th>
                    </tr>
    """
    
    for _, row in common_articles_df.head(10).iterrows():
        html_content += f"""
                    <tr>
                        <td>{row['ARTICLE_TITLE']}</td>
                        <td>{row['FREQUENCY']}</td>
                    </tr>
        """
    
    html_content += """
                </table>
            </div>
            
            <div class="visualization">
                <h2>Common Endpoints</h2>
                <img src="common_endpoints.png" alt="Common Endpoints" style="max-width:100%;">
            </div>
            
            <div class="visualization">
                <h2>Path Network Visualization</h2>
                <img src="wiki_path_network.png" alt="Path Network" style="max-width:100%;">
            </div>
        </div>
    </body>
    </html>
    """
    
    with open("wiki_path_analysis.html", "w") as file:
        file.write(html_content)
    
    print("\nAnalysis complete! Report saved as wiki_path_analysis.html")

def main():
    parser = argparse.ArgumentParser(description='Analyze Wikipedia path data from Oracle database')
    parser.add_argument('--host', default='localhost', help='Database host')
    parser.add_argument('--port', default=1521, type=int, help='Database port')
    parser.add_argument('--service', default='XE', help='Database service name')
    parser.add_argument('--user', default='sys', help='Database username')
    parser.add_argument('--password', required=True, help='Database password')
    parser.add_argument('--sysdba', action='store_true', help='Connect as SYSDBA')
    
    args = parser.parse_args()
    
    try:
        # Connect to the database
        connection = connect_to_database(
            args.host, args.port, args.service, 
            args.user, args.password, args.sysdba
        )
        print(f"Connected to Oracle Database as {args.user}")
        
        # Create visualizations and report
        create_html_report(connection)
        
        # Close connection
        connection.close()
        print("Database connection closed")
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return 1
    
    return 0

if __name__ == "__main__":
    main() 