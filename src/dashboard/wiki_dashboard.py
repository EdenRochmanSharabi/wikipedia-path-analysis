#!/usr/bin/env python3
import os
import time
import argparse
import threading
import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import networkx as nx
import oracledb
import datetime
try:
    import dash_daq as daq  # Import the daq components which includes Switch
except ImportError:
    print("Warning: dash_daq not available, will use checkbox instead")
    daq = None

# Global variables to store data for efficiency
last_update_time = None
db_size_history = []
node_count_history = []
edge_count_history = []
paths_count_history = []
common_articles = None
common_endpoints = None
graph = None

class DatabaseConnection:
    """Class to handle database connections and queries"""
    
    def __init__(self, host, port, service, user, password, sysdba=False):
        self.host = host
        self.port = port
        self.service = service
        self.user = user
        self.password = password
        self.sysdba = sysdba
        self.mode=None if sysdba else oracledb.DEFAULT_AUTH
        
    def connect(self):
        """Connect to the Oracle database"""
        try:
            connection = oracledb.connect(
                user=self.user,
                password=self.password,
                dsn=f"{self.host}:{self.port}/{self.service}",
                mode=self.mode
            )
            return connection
        except oracledb.Error as e:
            print(f"Error connecting to Oracle Database: {e}")
            return None
            
    def execute_query(self, query):
        """Execute a query and return results as a DataFrame"""
        connection = self.connect()
        if not connection:
            return pd.DataFrame()
            
        try:
            cursor = connection.cursor()
            cursor.execute(query)
            columns = [col[0] for col in cursor.description]
            data = cursor.fetchall()
            df = pd.DataFrame(data, columns=columns)
            cursor.close()
            connection.close()
            return df
        except Exception as e:
            print(f"Error executing query: {e}")
            if connection:
                connection.close()
            return pd.DataFrame()
    
    def get_database_size(self):
        """Get the current database size in GB"""
        query = """
        SELECT 
            SUM(bytes) / (1024 * 1024 * 1024) as size_gb
        FROM 
            dba_data_files
        """
        df = self.execute_query(query)
        if not df.empty:
            return round(df.iloc[0]['SIZE_GB'], 2)
        return 0
        
    def get_article_count(self):
        """Get the number of unique articles in the database"""
        query = """
        SELECT COUNT(DISTINCT article_title) as article_count
        FROM WIKI_PATH_NODES
        """
        df = self.execute_query(query)
        if not df.empty:
            return int(df.iloc[0]['ARTICLE_COUNT'])
        return 0
        
    def get_path_count(self):
        """Get the number of paths in the database"""
        query = """
        SELECT COUNT(*) as path_count
        FROM WIKI_PATHS
        """
        df = self.execute_query(query)
        if not df.empty:
            return int(df.iloc[0]['PATH_COUNT'])
        return 0
        
    def get_common_articles(self, limit=20):
        """Get the most common articles in paths"""
        query = f"""
        SELECT 
            article_title, 
            COUNT(*) as frequency
        FROM WIKI_PATH_NODES
        GROUP BY article_title
        ORDER BY frequency DESC
        FETCH FIRST {limit} ROWS ONLY
        """
        return self.execute_query(query)
        
    def get_common_endpoints(self, limit=15):
        """Get the most common endpoints in paths"""
        query = f"""
        SELECT 
            end_article as endpoint, 
            COUNT(*) as frequency
        FROM WIKI_PATHS
        GROUP BY end_article
        ORDER BY frequency DESC
        FETCH FIRST {limit} ROWS ONLY
        """
        return self.execute_query(query)
        
    def get_path_length_distribution(self):
        """Get distribution of path lengths"""
        query = """
        SELECT 
            steps as path_length,
            COUNT(*) as frequency
        FROM WIKI_PATHS 
        GROUP BY steps
        ORDER BY steps
        """
        return self.execute_query(query)
        
    def get_graph_data(self, max_edges=100):
        """Get data for building a graph visualization"""
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
        FETCH FIRST {max_edges} ROWS ONLY
        """
        return self.execute_query(query)
        
    def get_recent_paths(self, limit=5):
        """Get the most recently added paths"""
        query = f"""
        SELECT 
            path_id,
            start_article,
            end_article,
            steps,
            creation_date
        FROM 
            WIKI_PATHS
        ORDER BY 
            creation_date DESC
        FETCH FIRST {limit} ROWS ONLY
        """
        return self.execute_query(query)


def create_app(db_connection):
    """Create the Dash application"""
    app = dash.Dash(__name__, 
                   meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1"}])
    
    # Define the layout
    app.layout = html.Div([
        html.H1("Wikipedia Graph Collection Dashboard", className="header-title"),
        
        html.Div([
            html.Div([
                html.H4("Current Status"),
                html.Div(id="current-status"),
                dcc.Interval(id="status-update", interval=5000, n_intervals=0)
            ], className="status-card"),
            
            html.Div([
                html.H4("Collection Growth"),
                dcc.Graph(id="collection-growth"),
                dcc.Interval(id="growth-update", interval=10000, n_intervals=0)
            ], className="graph-card")
        ], className="row"),
        
        html.Div([
            html.Div([
                html.H4("Recent Paths"),
                html.Div(id="recent-paths"),
                dcc.Interval(id="recent-paths-update", interval=15000, n_intervals=0)
            ], className="table-card"),
        ], className="row"),
        
        html.Div([
            html.Div([
                html.H4("Path Length Distribution"),
                dcc.Graph(id="path-length-distribution"),
                dcc.Interval(id="path-length-update", interval=30000, n_intervals=0)
            ], className="graph-card"),
            
            html.Div([
                html.H4("Most Common Articles"),
                dcc.Graph(id="common-articles"),
                dcc.Interval(id="common-articles-update", interval=30000, n_intervals=0)
            ], className="graph-card")
        ], className="row"),
        
        html.Div([
            html.H4("Wikipedia Graph Visualization"),
            html.Div([
                html.Span("Show limited graph (faster)", style={"margin-right": "10px"}),
                html.Div([
                    html.Input(
                        id="show-all-nodes",
                        type="checkbox",
                        value=False
                    ) if daq is None else daq.BooleanSwitch(
                        id="show-all-nodes",
                        on=False,
                        label="",
                        labelPosition="top"
                    )
                ], style={"display": "inline-block"}),
                html.Span("Show all nodes (may be slow)", style={"margin-left": "10px"}),
            ], style={"display": "flex", "align-items": "center", "justify-content": "center", "margin-bottom": "15px"}),
            dcc.Graph(id="graph-visualization", style={"height": "800px"}),
            dcc.Interval(id="graph-update", interval=60000, n_intervals=0)
        ], className="row"),
        
        # Hidden div to store timestamps
        html.Div(id="timestamps", style={"display": "none"})
    ])
    
    # Callback for updating current status
    @app.callback(
        Output("current-status", "children"),
        Input("status-update", "n_intervals")
    )
    def update_status(n):
        global last_update_time
        
        # Get current data
        db_size = db_connection.get_database_size()
        article_count = db_connection.get_article_count()
        path_count = db_connection.get_path_count()
        
        # Update history with timestamp
        timestamp = datetime.datetime.now()
        if last_update_time is None or (timestamp - last_update_time).total_seconds() >= 10:
            db_size_history.append((timestamp, db_size))
            node_count_history.append((timestamp, article_count))
            paths_count_history.append((timestamp, path_count))
            last_update_time = timestamp
            
            # Limit history length
            if len(db_size_history) > 100:
                db_size_history.pop(0)
                node_count_history.pop(0)
                paths_count_history.pop(0)
        
        # Format the status display
        return html.Div([
            html.Div([
                html.H2(f"{db_size} GB", className="metric-value"),
                html.P("Database Size", className="metric-name")
            ], className="metric"),
            
            html.Div([
                html.H2(f"{article_count:,}", className="metric-value"),
                html.P("Unique Articles", className="metric-name")
            ], className="metric"),
            
            html.Div([
                html.H2(f"{path_count:,}", className="metric-value"),
                html.P("Paths Collected", className="metric-name")
            ], className="metric"),
            
            html.Div([
                html.H2(timestamp.strftime("%H:%M:%S"), className="metric-value"),
                html.P("Last Update", className="metric-name")
            ], className="metric")
        ], className="metrics-container")
    
    # Callback for updating collection growth chart
    @app.callback(
        Output("collection-growth", "figure"),
        Input("growth-update", "n_intervals")
    )
    def update_growth_chart(n):
        # Create dataframes from history
        if db_size_history:
            db_size_df = pd.DataFrame(db_size_history, columns=["timestamp", "size_gb"])
            article_df = pd.DataFrame(node_count_history, columns=["timestamp", "count"])
            path_df = pd.DataFrame(paths_count_history, columns=["timestamp", "count"])
            
            fig = go.Figure()
            
            # Add database size trace
            fig.add_trace(go.Scatter(
                x=db_size_df["timestamp"], 
                y=db_size_df["size_gb"],
                mode="lines+markers",
                name="Database Size (GB)",
                yaxis="y"
            ))
            
            # Add article count trace
            fig.add_trace(go.Scatter(
                x=article_df["timestamp"], 
                y=article_df["count"],
                mode="lines+markers",
                name="Articles",
                yaxis="y2"
            ))
            
            # Add path count trace
            fig.add_trace(go.Scatter(
                x=path_df["timestamp"], 
                y=path_df["count"],
                mode="lines+markers",
                name="Paths",
                yaxis="y2"
            ))
            
            # Set up dual y-axes
            fig.update_layout(
                title="Collection Growth Over Time",
                xaxis=dict(title="Time"),
                yaxis=dict(
                    title="Database Size (GB)",
                    side="left",
                    showgrid=True
                ),
                yaxis2=dict(
                    title="Count",
                    side="right",
                    overlaying="y",
                    showgrid=False
                ),
                legend=dict(orientation="h", y=1.1),
                margin=dict(l=50, r=50, t=80, b=50)
            )
            
            return fig
        else:
            # Return empty figure if no data
            return go.Figure()
    
    # Callback for updating recent paths table
    @app.callback(
        Output("recent-paths", "children"),
        Input("recent-paths-update", "n_intervals")
    )
    def update_recent_paths(n):
        recent_paths_df = db_connection.get_recent_paths(limit=10)
        
        if recent_paths_df.empty:
            return html.P("No paths collected yet.")
        
        # Format the table
        return html.Table([
            html.Thead(
                html.Tr([
                    html.Th("Path ID"),
                    html.Th("Start Article"),
                    html.Th("End Article"),
                    html.Th("Steps"),
                    html.Th("Time Collected")
                ])
            ),
            html.Tbody([
                html.Tr([
                    html.Td(row["PATH_ID"]),
                    html.Td(row["START_ARTICLE"]),
                    html.Td(row["END_ARTICLE"]),
                    html.Td(row["STEPS"]),
                    html.Td(row["CREATION_DATE"].strftime("%H:%M:%S"))
                ]) for _, row in recent_paths_df.iterrows()
            ])
        ], className="data-table")
    
    # Callback for updating path length distribution
    @app.callback(
        Output("path-length-distribution", "figure"),
        Input("path-length-update", "n_intervals")
    )
    def update_path_length_distribution(n):
        path_length_df = db_connection.get_path_length_distribution()
        
        if path_length_df.empty:
            return go.Figure()
        
        fig = px.bar(
            path_length_df, 
            x="PATH_LENGTH", 
            y="FREQUENCY",
            labels={"PATH_LENGTH": "Path Length (Steps)", "FREQUENCY": "Number of Paths"},
            title="Distribution of Wikipedia Path Lengths"
        )
        
        fig.update_layout(
            xaxis_title="Path Length (Steps)",
            yaxis_title="Number of Paths",
            margin=dict(l=50, r=50, t=80, b=50)
        )
        
        return fig
    
    # Callback for updating common articles chart
    @app.callback(
        Output("common-articles", "figure"),
        Input("common-articles-update", "n_intervals")
    )
    def update_common_articles(n):
        global common_articles
        
        # Only fetch new data every few updates to reduce load
        if n % 3 == 0 or common_articles is None:
            common_articles = db_connection.get_common_articles(limit=15)
        
        if common_articles.empty:
            return go.Figure()
        
        fig = px.bar(
            common_articles, 
            y="ARTICLE_TITLE", 
            x="FREQUENCY",
            orientation="h",
            labels={"ARTICLE_TITLE": "Article", "FREQUENCY": "Frequency"},
            title="Most Common Articles in Paths"
        )
        
        fig.update_layout(
            yaxis=dict(autorange="reversed"),
            margin=dict(l=50, r=50, t=80, b=50)
        )
        
        return fig
    
    # Callback for updating graph visualization
    @app.callback(
        Output("graph-visualization", "figure"),
        [Input("graph-update", "n_intervals"),
         Input("show-all-nodes", "value" if daq is None else "on")]
    )
    def update_graph_visualization(n, show_all_nodes):
        global graph
        
        # Boolean switch sends True/False, checkbox might send "True"/"False" or True/False
        if isinstance(show_all_nodes, str):
            show_all_nodes = show_all_nodes.lower() == "true"
        
        # Only update the graph periodically to reduce load
        if n % 6 == 0 or graph is None:
            # If showing all nodes, get more edges
            max_edges = 5000 if show_all_nodes else 100
            graph_data = db_connection.get_graph_data(max_edges=max_edges)
            
            if graph_data.empty:
                return go.Figure()
            
            # Create a directed graph
            G = nx.DiGraph()
            
            # Add edges with weights
            for _, row in graph_data.iterrows():
                G.add_edge(row["SOURCE"], row["TARGET"], weight=row["WEIGHT"])
            
            # Limit to most significant nodes if not showing all and too large
            if not show_all_nodes and len(G.nodes) > 50:
                # Keep only nodes with degree > 1
                to_remove = [node for node, degree in dict(G.degree()).items() if degree <= 1]
                G.remove_nodes_from(to_remove)
            
            # Calculate node positions using a spring layout
            # Use fewer iterations for large graphs to speed up rendering
            iterations = 25 if len(G.nodes) > 200 else 50
            pos = nx.spring_layout(G, iterations=iterations)
            
            # Calculate node sizes based on centrality
            centrality = nx.degree_centrality(G)
            node_sizes = [centrality[node] * 50 + 10 for node in G.nodes]
            
            # Create edge traces
            edge_x = []
            edge_y = []
            edge_text = []
            
            for edge in G.edges():
                x0, y0 = pos[edge[0]]
                x1, y1 = pos[edge[1]]
                edge_x.extend([x0, x1, None])
                edge_y.extend([y0, y1, None])
                weight = G.edges[edge]["weight"]
                edge_text.append(f"{edge[0]} → {edge[1]} (weight: {weight})")
            
            edge_trace = go.Scatter(
                x=edge_x, y=edge_y,
                line=dict(width=0.5 if show_all_nodes else 0.7, color="#888"),
                hoverinfo="none",
                mode="lines"
            )
            
            # Create node traces
            node_x = []
            node_y = []
            node_text = []
            
            for node in G.nodes():
                x, y = pos[node]
                node_x.append(x)
                node_y.append(y)
                node_text.append(node)
            
            # Use smaller markers when showing all nodes
            marker_size = node_sizes if not show_all_nodes else [min(s, 15) for s in node_sizes]
            
            node_trace = go.Scatter(
                x=node_x, y=node_y,
                mode="markers",
                hoverinfo="text",
                text=node_text,
                marker=dict(
                    showscale=True,
                    colorscale="YlGnBu",
                    size=marker_size,
                    color=list(centrality.values()),
                    colorbar=dict(
                        thickness=15,
                        title="Node Centrality",
                        xanchor="left",
                        titleside="right"
                    ),
                    line=dict(width=2 if not show_all_nodes else 1)
                )
            )
            
            # Add node count to title
            title = f"Wikipedia Article Network ({len(G.nodes)} nodes shown)"
            
            # Create the figure
            fig = go.Figure(data=[edge_trace, node_trace],
                           layout=go.Layout(
                               title=title,
                               titlefont=dict(size=16),
                               showlegend=False,
                               hovermode="closest",
                               margin=dict(b=20, l=5, r=5, t=40),
                               xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                               yaxis=dict(showgrid=False, zeroline=False, showticklabels=False)
                           ))
            
            graph = fig
            return fig
        else:
            # Return cached graph
            return graph if graph is not None else go.Figure()
    
    return app


def get_db_connection_args():
    """Get database connection arguments from command line"""
    parser = argparse.ArgumentParser(description="Wikipedia Graph Dashboard")
    parser.add_argument("--host", default="localhost", help="Database host")
    parser.add_argument("--port", default=1521, type=int, help="Database port")
    parser.add_argument("--service", default="XE", help="Database service name")
    parser.add_argument("--user", default="sys", help="Database username")
    parser.add_argument("--password", required=True, help="Database password")
    parser.add_argument("--sysdba", action="store_true", help="Connect as SYSDBA")
    parser.add_argument("--port-number", type=int, default=8050, help="Port to run the dashboard on")
    
    return parser.parse_args()


def main():
    # Parse arguments
    args = get_db_connection_args()
    
    try:
        print("Creating database connection...")
        # Create database connection
        db_connection = DatabaseConnection(
            host=args.host,
            port=args.port,
            service=args.service,
            user=args.user,
            password=args.password,
            sysdba=args.sysdba
        )
        
        print("Testing database connection...")
        # Test the connection
        test_connection = db_connection.connect()
        if test_connection:
            print("Database connection successful!")
            test_connection.close()
        else:
            print("Warning: Could not connect to database. Dashboard will start but may not show data.")
        
        print("Creating Dash app...")
        # Create and run the app
        app = create_app(db_connection)
        
        print("Setting up app styles...")
        # Add CSS styles
        app.index_string = '''
        <!DOCTYPE html>
        <html>
            <head>
                {%metas%}
                <title>Wikipedia Graph Dashboard</title>
                {%favicon%}
                {%css%}
                <style>
                    body {
                        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                        margin: 0;
                        padding: 20px;
                        background-color: #f5f5f5;
                    }
                    .header-title {
                        color: #333;
                        text-align: center;
                        margin-bottom: 30px;
                        font-size: 2.2em;
                    }
                    .row {
                        display: flex;
                        flex-wrap: wrap;
                        margin: 0 -10px;
                        margin-bottom: 20px;
                    }
                    .status-card, .graph-card, .table-card {
                        background: white;
                        border-radius: 8px;
                        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                        padding: 15px;
                        margin: 10px;
                    }
                    .status-card {
                        flex: 1;
                        min-width: 300px;
                    }
                    .graph-card {
                        flex: 1;
                        min-width: 450px;
                    }
                    .table-card {
                        flex: 1;
                        min-width: 600px;
                    }
                    h4 {
                        color: #444;
                        margin-top: 0;
                        border-bottom: 1px solid #eee;
                        padding-bottom: 10px;
                    }
                    .metrics-container {
                        display: flex;
                        flex-wrap: wrap;
                        justify-content: space-between;
                    }
                    .metric {
                        text-align: center;
                        padding: 10px;
                        border-radius: 5px;
                        background-color: #f9f9f9;
                        width: 22%;
                        margin-bottom: 10px;
                    }
                    .metric-value {
                        font-size: 1.8em;
                        margin: 5px 0;
                        color: #2c6aa1;
                    }
                    .metric-name {
                        margin: 5px 0;
                        color: #666;
                    }
                    .data-table {
                        width: 100%;
                        border-collapse: collapse;
                    }
                    .data-table th, .data-table td {
                        padding: 8px;
                        text-align: left;
                        border-bottom: 1px solid #ddd;
                    }
                    .data-table th {
                        background-color: #f2f2f2;
                        color: #333;
                    }
                    .data-table tr:hover {
                        background-color: #f5f5f5;
                    }
                    @media (max-width: 768px) {
                        .metric {
                            width: 48%;
                        }
                    }
                    @media (max-width: 480px) {
                        .metric {
                            width: 100%;
                        }
                    }
                </style>
            </head>
            <body>
                {%app_entry%}
                <footer>
                    {%config%}
                    {%scripts%}
                    {%renderer%}
                </footer>
            </body>
        </html>
        '''
        
        print(f"Starting Wikipedia Graph Dashboard on http://localhost:{args.port_number}")
        print(f"Press Ctrl+C to stop the server")
        app.run_server(debug=False, port=args.port_number)
    
    except Exception as e:
        import traceback
        print(f"Error starting dashboard: {e}")
        traceback.print_exc()
        print("\nTrying simplified approach...")
        
        try:
            # Create a simple app for debugging
            db_connection = DatabaseConnection(
                host=args.host,
                port=args.port,
                service=args.service,
                user=args.user,
                password=args.password,
                sysdba=args.sysdba
            )
            
            # Create a minimal app
            simple_app = dash.Dash(__name__)
            simple_app.layout = html.Div([
                html.H1("Wikipedia Dashboard (Debug Mode)"),
                html.Div(id="debug-output"),
                dcc.Interval(id="debug-interval", interval=5000, n_intervals=0)
            ])
            
            @simple_app.callback(
                Output("debug-output", "children"),
                Input("debug-interval", "n_intervals")
            )
            def update_debug(n):
                try:
                    db_size = db_connection.get_database_size()
                    article_count = db_connection.get_article_count()
                    path_count = db_connection.get_path_count()
                    
                    return html.Div([
                        html.P(f"Database connection working: True"),
                        html.P(f"Database size: {db_size} GB"),
                        html.P(f"Articles: {article_count}"),
                        html.P(f"Paths: {path_count}")
                    ])
                except Exception as e:
                    return html.Div([
                        html.P(f"Error: {str(e)}"),
                    ])
            
            print("Starting simplified dashboard for debugging...")
            simple_app.run_server(debug=False, port=args.port_number)
            
        except Exception as e:
            print(f"Even simplified dashboard failed: {e}")
            traceback.print_exc()


if __name__ == "__main__":
    main() 