# Wikipedia Path Analysis with Oracle Database

This document provides comprehensive documentation on setting up and using Oracle Database with Docker for Wikipedia path analysis, including installation of dependencies, database configuration, SQL queries, and Python integration.

## Table of Contents
1. [Oracle Database Setup](#oracle-database-setup)
   - [Installing Oracle XE with Docker](#installing-oracle-xe-with-docker)
   - [Oracle APEX Installation](#oracle-apex-installation)
   - [SQLPlus Client Setup](#sqlplus-client-setup)
2. [Database Schema](#database-schema)
   - [Tables Structure](#tables-structure)
   - [Recreating Schema](#recreating-schema)
3. [Data Collection with Python](#data-collection-with-python)
   - [Wikipedia Crawler](#wikipedia-crawler)
   - [Running the Crawler](#running-the-crawler)
4. [Data Analysis](#data-analysis)
   - [SQL Queries](#sql-queries)
   - [Python Visualization](#python-visualization)
5. [Generating Reports](#generating-reports)
   - [HTML Reports](#html-reports)
   - [Network Visualizations](#network-visualizations)
6. [Troubleshooting](#troubleshooting)

## Oracle Database Setup

### Installing Oracle XE with Docker

Oracle Express Edition (XE) provides a free version of Oracle Database suitable for development and small-scale projects. We used Docker to simplify the installation process.

#### Prerequisites
- Docker installed
- At least 4GB RAM allocated to Docker
- At least 15GB free disk space

#### Docker Setup

1. Pull the Oracle XE image from Oracle Container Registry:

```bash
docker run -d \
  --name oracle-wiki-21c \
  -p 1521:1521 -p 5500:5500 -p 8080:8080 \
  -e ORACLE_PWD=Oracle21c \
  container-registry.oracle.com/database/express:latest
```

2. Wait for container initialization (this can take 10-15 minutes):

```bash
docker logs -f oracle-wiki-21c
```

Look for the message "DATABASE IS READY TO USE!" to confirm successful initialization.

3. Verify installation:

```bash
docker exec oracle-wiki-21c sqlplus sys/Oracle21c@XEPDB1 as sysdba -S <<< "SELECT * FROM v\$version;"
```

Output should show Oracle Database version information.

### Oracle APEX Installation

Oracle APEX (Application Express) comes pre-installed with Oracle XE 21c, but requires configuration:

1. Check APEX installation status:

```bash
docker cp check_apex_config.sql oracle-wiki-21c:/tmp/
docker exec oracle-wiki-21c sqlplus sys/Oracle21c@XEPDB1 as sysdba @/tmp/check_apex_config.sql
```

The `check_apex_config.sql` script:

```sql
-- Display current APEX version
SELECT VERSION_NO FROM APEX_RELEASE;

-- Check APEX_ADMIN user existence
SELECT username, account_status FROM dba_users WHERE username = 'APEX_ADMIN';

-- Check APEX_PUBLIC_USER status
SELECT username, account_status FROM dba_users WHERE username = 'APEX_PUBLIC_USER';

-- Check ORDS configuration
SELECT APEX_INSTANCE_ADMIN.GET_PARAMETER('ORDS_PUBLIC_USER_PROXY_ENABLED') FROM dual;

EXIT;
```

2. Setting up APEX admin:

```bash
docker cp setup_apex_admin_direct.sql oracle-wiki-21c:/tmp/
docker exec oracle-wiki-21c sqlplus sys/Oracle21c@XEPDB1 as sysdba @/tmp/setup_apex_admin_direct.sql
```

The `setup_apex_admin_direct.sql` script:

```sql
-- Create APEX admin user
BEGIN
    APEX_UTIL.SET_SECURITY_GROUP_ID(10);
    APEX_UTIL.CREATE_USER(
        p_user_name       => 'ADMIN',
        p_email_address   => 'admin@example.com',
        p_web_password    => 'Admin123',
        p_developer_privs => 'ADMIN'
    );
    COMMIT;
END;
/

-- Verify user creation
SELECT username, account_status FROM dba_users WHERE username = 'APEX_ADMIN';

EXIT;
```

3. Create APEX workspace:

```bash
docker cp create_apex_workspace.sql oracle-wiki-21c:/tmp/
docker exec oracle-wiki-21c sqlplus sys/Oracle21c@XEPDB1 as sysdba @/tmp/create_apex_workspace.sql
```

### SQLPlus Client Setup

Although SQLPlus is available inside the Docker container, we also set up a local client for convenience:

1. Download and install Oracle Instant Client from Oracle's website
2. Add the client to your PATH
3. Configure the TNS file for connection:

```
XEPDB1 =
  (DESCRIPTION =
    (ADDRESS = (PROTOCOL = TCP)(HOST = localhost)(PORT = 1521))
    (CONNECT_DATA =
      (SERVER = DEDICATED)
      (SERVICE_NAME = XEPDB1)
    )
  )
```

4. Test connection:

```bash
sqlplus system/Oracle21c@XEPDB1
```

## Database Schema

### Tables Structure

The Wikipedia path analysis uses two main tables:

1. `WIKI_PATHS` - Stores metadata about paths between articles:

```sql
CREATE TABLE WIKI_PATHS (
    path_id       NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    start_article VARCHAR2(500) NOT NULL,
    end_article   VARCHAR2(500) NOT NULL,
    steps         NUMBER NOT NULL,
    succeeded     NUMBER(1) DEFAULT 1,
    creation_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

2. `WIKI_PATH_NODES` - Stores individual articles in each path:

```sql
CREATE TABLE WIKI_PATH_NODES (
    node_id       NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    path_id       NUMBER REFERENCES WIKI_PATHS(path_id),
    step_number   NUMBER NOT NULL,
    article_title VARCHAR2(500) NOT NULL,
    article_url   VARCHAR2(1000)
);
```

### Recreating Schema

The `recreate_schema.sql` script contains all DDL statements to recreate the schema from scratch:

```sql
-- Drop existing tables if they exist
BEGIN
    EXECUTE IMMEDIATE 'DROP TABLE WIKI_PATH_NODES';
EXCEPTION
    WHEN OTHERS THEN
        IF SQLCODE != -942 THEN
            RAISE;
        END IF;
END;
/

BEGIN
    EXECUTE IMMEDIATE 'DROP TABLE WIKI_PATHS';
EXCEPTION
    WHEN OTHERS THEN
        IF SQLCODE != -942 THEN
            RAISE;
        END IF;
END;
/

-- Create WIKI_PATHS table
CREATE TABLE WIKI_PATHS (
    path_id       NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    start_article VARCHAR2(500) NOT NULL,
    end_article   VARCHAR2(500) NOT NULL,
    steps         NUMBER NOT NULL,
    succeeded     NUMBER(1) DEFAULT 1,
    creation_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create WIKI_PATH_NODES table
CREATE TABLE WIKI_PATH_NODES (
    node_id       NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    path_id       NUMBER REFERENCES WIKI_PATHS(path_id),
    step_number   NUMBER NOT NULL,
    article_title VARCHAR2(500) NOT NULL,
    article_url   VARCHAR2(1000)
);

-- Create indexes for performance
CREATE INDEX idx_path_nodes_path_id ON WIKI_PATH_NODES(path_id);
CREATE INDEX idx_path_nodes_article ON WIKI_PATH_NODES(article_title);
CREATE INDEX idx_paths_start ON WIKI_PATHS(start_article);
CREATE INDEX idx_paths_end ON WIKI_PATHS(end_article);

-- Create WIKI_USER if it doesn't exist
BEGIN
    EXECUTE IMMEDIATE 'CREATE USER WIKI_USER IDENTIFIED BY wiki_password';
EXCEPTION
    WHEN OTHERS THEN
        IF SQLCODE != -1920 THEN
            RAISE;
        END IF;
END;
/

-- Grant permissions to WIKI_USER
GRANT CONNECT, RESOURCE TO WIKI_USER;
GRANT CREATE SESSION TO WIKI_USER;
GRANT UNLIMITED TABLESPACE TO WIKI_USER;

-- Create the same tables in WIKI_USER schema
CREATE TABLE WIKI_USER.WIKI_PATHS (
    path_id       NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    start_article VARCHAR2(500) NOT NULL,
    end_article   VARCHAR2(500) NOT NULL,
    steps         NUMBER NOT NULL,
    succeeded     NUMBER(1) DEFAULT 1,
    creation_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE WIKI_USER.WIKI_PATH_NODES (
    node_id       NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    path_id       NUMBER REFERENCES WIKI_USER.WIKI_PATHS(path_id),
    step_number   NUMBER NOT NULL,
    article_title VARCHAR2(500) NOT NULL,
    article_url   VARCHAR2(1000)
);

-- Create indexes in WIKI_USER schema
CREATE INDEX WIKI_USER.idx_path_nodes_path_id ON WIKI_USER.WIKI_PATH_NODES(path_id);
CREATE INDEX WIKI_USER.idx_path_nodes_article ON WIKI_USER.WIKI_PATH_NODES(article_title);
CREATE INDEX WIKI_USER.idx_paths_start ON WIKI_USER.WIKI_PATHS(start_article);
CREATE INDEX WIKI_USER.idx_paths_end ON WIKI_USER.WIKI_PATHS(end_article);

COMMIT;
```

To execute this script:

```bash
docker cp recreate_schema.sql oracle-wiki-21c:/tmp/
docker exec oracle-wiki-21c sqlplus sys/Oracle21c@XEPDB1 as sysdba @/tmp/recreate_schema.sql
```

## Data Collection with Python

### Wikipedia Crawler

The project includes a crawler that follows the "first link" of Wikipedia articles. This strategy follows the hypothesis that most paths eventually lead to the Philosophy article.

Key components of the crawler:

#### Core crawling functionality (`src/crawlers/parallel_wiki_crawler.py`):

```python
def crawl_wikipedia(start_article, target_depth, max_steps, conn):
    """Crawl Wikipedia starting from a given article"""
    path = []
    current_url = f"https://en.wikipedia.org/wiki/{start_article}"
    current_article = start_article
    
    print(f"Starting from: {current_url}")
    
    # Add starting node
    path.append((0, current_article, current_url))
    
    for step in range(1, max_steps + 1):
        try:
            # Get the webpage content
            response = requests.get(current_url, headers=HEADERS)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Process article
            print(f"Processing article: {current_article}")
            
            # Extract the first valid link from the main content
            next_link = find_first_valid_link(soup, current_article)
            
            if not next_link:
                print(f"Warning: No valid link found in article: {current_article}")
                return path, False
            
            # Extract article title from the link
            next_article = next_link.split('/wiki/')[1]
            next_article = urllib.parse.unquote(next_article)
            
            # Format the full URL
            next_url = f"https://en.wikipedia.org{next_link}"
            
            print(f"Step {step-1}: {current_article} -> {next_article}")
            
            # Add to path
            path.append((step, next_article, next_url))
            
            # Check if we've reached target depth
            if step >= target_depth:
                print(f"Reached target depth of {target_depth} steps")
                return path, True
            
            # Update for next iteration
            current_article = next_article
            current_url = next_url
            
        except Exception as e:
            print(f"Error crawling: {e}")
            return path, False
    
    return path, False
```

#### Database interaction:

```python
def store_path_in_database(path, succeeded, conn):
    """Store the crawled path in the Oracle database"""
    try:
        cursor = conn.cursor()
        
        # Get start and end articles
        start_article = path[0][1]
        end_article = path[-1][1]
        steps = len(path) - 1
        
        # Insert into WIKI_PATHS table
        insert_path_sql = """
        INSERT INTO WIKI_PATHS (start_article, end_article, steps, succeeded)
        VALUES (:1, :2, :3, :4)
        RETURNING path_id INTO :5
        """
        path_id_var = cursor.var(int)
        cursor.execute(insert_path_sql, (start_article, end_article, steps, 1 if succeeded else 0, path_id_var))
        path_id = path_id_var.getvalue()[0]
        
        # Insert nodes into WIKI_PATH_NODES table
        insert_node_sql = """
        INSERT INTO WIKI_PATH_NODES (path_id, step_number, article_title, article_url)
        VALUES (:1, :2, :3, :4)
        """
        for step, article, url in path:
            cursor.execute(insert_node_sql, (path_id, step, article, url))
        
        conn.commit()
        print(f"Stored path with ID {path_id} in the database")
        return path_id
    except Exception as e:
        conn.rollback()
        print(f"Error storing path: {e}")
        return None
```

### Running the Crawler

The crawler can be run in different modes:

1. Single run with specific parameters:

```bash
python -m src.crawlers.parallel_wiki_crawler \
  --user system --password Oracle21c --service XEPDB1 \
  -w 4 -r 10 -d 3 -m 10
```

Parameters:
- `-w`: Number of worker threads (4)
- `-r`: Number of random articles to crawl (10)
- `-d`: Target depth of path (3 steps)
- `-m`: Maximum steps per path (10)

2. Continuous crawling with `run_crawl.py`:

```bash
python run_crawl.py --workers 12 --batch-size 50 --depth 8 \
  --max-steps 25 --max-size 20 --service XEPDB1 \
  --user system --password Oracle21c --delay 3
```

3. Extended timed crawling with the shell script (`run_timed_crawl.sh`):

```bash
#!/bin/bash

# Calculate when to stop (5 hours from now)
END_TIME=$(($(date +%s) + 5*60*60))

echo "Starting 5-hour Wikipedia crawl at $(date)"
echo "Will end at $(date -r $END_TIME)"
echo "---------------------------------------------"

# Run the crawler until the time is up
while [ $(date +%s) -lt $END_TIME ]
do
    python run_crawl.py --workers 12 --batch-size 50 --depth 8 --max-steps 25 --max-size 20 --service XEPDB1 --user system --password Oracle21c --delay 3
    
    # If we still have time, start another batch
    if [ $(date +%s) -lt $END_TIME ]; then
        echo "---------------------------------------------"
        echo "Crawler stopped. Restarting for next batch..."
        echo "Time remaining: $(( ($END_TIME - $(date +%s)) / 60 )) minutes"
        echo "---------------------------------------------"
        sleep 5
    fi
done

echo "---------------------------------------------"
echo "5-hour crawl completed at $(date)"
echo "Run visualize_wiki_data.py and generate_wiki_report.py to see the results"
```

## Data Analysis

### SQL Queries

The project uses various SQL queries to analyze the collected data:

1. Path statistics:

```sql
-- Count total paths
SELECT COUNT(*) FROM WIKI_PATHS;

-- Average path length
SELECT AVG(steps) FROM WIKI_PATHS;

-- Success rate
SELECT 
    COUNT(*) AS total_paths,
    SUM(CASE WHEN succeeded = 1 THEN 1 ELSE 0 END) AS successful_paths,
    ROUND(SUM(CASE WHEN succeeded = 1 THEN 1 ELSE 0 END) * 100 / COUNT(*), 2) AS success_rate
FROM WIKI_PATHS;
```

2. Most common articles:

```sql
-- Most common articles across paths
SELECT article_title, COUNT(*) as frequency
FROM WIKI_PATH_NODES
GROUP BY article_title
ORDER BY frequency DESC
FETCH FIRST 15 ROWS ONLY;

-- Most common start articles
SELECT start_article, COUNT(*) as count
FROM WIKI_PATHS
GROUP BY start_article
ORDER BY count DESC
FETCH FIRST 5 ROWS ONLY;

-- Most common end articles
SELECT end_article, COUNT(*) as count
FROM WIKI_PATHS
GROUP BY end_article
ORDER BY count DESC
FETCH FIRST 5 ROWS ONLY;
```

3. Article transitions (connections):

```sql
-- Most common article transitions
SELECT 
    src.article_title as source,
    dst.article_title as target,
    COUNT(*) as frequency
FROM 
    WIKI_PATH_NODES src,
    WIKI_PATH_NODES dst
WHERE 
    src.path_id = dst.path_id
    AND dst.step_number = src.step_number + 1
GROUP BY
    src.article_title, dst.article_title
ORDER BY 
    frequency DESC
FETCH FIRST 10 ROWS ONLY;
```

### Python Visualization

The project uses several Python libraries to visualize the data:

- **pandas**: For data manipulation
- **matplotlib**: For creating plots
- **networkx**: For network graph analysis
- **seaborn**: For enhanced visualizations

Key visualization functions:

1. Bar chart of most common articles:

```python
def create_bar_chart(conn, output_dir, tables):
    """Create a bar chart of most common articles"""
    path_nodes_schema = get_table_schema(tables, 'WIKI_PATH_NODES')
    
    query = f"""
    SELECT article_title as "article_title", COUNT(*) as "frequency"
    FROM {path_nodes_schema}.WIKI_PATH_NODES
    GROUP BY article_title
    ORDER BY COUNT(*) DESC
    FETCH FIRST 15 ROWS ONLY
    """
    
    df = pd.read_sql(query, conn)
    df.columns = df.columns.str.lower()
        
    plt.figure(figsize=(12, 8))
    chart = sns.barplot(x='frequency', y='article_title', data=df, palette='viridis')
    
    plt.title('Most Common Wikipedia Articles in Paths', fontsize=16)
    plt.xlabel('Frequency', fontsize=12)
    plt.ylabel('Article', fontsize=12)
    plt.tight_layout()
    
    output_file = os.path.join(output_dir, 'wiki_article_frequency.png')
    plt.savefig(output_file, dpi=300)
    plt.close()
```

2. Network graph visualization:

```python
def create_network_graph(conn, output_dir, tables):
    """Create a network graph of article connections"""
    path_nodes_schema = get_table_schema(tables, 'WIKI_PATH_NODES')
    
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
    
    df = pd.read_sql(query, conn)
    df.columns = df.columns.str.lower()
    df['weight'] = pd.to_numeric(df['weight'])
    
    # Create network graph
    G = nx.from_pandas_edgelist(df, 'source', 'target', edge_attr='weight')
    
    # Set node size based on degree centrality
    centrality = nx.degree_centrality(G)
    node_size = [centrality[node] * 5000 + 100 for node in G.nodes()]
    
    # Create visualization
    plt.figure(figsize=(16, 12))
    pos = nx.spring_layout(G, seed=42, k=0.3)
    
    nx.draw_networkx_nodes(G, pos, node_size=node_size, node_color='lightblue', alpha=0.8)
    edge_width = [G[u][v]['weight'] * 0.5 + 0.1 for u, v in G.edges()]
    nx.draw_networkx_edges(G, pos, width=edge_width, alpha=0.6, edge_color='gray')
    
    important_nodes = {node: node for node, cent in centrality.items() if cent > 0.05}
    nx.draw_networkx_labels(G, pos, labels=important_nodes, font_size=8, font_weight='bold')
    
    plt.title('Wikipedia Article Network', fontsize=16)
    plt.axis('off')
    plt.tight_layout()
    
    output_file = os.path.join(output_dir, 'wiki_network_graph.png')
    plt.savefig(output_file, dpi=300)
```

3. Circular network layout:

```python
def create_circular_network(conn, output_dir, tables):
    """Create a circular network visualization of article connections"""
    path_nodes_schema = get_table_schema(tables, 'WIKI_PATH_NODES')
    
    # Same query as network graph
    query = "..."  # Same as above
    
    df = pd.read_sql(query, conn)
    df.columns = df.columns.str.lower()
    df['weight'] = pd.to_numeric(df['weight'])
    
    # Create network graph
    G = nx.from_pandas_edgelist(df, 'source', 'target', edge_attr='weight')
    
    # Calculate betweenness centrality
    betweenness = nx.betweenness_centrality(G)
    node_colors = [plt.cm.plasma(betweenness[node] * 4) for node in G.nodes()]
    
    # Node sizes based on degree
    node_degrees = dict(G.degree())
    node_size = [node_degrees[node] * 100 + 100 for node in G.nodes()]
    
    # Create circular layout
    fig, ax = plt.subplots(figsize=(20, 20))
    pos = nx.circular_layout(G)
    
    nx.draw_networkx_nodes(G, pos, node_size=node_size, node_color=node_colors, alpha=0.8, ax=ax)
    edge_width = [G[u][v]['weight'] * 0.5 + 0.1 for u, v in G.edges()]
    nx.draw_networkx_edges(G, pos, width=edge_width, alpha=0.5, edge_color='gray', ax=ax)
    
    # Add colorbar for betweenness centrality
    sm = plt.cm.ScalarMappable(cmap=plt.cm.plasma, norm=plt.Normalize(vmin=0, vmax=max(betweenness.values())))
    sm.set_array([])
    cbar = plt.colorbar(sm, ax=ax, shrink=0.6)
    cbar.set_label('Betweenness Centrality')
    
    plt.title('Wikipedia Article Relationship Network (Circular Layout)', fontsize=18)
    plt.axis('off')
    plt.tight_layout()
    
    output_file = os.path.join(output_dir, 'wiki_circular_network.png')
    plt.savefig(output_file, dpi=300)
```

## Generating Reports

### HTML Reports

The project includes a comprehensive HTML report generator (`generate_wiki_report.py`) that combines statistics and visualizations:

```python
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
            /* CSS styles omitted for brevity */
        </style>
    </head>
    <body>
        <div class="report-header">
            <h1>Wikipedia Path Analysis Report</h1>
            <p>Analysis of paths between Wikipedia articles using the "first link" strategy</p>
            <p>Generated on {{ date }}</p>
        </div>
        
        <!-- Statistics section -->
        <div class="report-section">
            <h2>Key Statistics</h2>
            <div class="stats-grid">
                <div class="stats-card">
                    <h3>Total Paths</h3>
                    <div class="stats-value">{{ stats.total_paths }}</div>
                </div>
                <!-- Other statistics cards -->
            </div>
        </div>
        
        <!-- Visualizations section -->
        <div class="report-section">
            <h2>Visualizations</h2>
            
            <h3>Distribution of Path Lengths</h3>
            <div class="visualization">
                <img src="visualizations/path_length_histogram.png" alt="Path Length Histogram">
                <p>Distribution of path lengths (steps) across all paths</p>
            </div>
            
            <!-- Other visualizations -->
        </div>
        
        <!-- Network Analysis section -->
        <div class="report-section">
            <h2>Network Analysis</h2>
            <!-- Network analysis tables -->
        </div>
        
        <!-- Sample Paths section -->
        <div class="report-section">
            <h2>Sample Paths</h2>
            <!-- Sample paths -->
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
```

## Troubleshooting

### Common Issues

1. Docker container not starting:
   - Ensure Docker has enough memory allocated (at least 4GB)
   - Check Docker logs: `docker logs oracle-wiki-21c`

2. Database connection errors:
   - Verify container is running: `docker ps`
   - Test connection: `docker exec oracle-wiki-21c sqlplus sys/Oracle21c@XEPDB1 as sysdba`
   - Check if the service is accessible: `docker exec oracle-wiki-21c lsnrctl status`

3. Table structure errors:
   - Verify tables exist: `docker exec oracle-wiki-21c sqlplus sys/Oracle21c@XEPDB1 as sysdba @/tmp/check_tables.sql`
   - Run recreate_schema.sql to recreate tables

4. Python library issues:
   - Ensure all dependencies are installed: `pip install -r requirements.txt`
   - Check for Python version compatibility (requires Python 3.6+)

5. Oracle APEX issues:
   - Verify APEX installation: `docker exec oracle-wiki-21c sqlplus sys/Oracle21c@XEPDB1 as sysdba -S <<< "SELECT VERSION_NO FROM APEX_RELEASE;"`
   - Run APEX configuration scripts

### Monitoring Database Size

To check the current size of the database:

```sql
SELECT 
    owner, 
    segment_name, 
    SUM(bytes)/1024/1024 as size_mb 
FROM 
    dba_segments 
WHERE 
    owner IN ('SYSTEM', 'WIKI_USER') 
    AND segment_name IN ('WIKI_PATHS', 'WIKI_PATH_NODES')
GROUP BY 
    owner, segment_name
ORDER BY 
    size_mb DESC;
``` 