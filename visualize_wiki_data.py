#!/usr/bin/env python3
import pandas as pd
import matplotlib.pyplot as plt
import oracledb
import networkx as nx
import argparse
import os
from collections import Counter
import seaborn as sns
import numpy as np

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

def get_table_schema(conn, tables, table_name):
    """Get the appropriate schema for a table"""
    schemas_to_check = []
    
    if 'wiki_user' in tables and table_name in tables['wiki_user']:
        schemas_to_check.append('WIKI_USER')
    
    if 'system' in tables and table_name in tables['system']:
        schemas_to_check.append('SYSTEM')
    
    if not schemas_to_check:
        return None
    
    # If we have both schemas, check which one has more rows
    if len(schemas_to_check) > 1:
        max_rows = 0
        best_schema = None
        
        for schema in schemas_to_check:
            cursor = conn.cursor()
            cursor.execute(f"SELECT COUNT(*) FROM {schema}.{table_name}")
            count = cursor.fetchone()[0]
            print(f"Found {count} rows in {schema}.{table_name}")
            
            if count > max_rows:
                max_rows = count
                best_schema = schema
        
        return best_schema
    
    # If we only have one schema, return it
    return schemas_to_check[0]

def create_bar_chart(conn, output_dir, tables):
    """Create a bar chart of most common articles"""
    # Get the appropriate schema
    path_nodes_schema = get_table_schema(conn, tables, 'WIKI_PATH_NODES')
    
    if not path_nodes_schema:
        print("Could not find WIKI_PATH_NODES table in any schema")
        return
        
    query = f"""
    SELECT article_title as "article_title", COUNT(*) as "frequency"
    FROM {path_nodes_schema}.WIKI_PATH_NODES
    GROUP BY article_title
    ORDER BY COUNT(*) DESC
    FETCH FIRST 15 ROWS ONLY
    """
    
    try:
        # Execute query and get data
        df = pd.read_sql(query, conn)
        
        if len(df) == 0:
            print("No data available for bar chart")
            return
        
        # Convert column names to lowercase for consistency
        df.columns = df.columns.str.lower()
            
        # Create visualization
        plt.figure(figsize=(12, 8))
        chart = sns.barplot(x='frequency', y='article_title', data=df, palette='viridis')
        
        # Format chart
        plt.title('Most Common Wikipedia Articles in Paths', fontsize=16)
        plt.xlabel('Frequency', fontsize=12)
        plt.ylabel('Article', fontsize=12)
        plt.tight_layout()
        
        # Save the figure
        output_file = os.path.join(output_dir, 'wiki_article_frequency.png')
        plt.savefig(output_file, dpi=300)
        plt.close()
        
        print(f"Bar chart saved to {output_file}")
        
    except Exception as e:
        print(f"Error creating bar chart: {e}")

def create_network_graph(conn, output_dir, tables):
    """Create a network graph of article connections"""
    # Get the appropriate schema
    path_nodes_schema = get_table_schema(conn, tables, 'WIKI_PATH_NODES')
    
    if not path_nodes_schema:
        print("Could not find WIKI_PATH_NODES table in any schema")
        return
        
    query = f"""
    SELECT 
        src.article_title as "source",
        dst.article_title as "target",
        COUNT(*) as "weight"
    FROM 
        {path_nodes_schema}.WIKI_PATH_NODES src,
        {path_nodes_schema}.WIKI_PATH_NODES dst
    WHERE 
        src.path_id = dst.path_id
        AND dst.step_number = src.step_number + 1
    GROUP BY
        src.article_title, dst.article_title
    """
    
    try:
        # Execute query and get data
        df = pd.read_sql(query, conn)
        
        if len(df) == 0:
            print("No data available for network graph")
            return
        
        # Convert column names to lowercase for consistency
        df.columns = df.columns.str.lower()
        
        # Convert weight column to numeric to ensure it's properly handled
        df['weight'] = pd.to_numeric(df['weight'])
        
        # Create network graph - specify edge_attr properly
        G = nx.from_pandas_edgelist(df, 'source', 'target', edge_attr='weight')
        
        # Set node size based on degree centrality
        centrality = nx.degree_centrality(G)
        node_size = [centrality[node] * 5000 + 100 for node in G.nodes()]
        
        # Create visualization
        plt.figure(figsize=(16, 12))
        pos = nx.spring_layout(G, seed=42, k=0.3)
        
        # Draw nodes with size based on centrality
        nx.draw_networkx_nodes(G, pos, node_size=node_size, node_color='lightblue', alpha=0.8)
        
        # Draw edges with width based on weight
        edge_width = [G[u][v]['weight'] * 0.5 + 0.1 for u, v in G.edges()]
        nx.draw_networkx_edges(G, pos, width=edge_width, alpha=0.6, edge_color='gray')
        
        # Draw labels for important nodes (high centrality)
        important_nodes = {node: node for node, cent in centrality.items() if cent > 0.05}
        nx.draw_networkx_labels(G, pos, labels=important_nodes, font_size=8, font_weight='bold')
        
        plt.title('Wikipedia Article Network', fontsize=16)
        plt.axis('off')
        plt.tight_layout()
        
        # Save the figure
        output_file = os.path.join(output_dir, 'wiki_network_graph.png')
        plt.savefig(output_file, dpi=300)
        plt.close()
        
        print(f"Network graph saved to {output_file}")
        
    except Exception as e:
        print(f"Error creating network graph: {e}")

def create_circular_network(conn, output_dir, tables):
    """Create a circular network visualization of article connections"""
    # Get the appropriate schema
    path_nodes_schema = get_table_schema(conn, tables, 'WIKI_PATH_NODES')
    
    if not path_nodes_schema:
        print("Could not find WIKI_PATH_NODES table in any schema")
        return
        
    query = f"""
    SELECT 
        src.article_title as "source",
        dst.article_title as "target",
        COUNT(*) as "weight"
    FROM 
        {path_nodes_schema}.WIKI_PATH_NODES src,
        {path_nodes_schema}.WIKI_PATH_NODES dst
    WHERE 
        src.path_id = dst.path_id
        AND dst.step_number = src.step_number + 1
    GROUP BY
        src.article_title, dst.article_title
    """
    
    try:
        # Execute query and get data
        df = pd.read_sql(query, conn)
        
        if len(df) == 0:
            print("No data available for circular network visualization")
            return
        
        # Convert column names to lowercase for consistency
        df.columns = df.columns.str.lower()
        
        # Convert weight column to numeric to ensure it's properly handled
        df['weight'] = pd.to_numeric(df['weight'])
        
        # Create network graph
        G = nx.from_pandas_edgelist(df, 'source', 'target', edge_attr='weight')
        
        # Calculate betweenness centrality (measures bridge nodes)
        betweenness = nx.betweenness_centrality(G)
        
        # Set node colors based on betweenness centrality
        node_colors = [plt.cm.plasma(betweenness[node] * 4) for node in G.nodes()]
        
        # Node sizes based on degree
        node_degrees = dict(G.degree())
        node_size = [node_degrees[node] * 100 + 100 for node in G.nodes()]
        
        # Create circular layout visualization
        fig, ax = plt.subplots(figsize=(20, 20))
        pos = nx.circular_layout(G)
        
        # Draw nodes
        nx.draw_networkx_nodes(G, pos, node_size=node_size, node_color=node_colors, alpha=0.8, ax=ax)
        
        # Draw edges with weight-based width
        edge_width = [G[u][v]['weight'] * 0.5 + 0.1 for u, v in G.edges()]
        
        # Draw straight edges (curved edges cause warnings with this graph type)
        nx.draw_networkx_edges(
            G, pos, 
            width=edge_width,
            alpha=0.5,
            edge_color='gray',
            ax=ax
        )
        
        # Label only important nodes to avoid clutter
        # Use betweenness and degree to identify important nodes
        important_nodes = {
            node: node for node in G.nodes() 
            if betweenness[node] > 0.05 or node_degrees[node] > 2
        }
        nx.draw_networkx_labels(
            G, pos, 
            labels=important_nodes, 
            font_size=8, 
            font_weight='bold',
            font_color='black',
            ax=ax
        )
        
        # Add a colorbar legend for betweenness centrality
        sm = plt.cm.ScalarMappable(cmap=plt.cm.plasma, norm=plt.Normalize(vmin=0, vmax=max(betweenness.values())))
        sm.set_array([])
        cbar = plt.colorbar(sm, ax=ax, shrink=0.6)
        cbar.set_label('Betweenness Centrality')
        
        plt.title('Wikipedia Article Relationship Network (Circular Layout)', fontsize=18)
        plt.axis('off')
        plt.tight_layout()
        
        # Save the figure
        output_file = os.path.join(output_dir, 'wiki_circular_network.png')
        plt.savefig(output_file, dpi=300)
        plt.close()
        
        print(f"Circular network visualization saved to {output_file}")
        
    except Exception as e:
        print(f"Error creating circular network visualization: {e}")

def create_path_length_histogram(conn, output_dir, tables):
    """Create a histogram of path lengths"""
    # Get the appropriate schema
    paths_schema = get_table_schema(conn, tables, 'WIKI_PATHS')
    
    if not paths_schema:
        print("Could not find WIKI_PATHS table in any schema")
        return
        
    query = f"""
    SELECT steps as "path_length"
    FROM {paths_schema}.WIKI_PATHS
    """
    
    try:
        # Execute query and get data
        df = pd.read_sql(query, conn)
        
        if len(df) == 0:
            print("No data available for path length histogram")
            return
            
        # Convert column names to lowercase for consistency
        df.columns = df.columns.str.lower()
        
        # Create visualization
        plt.figure(figsize=(10, 6))
        sns.histplot(data=df, x='path_length', bins=10, kde=True)
        
        # Format chart
        plt.title('Distribution of Path Lengths', fontsize=16)
        plt.xlabel('Path Length (steps)', fontsize=12)
        plt.ylabel('Frequency', fontsize=12)
        plt.grid(axis='y', alpha=0.3)
        plt.tight_layout()
        
        # Save the figure
        output_file = os.path.join(output_dir, 'path_length_histogram.png')
        plt.savefig(output_file, dpi=300)
        plt.close()
        
        print(f"Path length histogram saved to {output_file}")
        
    except Exception as e:
        print(f"Error creating path length histogram: {e}")

def check_tables_exist(conn):
    """Check which tables exist in the database"""
    cursor = conn.cursor()
    tables = {}
    
    try:
        # Check system schema tables
        cursor.execute("""
        SELECT table_name FROM all_tables 
        WHERE owner = 'SYSTEM' AND table_name IN ('WIKI_PATHS', 'WIKI_PATH_NODES')
        """)
        system_tables = [row[0] for row in cursor.fetchall()]
        tables['system'] = system_tables
        
        # Check wiki_user schema tables
        cursor.execute("""
        SELECT table_name FROM all_tables 
        WHERE owner = 'WIKI_USER' AND table_name IN ('WIKI_PATHS', 'WIKI_PATH_NODES')
        """)
        wiki_user_tables = [row[0] for row in cursor.fetchall()]
        tables['wiki_user'] = wiki_user_tables
        
    except Exception as e:
        print(f"Error checking tables: {e}")
        
    return tables

def main():
    parser = argparse.ArgumentParser(description="Visualize Wikipedia Path Data")
    parser.add_argument("--host", type=str, default="localhost", help="Database host")
    parser.add_argument("--port", type=int, default=1521, help="Database port")
    parser.add_argument("--service", type=str, default="XEPDB1", help="Database service name")
    parser.add_argument("--user", type=str, default="system", help="Database username")
    parser.add_argument("--password", type=str, default="Oracle21c", help="Database password")
    parser.add_argument("--output-dir", type=str, default="visualizations", help="Output directory for visualizations")
    
    args = parser.parse_args()
    
    # Create output directory if it doesn't exist
    if not os.path.exists(args.output_dir):
        os.makedirs(args.output_dir)
        
    # Connect to the database
    conn = connect_to_database(args)
    if not conn:
        return
    
    try:
        # Check which tables exist
        tables = check_tables_exist(conn)
        print(f"Found tables: {tables}")
        
        # Only proceed if we have tables to visualize
        if (tables.get('system') or tables.get('wiki_user')):
            # Create visualizations
            create_bar_chart(conn, args.output_dir, tables)
            create_network_graph(conn, args.output_dir, tables)
            create_circular_network(conn, args.output_dir, tables)
            create_path_length_histogram(conn, args.output_dir, tables)
            
            print(f"\nAll visualizations saved to the '{args.output_dir}' directory.")
        else:
            print("No Wikipedia data tables found in the database. Please make sure the tables are created.")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    main() 