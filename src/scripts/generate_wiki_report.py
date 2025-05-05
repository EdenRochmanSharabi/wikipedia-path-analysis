#!/usr/bin/env python3
import pandas as pd
import oracledb
import argparse
import os
import datetime
import networkx as nx
from jinja2 import Template
import json
import math

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

def get_table_schema(conn, table_name):
    """Get the appropriate schema for a table"""
    cursor = conn.cursor()
    try:
        # Check both schemas and use the one with more data
        schemas = ['WIKI_USER', 'SYSTEM']
        max_count = 0
        best_schema = None
        
        for schema in schemas:
            # Check if table exists in this schema
            cursor.execute(f"""
            SELECT table_name FROM all_tables 
            WHERE owner = '{schema}' AND table_name = '{table_name}'
            """)
            
            if cursor.fetchone():
                # Count rows in this schema's table
                cursor.execute(f"SELECT COUNT(*) FROM {schema}.{table_name}")
                count = cursor.fetchone()[0]
                
                print(f"Found {count} rows in {schema}.{table_name}")
                
                if count > max_count:
                    max_count = count
                    best_schema = schema
        
        return best_schema
            
    except Exception as e:
        print(f"Error checking table schema: {e}")
    
    return None

def get_summary_stats(conn):
    """Get summary statistics about the database"""
    stats = {}
    
    try:
        # Get path stats
        paths_schema = get_table_schema(conn, 'WIKI_PATHS')
        if paths_schema:
            cursor = conn.cursor()
            
            # Total paths
            cursor.execute(f"SELECT COUNT(*) FROM {paths_schema}.WIKI_PATHS")
            stats['total_paths'] = cursor.fetchone()[0]
            
            # Min, max, avg path length
            cursor.execute(f"""
            SELECT MIN(steps), MAX(steps), AVG(steps)
            FROM {paths_schema}.WIKI_PATHS
            """)
            min_steps, max_steps, avg_steps = cursor.fetchone()
            stats['min_path_length'] = min_steps
            stats['max_path_length'] = max_steps
            stats['avg_path_length'] = round(avg_steps, 2) if avg_steps else 0
            
            # Number of successful paths
            cursor.execute(f"""
            SELECT COUNT(*) 
            FROM {paths_schema}.WIKI_PATHS 
            WHERE succeeded = 1
            """)
            result = cursor.fetchone()
            stats['successful_paths'] = result[0] if result else 0
            
            # Get completion rate
            if stats['total_paths'] > 0:
                stats['completion_rate'] = round((stats['successful_paths'] / stats['total_paths']) * 100, 2)
            else:
                stats['completion_rate'] = 0
        
        # Get article stats
        nodes_schema = get_table_schema(conn, 'WIKI_PATH_NODES')
        if nodes_schema:
            cursor = conn.cursor()
            
            # Total unique articles
            cursor.execute(f"""
            SELECT COUNT(DISTINCT article_title) 
            FROM {nodes_schema}.WIKI_PATH_NODES
            """)
            stats['unique_articles'] = cursor.fetchone()[0]
            
            # Most common start articles
            cursor.execute(f"""
            SELECT p.start_article, COUNT(*) as count
            FROM {paths_schema}.WIKI_PATHS p
            GROUP BY p.start_article
            ORDER BY count DESC
            FETCH FIRST 5 ROWS ONLY
            """)
            stats['common_start_articles'] = [dict(zip(['article', 'count'], row)) for row in cursor.fetchall()]
            
            # Most common end articles
            cursor.execute(f"""
            SELECT p.end_article, COUNT(*) as count
            FROM {paths_schema}.WIKI_PATHS p
            GROUP BY p.end_article
            ORDER BY count DESC
            FETCH FIRST 5 ROWS ONLY
            """)
            stats['common_end_articles'] = [dict(zip(['article', 'count'], row)) for row in cursor.fetchall()]
            
            # Most common articles in any position
            cursor.execute(f"""
            SELECT article_title, COUNT(*) as count
            FROM {nodes_schema}.WIKI_PATH_NODES
            GROUP BY article_title
            ORDER BY count DESC
            FETCH FIRST 10 ROWS ONLY
            """)
            stats['common_articles'] = [dict(zip(['article', 'count'], row)) for row in cursor.fetchall()]
            
            # Most common article pairs (transitions)
            cursor.execute(f"""
            SELECT 
                src.article_title as source, 
                dst.article_title as target, 
                COUNT(*) as count
            FROM 
                {nodes_schema}.WIKI_PATH_NODES src,
                {nodes_schema}.WIKI_PATH_NODES dst
            WHERE 
                src.path_id = dst.path_id
                AND dst.step_number = src.step_number + 1
            GROUP BY
                src.article_title, dst.article_title
            ORDER BY 
                count DESC
            FETCH FIRST 5 ROWS ONLY
            """)
            stats['common_transitions'] = [dict(zip(['source', 'target', 'count'], row)) for row in cursor.fetchall()]
            
    except Exception as e:
        print(f"Error getting summary stats: {e}")
    
    return stats

def generate_graph_stats(conn):
    """Generate network graph statistics"""
    graph_stats = {}
    
    try:
        # Get appropriate schema
        nodes_schema = get_table_schema(conn, 'WIKI_PATH_NODES')
        if not nodes_schema:
            return graph_stats
            
        # Get all transitions to build the graph
        query = f"""
        SELECT 
            src.article_title as source,
            dst.article_title as target,
            COUNT(*) as weight
        FROM 
            {nodes_schema}.WIKI_PATH_NODES src,
            {nodes_schema}.WIKI_PATH_NODES dst
        WHERE 
            src.path_id = dst.path_id
            AND dst.step_number = src.step_number + 1
        GROUP BY
            src.article_title, dst.article_title
        """
        
        df = pd.read_sql(query, conn)
        if len(df) == 0:
            return graph_stats
            
        # Create graph
        G = nx.from_pandas_edgelist(df, 'SOURCE', 'TARGET', edge_attr='WEIGHT')
        
        # Get basic statistics
        graph_stats['node_count'] = G.number_of_nodes()
        graph_stats['edge_count'] = G.number_of_edges()
        graph_stats['density'] = nx.density(G)
        
        # Get degree statistics
        degrees = [d for n, d in G.degree()]
        graph_stats['avg_degree'] = sum(degrees) / len(degrees) if degrees else 0
        graph_stats['max_degree'] = max(degrees) if degrees else 0
        
        # Get centrality metrics
        # Degree centrality
        dc = nx.degree_centrality(G)
        most_central_dc = sorted(dc.items(), key=lambda x: x[1], reverse=True)[:5]
        graph_stats['degree_central_nodes'] = [{'article': node, 'centrality': round(cent, 4)} 
                                              for node, cent in most_central_dc]
        
        # Try to get betweenness centrality for key nodes
        try:
            # Compute betweenness centrality (can be slow for large graphs)
            bc = nx.betweenness_centrality(G, k=min(500, G.number_of_nodes()))
            most_central_bc = sorted(bc.items(), key=lambda x: x[1], reverse=True)[:5]
            graph_stats['betweenness_central_nodes'] = [{'article': node, 'centrality': round(cent, 4)} 
                                                      for node, cent in most_central_bc]
        except Exception as e:
            print(f"Could not compute betweenness centrality: {e}")
        
        # Top connectors (nodes that link many paths)
        try:
            # Get the number of distinct paths each article appears in
            query = f"""
            SELECT article_title, COUNT(DISTINCT path_id) as path_count
            FROM {nodes_schema}.WIKI_PATH_NODES
            GROUP BY article_title
            ORDER BY path_count DESC
            FETCH FIRST 5 ROWS ONLY
            """
            df_connectors = pd.read_sql(query, conn)
            graph_stats['top_connectors'] = [{'article': row['ARTICLE_TITLE'], 'path_count': int(row['PATH_COUNT'])} 
                                           for _, row in df_connectors.iterrows()]
        except Exception as e:
            print(f"Could not compute top connectors: {e}")
        
    except Exception as e:
        print(f"Error generating graph stats: {e}")
    
    return graph_stats

def get_sample_paths(conn, limit=5):
    """Get sample paths for display"""
    samples = []
    
    try:
        # Get appropriate schemas
        paths_schema = get_table_schema(conn, 'WIKI_PATHS')
        nodes_schema = get_table_schema(conn, 'WIKI_PATH_NODES')
        
        if not paths_schema or not nodes_schema:
            return samples
        
        # Get some sample path IDs
        cursor = conn.cursor()
        cursor.execute(f"""
        SELECT path_id, start_article, end_article, steps
        FROM {paths_schema}.WIKI_PATHS
        ORDER BY creation_date DESC
        FETCH FIRST {limit} ROWS ONLY
        """)
        
        paths = cursor.fetchall()
        
        # For each path, get the full node list
        for path_id, start, end, steps in paths:
            cursor.execute(f"""
            SELECT article_title, step_number
            FROM {nodes_schema}.WIKI_PATH_NODES
            WHERE path_id = {path_id}
            ORDER BY step_number
            """)
            
            nodes = [row[0] for row in cursor.fetchall()]
            
            samples.append({
                'path_id': path_id,
                'start': start,
                'end': end,
                'steps': steps,
                'nodes': nodes
            })
    
    except Exception as e:
        print(f"Error getting sample paths: {e}")
    
    return samples

def generate_html_report(stats, graph_stats, samples, output_dir):
    """Generate HTML report with visualizations and statistics"""
    # Load template
    template_str = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Wikipedia Path Analysis Report</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                line-height: 1.6;
                color: #333;
                max-width: 1200px;
                margin: 0 auto;
                padding: 20px;
            }
            h1, h2, h3 {
                color: #2c3e50;
            }
            .report-header {
                text-align: center;
                margin-bottom: 30px;
                padding-bottom: 20px;
                border-bottom: 1px solid #eee;
            }
            .report-section {
                margin-bottom: 40px;
            }
            .visualization {
                text-align: center;
                margin: 20px 0;
            }
            .visualization img {
                max-width: 100%;
                box-shadow: 0 2px 15px rgba(0,0,0,0.1);
                border-radius: 5px;
            }
            .stats-grid {
                display: grid;
                grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
                grid-gap: 20px;
                margin: 20px 0;
            }
            .stats-card {
                background: #f8f9fa;
                border-radius: 5px;
                padding: 15px;
                box-shadow: 0 2px 5px rgba(0,0,0,0.05);
            }
            .stats-value {
                font-size: 24px;
                font-weight: bold;
                color: #3498db;
            }
            table {
                width: 100%;
                border-collapse: collapse;
                margin: 20px 0;
            }
            th, td {
                padding: 12px 15px;
                text-align: left;
                border-bottom: 1px solid #ddd;
            }
            th {
                background-color: #f8f9fa;
            }
            .path-example {
                background: #f8f9fa;
                border-radius: 5px;
                padding: 15px;
                margin-bottom: 20px;
            }
            .path-nodes {
                display: flex;
                flex-wrap: wrap;
                gap: 10px;
                align-items: center;
            }
            .path-node {
                background: #e1f5fe;
                padding: 5px 10px;
                border-radius: 15px;
            }
            .path-arrow {
                color: #7f8c8d;
            }
            footer {
                text-align: center;
                margin-top: 50px;
                padding-top: 20px;
                border-top: 1px solid #eee;
                color: #7f8c8d;
            }
        </style>
    </head>
    <body>
        <div class="report-header">
            <h1>Wikipedia Path Analysis Report</h1>
            <p>Analysis of paths between Wikipedia articles using the "first link" strategy</p>
            <p>Generated on {{ date }}</p>
        </div>
        
        <div class="report-section">
            <h2>Key Statistics</h2>
            <div class="stats-grid">
                <div class="stats-card">
                    <h3>Total Paths</h3>
                    <div class="stats-value">{{ stats.total_paths }}</div>
                </div>
                <div class="stats-card">
                    <h3>Unique Articles</h3>
                    <div class="stats-value">{{ stats.unique_articles }}</div>
                </div>
                <div class="stats-card">
                    <h3>Successful Paths</h3>
                    <div class="stats-value">{{ stats.successful_paths }} ({{ stats.completion_rate }}%)</div>
                </div>
                <div class="stats-card">
                    <h3>Path Length</h3>
                    <div class="stats-value">{{ stats.avg_path_length }}</div>
                    <div>Range: {{ stats.min_path_length }} - {{ stats.max_path_length }} steps</div>
                </div>
                <div class="stats-card">
                    <h3>Network Size</h3>
                    <div class="stats-value">{{ graph_stats.node_count }} nodes, {{ graph_stats.edge_count }} edges</div>
                </div>
                <div class="stats-card">
                    <h3>Network Density</h3>
                    <div class="stats-value">{{ (graph_stats.density * 100) | round(2) }}%</div>
                </div>
            </div>
        </div>
        
        <div class="report-section">
            <h2>Visualizations</h2>
            
            <h3>Distribution of Path Lengths</h3>
            <div class="visualization">
                <img src="visualizations/path_length_histogram.png" alt="Path Length Histogram">
                <p>Distribution of path lengths (steps) across all paths</p>
            </div>
            
            <h3>Most Common Wikipedia Articles</h3>
            <div class="visualization">
                <img src="visualizations/wiki_article_frequency.png" alt="Article Frequency">
                <p>Articles that appear most frequently across all paths</p>
            </div>
            
            <h3>Network Graph (Spring Layout)</h3>
            <div class="visualization">
                <img src="visualizations/wiki_network_graph.png" alt="Network Graph">
                <p>Network visualization of article connections with spring layout</p>
            </div>
            
            <h3>Network Graph (Circular Layout)</h3>
            <div class="visualization">
                <img src="visualizations/wiki_circular_network.png" alt="Circular Network">
                <p>Circular network layout with betweenness centrality highlighted</p>
            </div>
        </div>
        
        <div class="report-section">
            <h2>Network Analysis</h2>
            
            <h3>Central Articles (Degree Centrality)</h3>
            <p>Articles that connect to many other articles:</p>
            <table>
                <tr>
                    <th>Article</th>
                    <th>Centrality Score</th>
                </tr>
                {% for node in graph_stats.degree_central_nodes %}
                <tr>
                    <td>{{ node.article }}</td>
                    <td>{{ node.centrality }}</td>
                </tr>
                {% endfor %}
            </table>
            
            {% if graph_stats.betweenness_central_nodes %}
            <h3>Bridge Articles (Betweenness Centrality)</h3>
            <p>Articles that serve as bridges between different parts of the network:</p>
            <table>
                <tr>
                    <th>Article</th>
                    <th>Centrality Score</th>
                </tr>
                {% for node in graph_stats.betweenness_central_nodes %}
                <tr>
                    <td>{{ node.article }}</td>
                    <td>{{ node.centrality }}</td>
                </tr>
                {% endfor %}
            </table>
            {% endif %}
            
            {% if graph_stats.top_connectors %}
            <h3>Top Connector Articles</h3>
            <p>Articles that appear in the most distinct paths:</p>
            <table>
                <tr>
                    <th>Article</th>
                    <th>Number of Paths</th>
                </tr>
                {% for connector in graph_stats.top_connectors %}
                <tr>
                    <td>{{ connector.article }}</td>
                    <td>{{ connector.path_count }}</td>
                </tr>
                {% endfor %}
            </table>
            {% endif %}
        </div>
        
        <div class="report-section">
            <h2>Common Articles and Transitions</h2>
            
            <h3>Most Common Starting Articles</h3>
            <table>
                <tr>
                    <th>Article</th>
                    <th>Count</th>
                </tr>
                {% for item in stats.common_start_articles %}
                <tr>
                    <td>{{ item.article }}</td>
                    <td>{{ item.count }}</td>
                </tr>
                {% endfor %}
            </table>
            
            <h3>Most Common Ending Articles</h3>
            <table>
                <tr>
                    <th>Article</th>
                    <th>Count</th>
                </tr>
                {% for item in stats.common_end_articles %}
                <tr>
                    <td>{{ item.article }}</td>
                    <td>{{ item.count }}</td>
                </tr>
                {% endfor %}
            </table>
            
            <h3>Most Common Article Transitions</h3>
            <p>Most frequent steps between articles:</p>
            <table>
                <tr>
                    <th>Source</th>
                    <th>Target</th>
                    <th>Count</th>
                </tr>
                {% for item in stats.common_transitions %}
                <tr>
                    <td>{{ item.source }}</td>
                    <td>{{ item.target }}</td>
                    <td>{{ item.count }}</td>
                </tr>
                {% endfor %}
            </table>
        </div>
        
        <div class="report-section">
            <h2>Sample Paths</h2>
            <p>Recent paths collected in the database:</p>
            
            {% for path in samples %}
            <div class="path-example">
                <h3>Path ID: {{ path.path_id }}</h3>
                <p><strong>Start:</strong> {{ path.start }}</p>
                <p><strong>End:</strong> {{ path.end }}</p>
                <p><strong>Steps:</strong> {{ path.steps }}</p>
                
                <div class="path-nodes">
                    {% for node in path.nodes %}
                    <div class="path-node">{{ node }}</div>
                    {% if not loop.last %}
                    <div class="path-arrow">→</div>
                    {% endif %}
                    {% endfor %}
                </div>
            </div>
            {% endfor %}
        </div>
        
        <footer>
            <p>Wikipedia Path Analysis Project - Generated using Python data visualization tools</p>
        </footer>
    </body>
    </html>
    """
    
    template = Template(template_str)
    
    # Format data for template
    formatted_date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Render template
    html_content = template.render(
        stats=stats,
        graph_stats=graph_stats,
        samples=samples,
        date=formatted_date
    )
    
    # Save to file
    output_file = os.path.join(output_dir, "wiki_path_report.html")
    with open(output_file, "w") as f:
        f.write(html_content)
    
    print(f"Report generated: {output_file}")

def main():
    parser = argparse.ArgumentParser(description="Generate Wikipedia Path Analysis Report")
    parser.add_argument("--host", type=str, default="localhost", help="Database host")
    parser.add_argument("--port", type=int, default=1521, help="Database port")
    parser.add_argument("--service", type=str, default="XEPDB1", help="Database service name")
    parser.add_argument("--user", type=str, default="system", help="Database username")
    parser.add_argument("--password", type=str, default="Oracle21c", help="Database password")
    parser.add_argument("--output-dir", type=str, default="reports", help="Output directory for reports")
    
    args = parser.parse_args()
    
    # Create output directory if it doesn't exist
    if not os.path.exists(args.output_dir):
        os.makedirs(args.output_dir)
        
    # Create visualizations directory link if it doesn't exist in the reports dir
    vis_source = os.path.join(os.getcwd(), "visualizations")
    vis_link = os.path.join(args.output_dir, "visualizations")
    
    if not os.path.exists(vis_link) and os.path.exists(vis_source):
        # Try to create a symlink first
        try:
            os.symlink(vis_source, vis_link)
        except:
            # If symlink fails, make a directory and copy files
            os.makedirs(vis_link, exist_ok=True)
            for file in os.listdir(vis_source):
                src_file = os.path.join(vis_source, file)
                dst_file = os.path.join(vis_link, file)
                if os.path.isfile(src_file) and not os.path.exists(dst_file):
                    with open(src_file, 'rb') as f_in, open(dst_file, 'wb') as f_out:
                        f_out.write(f_in.read())
    
    # Connect to the database
    conn = connect_to_database(args)
    if not conn:
        return
    
    try:
        # Get statistics
        print("Collecting database statistics...")
        stats = get_summary_stats(conn)
        
        # Get graph statistics
        print("Analyzing network properties...")
        graph_stats = generate_graph_stats(conn)
        
        # Get sample paths
        print("Retrieving sample paths...")
        samples = get_sample_paths(conn)
        
        # Generate HTML report
        print("Generating HTML report...")
        generate_html_report(stats, graph_stats, samples, args.output_dir)
        
        # Success message
        print(f"Report generation complete! Open {args.output_dir}/wiki_path_report.html to view it.")
        
    except Exception as e:
        print(f"Error generating report: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    main() 