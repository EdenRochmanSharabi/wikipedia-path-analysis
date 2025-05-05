# Wikipedia Network Analysis SQL Framework

## Overview

This collection of SQL scripts provides comprehensive analytical capabilities for analyzing Wikipedia link networks. The framework is designed to process, analyze, and derive insights from large-scale Wikipedia crawling data, focusing on the paths users take when navigating from one article to another.

The scripts utilize advanced Oracle Database features to implement sophisticated statistical measures, data modeling techniques, and big data optimizations for scalable performance.

## Database Structure

The analysis is performed on the `WIKI_COPY` schema, which contains these core tables:

- `WIKI_PATHS`: Records of paths crawled, including start article, end article, number of steps, and success status
- `WIKI_PATH_NODES`: Individual nodes (articles) within each path, with their position in the path

## SQL Scripts

### 1. Basic Path Analysis (`01_path_analysis.sql`)

Basic analytical queries to understand path distributions and characteristics:

- Total paths and articles counts
- Path length distribution statistics
- Top starting and ending articles
- Most common articles appearing in paths
- Articles commonly leading to Philosophy
- Common path patterns (article pairs)
- Success rate trends over time

### 2. Network Analysis (`02_network_analysis.sql`)

Graph-based analysis of the Wikipedia link structure:

- Hub article identification (high in/out degree)
- Strongly connected path analysis
- Bottleneck article identification
- Common path segment analysis
- Circular reference detection
- Domain category bridge analysis
- Centrality analysis
- Path structure complexity

### 3. Advanced Statistical Analysis (`03_statistical_analysis.sql`)

Sophisticated statistical measures and models:

- Comprehensive statistical distributions (mean, median, quartiles, standard deviation)
- Z-score analysis for outlier detection
- Time series analysis with moving averages
- Correlation analysis between path attributes
- Statistical distribution of network centrality
- Regression analysis for path success prediction
- Category distribution inference
- Article volatility analysis

### 4. Logical Data Modeling (`04_data_modeling.sql`)

Advanced data modeling techniques for graph data:

- Star schema transformation (dimensions and facts)
- Graph model optimization (adjacency lists, edge lists)
- Temporal graph modeling
- Hierarchical clustering model
- Community detection algorithms
- Path pattern analysis

### 5. Big Data Techniques (`05_big_data_techniques.sql`)

Optimizations for large-scale data processing:

- Partitioning strategies (range and hash)
- Parallel query execution
- Materialized views for complex metrics
- Bitmap and function-based indexing
- Result caching and in-memory optimizations
- Dynamic sampling for query optimization
- Approximate count techniques
- SQL model clause for analytical processing
- Partition pruning optimizations
- Advanced optimizer directives

## Technical Capabilities Demonstrated

### Oracle Database Expertise

- Complex SQL query formulation with CTEs, window functions, and analytical functions
- Oracle-specific features: LISTAGG, PERCENTILE_CONT, NTILE, partitioning
- Performance optimization using hints (PARALLEL, LEADING, USE_HASH)
- Materialized views and specialized indexes
- Advanced SQL constructs like the MODEL clause
- Memory optimization with RESULT_CACHE and INMEMORY directives

### Statistical Analysis Capabilities

- Descriptive statistics (mean, median, standard deviation, quartiles)
- Distribution analysis with percentiles and cumulative distributions
- Z-score calculations for outlier detection
- Time-series analysis with moving averages
- Correlation analysis between variables
- Logistic regression modeling in SQL
- Clustering and categorization algorithms

### Logical Data Modeling

- Star schema design for dimensional modeling
- Graph data representations (adjacency lists, edge lists)
- Temporal modeling techniques
- Hierarchical clustering structures
- Entity relationship modeling for network data
- Data denormalization strategies for analytical purposes

### Big Data Architectures

- Partitioning strategies for massive datasets
- Parallel processing techniques
- Memory optimization for large-scale operations
- Materialized view strategies for pre-computed metrics
- Indexing strategies for high-cardinality data
- Approximation techniques for performance optimization
- Query optimization for complex graph operations

## Usage Examples

### Basic Path Length Distribution

```sql
-- Path length distribution with statistical categorization
SELECT 
    steps, 
    COUNT(*) as path_count,
    ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM WIKI_COPY.WIKI_PATHS), 2) as percentage,
    CASE 
        WHEN steps < avg_steps - stddev_steps THEN 'Short'
        WHEN steps > avg_steps + stddev_steps THEN 'Long'
        ELSE 'Average'
    END as length_category
FROM 
    WIKI_COPY.WIKI_PATHS,
    (SELECT AVG(steps) as avg_steps, STDDEV(steps) as stddev_steps FROM WIKI_COPY.WIKI_PATHS)
GROUP BY 
    steps, avg_steps, stddev_steps
ORDER BY 
    steps;
```

### Identifying Network Hub Articles

```sql
-- Find top hub articles by combined degree centrality
WITH outgoing AS (
    SELECT 
        n1.article_title,
        COUNT(DISTINCT n2.article_title) as outgoing_count
    FROM 
        WIKI_COPY.WIKI_PATH_NODES n1
    JOIN 
        WIKI_COPY.WIKI_PATH_NODES n2 
        ON n1.path_id = n2.path_id
        AND n2.step_number = n1.step_number + 1
    GROUP BY 
        n1.article_title
),
incoming AS (
    SELECT 
        n2.article_title,
        COUNT(DISTINCT n1.article_title) as incoming_count
    FROM 
        WIKI_COPY.WIKI_PATH_NODES n1
    JOIN 
        WIKI_COPY.WIKI_PATH_NODES n2 
        ON n1.path_id = n2.path_id
        AND n2.step_number = n1.step_number + 1
    GROUP BY 
        n2.article_title
)
SELECT 
    COALESCE(o.article_title, i.article_title) as article,
    NVL(incoming_count, 0) as in_degree,
    NVL(outgoing_count, 0) as out_degree,
    NVL(incoming_count, 0) + NVL(outgoing_count, 0) as total_degree
FROM 
    outgoing o
FULL OUTER JOIN 
    incoming i ON o.article_title = i.article_title
ORDER BY 
    total_degree DESC
FETCH FIRST 20 ROWS ONLY;
```

### Analyzing Time Trends with Moving Averages

```sql
-- Time series analysis with moving averages
WITH daily_stats AS (
    SELECT 
        TO_CHAR(creation_date, 'YYYY-MM-DD') as day,
        COUNT(*) as paths_collected,
        ROUND(AVG(steps), 2) as avg_path_length,
        SUM(CASE WHEN succeeded = 1 THEN 1 ELSE 0 END) as successful_paths,
        ROUND(SUM(CASE WHEN succeeded = 1 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) as success_rate
    FROM 
        WIKI_COPY.WIKI_PATHS
    GROUP BY 
        TO_CHAR(creation_date, 'YYYY-MM-DD')
)
SELECT 
    day,
    paths_collected,
    avg_path_length,
    success_rate,
    -- 3-day moving averages
    ROUND(AVG(paths_collected) OVER (ORDER BY day ROWS BETWEEN 2 PRECEDING AND CURRENT ROW), 2) as ma3_paths,
    ROUND(AVG(avg_path_length) OVER (ORDER BY day ROWS BETWEEN 2 PRECEDING AND CURRENT ROW), 2) as ma3_length,
    ROUND(AVG(success_rate) OVER (ORDER BY day ROWS BETWEEN 2 PRECEDING AND CURRENT ROW), 2) as ma3_success
FROM 
    daily_stats
ORDER BY 
    day;
```

## Performance Considerations

For optimal performance when working with large Wikipedia datasets:

1. **Partitioned Tables**: Use the partitioned table structures for datasets exceeding 100 million records
2. **Materialized Views**: Leverage pre-computed metrics for common analytical queries
3. **Parallel Execution**: Utilize the PARALLEL hint for resource-intensive operations
4. **Memory Optimization**: Apply RESULT_CACHE and INMEMORY directives for frequently accessed data
5. **Index Strategy**: Use appropriate indexes (B-tree, bitmap, function-based) based on data characteristics
6. **Query Optimization**: Apply optimizer hints for complex joins and filtering conditions

## Implementation Notes

The SQL framework is designed for Oracle Database 19c or higher to leverage advanced analytical capabilities. Most queries can be adapted for other database platforms with minor syntax adjustments, but Oracle-specific features like the MODEL clause would require alternative implementations. 