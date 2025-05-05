# Miscellaneous Useful Information

This document contains additional information, tips, and best practices that weren't covered in other documentation files.

## Development Workflow

### Local Development Setup

For local development without Docker, set up your environment:

```bash
# Create a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up local connection string for testing
export ORACLE_CONNECTION_STRING="username/password@localhost:1521/service"
```

### Version Control Best Practices

- Always create feature branches for new development
- Use descriptive commit messages that explain the purpose of changes
- Tag versions when deploying to production
- Keep large binary files (like images, dumps, logs) out of Git using .gitignore

## Performance Optimization

### Crawler Performance Tips

1. **Connection Pooling**: The crawler uses connection pooling to minimize database connection overhead. Configure pool size in `src/db/wiki_db_storage.py`:

```python
pool_size = min(32, os.cpu_count() + 4)  # Adjust based on system capabilities
```

2. **Rate Limiting**: Adjust Wikipedia API requests rate to avoid IP blocking:

```python
# In src/crawlers/parallel_wiki_crawler.py
RATE_LIMIT = 10  # Requests per second
```

3. **Memory Management**: For large crawls, use incremental processing:

```bash
scripts/run_large_crawler.sh --batch-size 1000 --checkpoint-interval 300
```

### Database Optimization

1. **Indexing Strategy**: The following indexes significantly improve query performance:

```sql
-- Create indexes on frequently queried columns
CREATE INDEX wiki_paths_start_idx ON wiki_paths(start_article);
CREATE INDEX wiki_paths_end_idx ON wiki_paths(end_article);
CREATE INDEX wiki_path_nodes_path_id_idx ON wiki_path_nodes(path_id);
CREATE INDEX wiki_path_nodes_article_idx ON wiki_path_nodes(article_name);
```

2. **Materialized Views**: Precompute common aggregations:

```sql
-- Example materialized view for path statistics
CREATE MATERIALIZED VIEW mv_path_stats
REFRESH COMPLETE ON DEMAND
AS
SELECT 
    end_article,
    COUNT(*) as path_count,
    AVG(steps) as avg_steps,
    MIN(steps) as min_steps,
    MAX(steps) as max_steps
FROM wiki_paths
GROUP BY end_article;
```

3. **Oracle Performance Parameters**:

```sql
-- Set appropriate SGA and PGA sizes
ALTER SYSTEM SET sga_target = 4G;
ALTER SYSTEM SET pga_aggregate_target = 2G;

-- Enable result cache for commonly executed queries
ALTER SYSTEM SET result_cache_mode = FORCE;
```

## Wiki API Considerations

### API Limitations

Wikipedia's API has rate limits to prevent abuse. Consider these guidelines:

- Keep requests under 200 per minute
- Add proper User-Agent headers identifying your crawler
- Implement exponential backoff for retries
- Use the official API rather than scraping

Example custom User-Agent setting:

```python
# In wiki_core.py
HEADERS = {
    'User-Agent': 'WikiPathAnalysis/1.0 (https://yourwebsite.com; yourname@example.com)'
}
```

### Handling Wiki Content Changes

Wikipedia content changes over time. To ensure reproducibility:

1. Store timestamps with each path
2. Consider using Wikipedia's revision IDs for exact version tracking
3. Implement periodic recrawling of paths to check for changes

## Analysis Techniques

### Advanced SQL Queries

#### Finding Central Articles

Articles that appear in many paths can be identified with:

```sql
SELECT 
    wpn.article_name,
    COUNT(DISTINCT wpn.path_id) as appearance_count
FROM wiki_path_nodes wpn
GROUP BY wpn.article_name
ORDER BY appearance_count DESC
FETCH FIRST 20 ROWS ONLY;
```

#### Analyzing Path Convergence

Find where paths begin to converge:

```sql
WITH path_positions AS (
    SELECT 
        wpn.path_id,
        wpn.article_name,
        wpn.position,
        wp.start_article
    FROM wiki_path_nodes wpn
    JOIN wiki_paths wp ON wpn.path_id = wp.id
),
convergence_points AS (
    SELECT 
        a.article_name,
        a.position,
        COUNT(DISTINCT a.start_article) as distinct_starts
    FROM path_positions a
    GROUP BY a.article_name, a.position
    HAVING COUNT(DISTINCT a.start_article) > 5
)
SELECT * FROM convergence_points
ORDER BY distinct_starts DESC, position;
```

### Network Visualization Tips

When visualizing the wiki path network:

1. **Limit Graph Size**: Focus on paths with specific characteristics
2. **Use Node Sizing**: Set node size based on centrality or frequency
3. **Color Coding**: Use colors to represent categories or domains
4. **Interactive Features**: Implement zoom, filtering, and hover details

Example visualization parameters (used in `src/dashboard/wiki_dashboard.py`):

```python
# Node size based on frequency
node_sizes = [10 + (count * 0.5) for count in node_counts]

# Color nodes by category
category_colors = {
    'science': '#4286f4',
    'mathematics': '#41f4a0',
    'philosophy': '#f44242',
    'other': '#a8a8a8'
}
```

## Data Interpretation Guidelines

### Path Analysis Interpretation

When interpreting path analysis results:

1. **Length Distribution**: Most successful paths to Philosophy are 15-25 steps long
2. **Dead Ends**: Pages with no links, red links, or circular references cause path failures
3. **Domain Convergence**: Paths tend to converge in abstract/fundamental topic areas
4. **Temporal Changes**: Wikipedia edits can alter paths over time

### Statistical Significance

Consider:
- Paths with at least 30 samples for statistical significance
- Z-scores above 2.0 indicate significant deviation from average
- Account for circular references when analyzing convergence

## Security Considerations

### Database Security

1. **User Permissions**: Create dedicated users with minimal privileges:

```sql
-- Create application user with limited permissions
CREATE USER wiki_app IDENTIFIED BY secure_password;
GRANT CONNECT, RESOURCE TO wiki_app;
GRANT SELECT, INSERT ON wiki_paths TO wiki_app;
GRANT SELECT, INSERT ON wiki_path_nodes TO wiki_app;
```

2. **Connection Security**: Use encrypted connections and secure passwords

3. **API Key Management**: Store any API keys securely, not in code

### Oracle APEX Security

1. **Workspace Isolation**: Create separate workspaces for development and production
2. **Authentication**: Use stronger authentication methods than the default
3. **Access Control**: Implement proper authorization and row-level security

## Project Maintenance

### Database Maintenance

Regular maintenance tasks:

```sql
-- Gather statistics for optimizer
EXEC DBMS_STATS.GATHER_SCHEMA_STATS('WIKI');

-- Rebuild fragmented indexes
ALTER INDEX wiki_paths_pk REBUILD;
ALTER INDEX wiki_path_nodes_pk REBUILD;

-- Purge recyclebin
PURGE RECYCLEBIN;
```

### Log Management

- Rotate logs regularly to prevent disk space issues
- Archive old logs for historical analysis
- Set appropriate log levels:

```bash
# In scripts/run_crawler.sh
LOG_LEVEL=INFO  # Change to DEBUG for troubleshooting
```

## Useful References

### Oracle Database Resources

- [Oracle Database Documentation](https://docs.oracle.com/en/database/)
- [Oracle SQL Language Reference](https://docs.oracle.com/en/database/oracle/oracle-database/19/sqlrf/index.html)
- [Oracle PL/SQL Language Reference](https://docs.oracle.com/en/database/oracle/oracle-database/19/lnpls/index.html)

### Python Libraries Documentation

- [cx_Oracle](https://cx-oracle.readthedocs.io/)
- [Requests](https://requests.readthedocs.io/)
- [Beautiful Soup](https://www.crummy.com/software/BeautifulSoup/bs4/doc/)
- [NetworkX](https://networkx.org/documentation/stable/)
- [Matplotlib](https://matplotlib.org/stable/contents.html)

### Wikipedia API Documentation

- [MediaWiki API](https://www.mediawiki.org/wiki/API:Main_page)
- [Wikipedia API Usage Policies](https://www.mediawiki.org/wiki/API:Etiquette)

## Project History

The Wikipedia Path Analysis project originated from the "Getting to Philosophy" phenomenon, where clicking the first link in a Wikipedia article, and repeating the process for subsequent articles, usually leads to the Philosophy article.

The project has evolved through several phases:
1. Initial proof-of-concept with single-threaded crawler
2. Database integration for persistent storage
3. Parallel processing implementation
4. Advanced analytics framework
5. Visualization and reporting capabilities

## Future Directions

Potential areas for project expansion:

1. **Multilingual Analysis**: Compare path patterns across different language Wikipedias
2. **Machine Learning**: Predict path endpoints based on starting article characteristics
3. **Real-time Monitoring**: Track path changes as Wikipedia evolves
4. **API Service**: Expose path finding as a web service
5. **Community Analysis**: Identify topic clusters and community structures in the network

## Environment Variables

The application uses these environment variables:

| Variable | Purpose | Default |
|----------|---------|---------|
| ORACLE_CONNECTION_STRING | Database connection | "system/oracle@localhost:1521/FREE" |
| WIKI_CRAWL_THREADS | Number of crawler threads | 16 |
| WIKI_BATCH_SIZE | Articles per batch | 100 |
| WIKI_MAX_DEPTH | Maximum path depth | 30 |
| LOG_LEVEL | Logging verbosity | "INFO" |

## Common Error Resolutions

| Error | Resolution |
|-------|------------|
| ORA-12154: TNS:could not resolve the connect identifier | Check tnsnames.ora configuration and connection string |
| ORA-01017: invalid username/password | Verify database credentials |
| Rate limit exceeded on Wikipedia API | Reduce request rate and implement backoff |
| Out of memory during large crawls | Reduce batch size, enable checkpointing |
| Database connection timeouts | Adjust connection pool settings, check network | 