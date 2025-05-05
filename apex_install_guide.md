# Oracle APEX Installation and Configuration Guide

The APEX installation in the Oracle Express container isn't working correctly. Here are two options to access your database and visualize your data:

## Option 1: Access Enterprise Manager Database Express

1. Open your browser and navigate to https://localhost:5500/em
2. Enter the following credentials:
   - Username: sys
   - Password: Oracle21c
   - Connect As: SYSDBA
   - Container: XEPDB1
3. Accept the self-signed certificate warning if it appears

From Enterprise Manager, you can:
- Browse database objects
- Run SQL queries
- View table data
- Create basic reports

## Option 2: Use Oracle SQL Developer

1. Download Oracle SQL Developer from the Oracle website (if not already installed)
2. Create a new connection with these settings:
   - Connection Name: Wiki_Oracle
   - Username: sys
   - Password: Oracle21c
   - Role: SYSDBA
   - Hostname: localhost
   - Port: 1521
   - Service name: XEPDB1
3. Connect and explore your database

## Option 3: Create Data Visualizations Without APEX

You can use alternative tools to create visualizations of your Wikipedia data:

### Python Visualization
```python
import pandas as pd
import matplotlib.pyplot as plt
import oracledb
import seaborn as sns

# Connect to Oracle
conn = oracledb.connect("system/Oracle21c@localhost:1521/XEPDB1")

# Query most common articles
query = """
SELECT article_title, COUNT(*) as frequency
FROM wiki_user.wiki_path_nodes
GROUP BY article_title
HAVING COUNT(*) > 1
ORDER BY frequency DESC
FETCH FIRST 10 ROWS ONLY
"""

# Read data into pandas
df = pd.read_sql(query, conn)

# Create visualization
plt.figure(figsize=(12, 6))
sns.barplot(x='frequency', y='article_title', data=df)
plt.title('Most Common Wikipedia Articles in Paths')
plt.tight_layout()
plt.savefig('wiki_article_frequency.png')
plt.show()

# Close connection
conn.close()
```

### Network Graph Visualization
```python
import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt
import oracledb

# Connect to Oracle
conn = oracledb.connect("system/Oracle21c@localhost:1521/XEPDB1")

# Query path connections
query = """
SELECT 
    src.article_title as source,
    dst.article_title as target,
    COUNT(*) as weight
FROM 
    wiki_user.wiki_path_nodes src,
    wiki_user.wiki_path_nodes dst
WHERE 
    src.path_id = dst.path_id
    AND dst.step_number = src.step_number + 1
GROUP BY
    src.article_title, dst.article_title
"""

# Read data into pandas
df = pd.read_sql(query, conn)

# Create network graph
G = nx.from_pandas_edgelist(df, 'source', 'target', ['weight'])

# Plot graph
plt.figure(figsize=(15, 10))
pos = nx.spring_layout(G, seed=42)
nodes = nx.draw_networkx_nodes(G, pos, node_size=700, node_color='lightblue')
edges = nx.draw_networkx_edges(G, pos, width=1, alpha=0.7)
labels = nx.draw_networkx_labels(G, pos, font_size=8)
plt.axis('off')
plt.title('Wikipedia Article Connections')
plt.tight_layout()
plt.savefig('wiki_network_graph.png')
plt.show()

# Close connection
conn.close()
```

## Option 4: Reinstall APEX (Advanced)

If you really need APEX, you'd need to:

1. Download the APEX installation files
2. Configure ORDS (Oracle REST Data Services)
3. Set up the APEX listener

This is a complex process and may require rebuilding your Docker container. If you want to pursue this option, please refer to the official Oracle documentation for APEX installation.

## Using SQL for Data Analysis

You can still run SQL queries directly in the database to analyze your Wikipedia data:

```sql
-- Most common articles
SELECT article_title, COUNT(*) as frequency
FROM wiki_user.wiki_path_nodes
GROUP BY article_title
HAVING COUNT(*) > 1
ORDER BY frequency DESC;

-- Average path length
SELECT AVG(steps) as avg_path_length
FROM wiki_user.wiki_paths;

-- Article connections
SELECT 
    src.article_title as source,
    dst.article_title as target,
    COUNT(*) as frequency
FROM 
    wiki_user.wiki_path_nodes src,
    wiki_user.wiki_path_nodes dst
WHERE 
    src.path_id = dst.path_id
    AND dst.step_number = src.step_number + 1
GROUP BY
    src.article_title, dst.article_title
ORDER BY 
    frequency DESC;
``` 