# Wikipedia Paths in Oracle Database

This project creates and analyzes paths between Wikipedia articles stored in an Oracle database. It uses a crawler that follows the "first link" strategy, where it always clicks on the first link in the main text of each Wikipedia article.

## Setup Instructions

### Prerequisites
- Docker
- Python 3.7+
- Oracle client libraries

### Required Python Libraries
```
pip install oracledb tabulate matplotlib networkx
```

### Docker Setup
1. Pull and run the Oracle Express container:
```bash
docker run -d \
  --name oracle-wiki-21c \
  -p 1521:1521 -p 5500:5500 -p 8080:8080 \
  -e ORACLE_PWD=Oracle21c \
  container-registry.oracle.com/database/express:latest
```

2. Wait for the container to be fully up and running (may take 10-15 minutes):
```bash
docker logs -f oracle-wiki-21c
```

### Database Setup
1. Create the database schema:
```bash
docker cp recreate_schema.sql oracle-wiki-21c:/tmp/
docker exec oracle-wiki-21c sqlplus sys/Oracle21c@XEPDB1 as sysdba @/tmp/recreate_schema.sql
```

## Running the Crawler

The crawler fetches Wikipedia articles and stores the paths between them:

```bash
# Basic crawl with 2 workers and 5 random articles
python -m src.crawlers.parallel_wiki_crawler \
  --user system --password Oracle21c --service XEPDB1 \
  -w 2 -r 5 -d 3 -m 10

# More extensive crawl
python -m src.crawlers.parallel_wiki_crawler \
  --user system --password Oracle21c --service XEPDB1 \
  -w 4 -r 20 -d 3 -m 10
```

Parameters:
- `-w`: Number of workers (parallel crawlers)
- `-r`: Number of random articles to start with
- `-d`: Target path depth
- `-m`: Maximum steps per path
- `--max-size`: Maximum database size in GB (default 2GB)

## Analyzing the Data

### View Basic Statistics
```bash
python analyze_wiki_paths.py
```

### View Specific Path Details
```bash
python analyze_wiki_paths.py --path-id 1
```

### Export All Paths to JSON
```bash
python analyze_wiki_paths.py --export --output wiki_paths.json
```

## Database Schema

### WIKI_PATHS Table
Stores metadata about each path:
- `path_id`: Unique identifier (auto-increment)
- `start_article`: The starting article title
- `end_article`: The final article title
- `steps`: Number of steps in the path
- `succeeded`: Whether the path reached the target depth (1=yes, 0=no)
- `creation_date`: When the path was crawled

### WIKI_PATH_NODES Table
Stores each node (article) in a path:
- `node_id`: Unique identifier (auto-increment)
- `path_id`: Foreign key to WIKI_PATHS
- `step_number`: Position in the path (0 = start)
- `article_title`: The article title
- `article_url`: Full URL to the Wikipedia article

## Example Queries

### Most common articles across all paths
```sql
SELECT article_title, COUNT(*) as frequency
FROM WIKI_PATH_NODES
GROUP BY article_title
ORDER BY frequency DESC
FETCH FIRST 10 ROWS ONLY;
```

### Longest paths
```sql
SELECT path_id, start_article, end_article, steps
FROM WIKI_PATHS
ORDER BY steps DESC
FETCH FIRST 5 ROWS ONLY;
```

### Articles that serve as bridges between multiple paths
```sql
SELECT article_title, COUNT(DISTINCT path_id) as num_paths
FROM WIKI_PATH_NODES
GROUP BY article_title
HAVING COUNT(DISTINCT path_id) > 1
ORDER BY num_paths DESC;
```

## Viewing Data in Oracle APEX

1. Access the Oracle Enterprise Manager:
   - URL: https://localhost:5500/em
   - Username: sys
   - Password: Oracle21c
   - Container: XEPDB1

2. Navigate to "SQL Workshop" > "SQL Commands" to run queries

3. Create a report in APEX to visualize the paths 