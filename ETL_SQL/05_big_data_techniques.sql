-- Big Data Techniques for Wikipedia Network Analysis
-- This file contains SQL queries optimized for large-scale processing of Wikipedia network data

-- 1. Partitioning Strategy for Large Wiki Datasets
-- Demonstrate how to partition tables for improved query performance

-- Path table partitioning by date ranges
CREATE TABLE WIKI_COPY.WIKI_PATHS_PARTITIONED (
    path_id NUMBER PRIMARY KEY,
    start_article VARCHAR2(500),
    end_article VARCHAR2(500),
    steps NUMBER,
    succeeded NUMBER(1),
    creation_date DATE
)
PARTITION BY RANGE (creation_date) (
    PARTITION paths_q1_2023 VALUES LESS THAN (TO_DATE('2023-04-01', 'YYYY-MM-DD')),
    PARTITION paths_q2_2023 VALUES LESS THAN (TO_DATE('2023-07-01', 'YYYY-MM-DD')),
    PARTITION paths_q3_2023 VALUES LESS THAN (TO_DATE('2023-10-01', 'YYYY-MM-DD')),
    PARTITION paths_q4_2023 VALUES LESS THAN (TO_DATE('2024-01-01', 'YYYY-MM-DD')),
    PARTITION paths_q1_2024 VALUES LESS THAN (TO_DATE('2024-04-01', 'YYYY-MM-DD')),
    PARTITION paths_q2_2024 VALUES LESS THAN (TO_DATE('2024-07-01', 'YYYY-MM-DD')),
    PARTITION paths_q3_2024 VALUES LESS THAN (TO_DATE('2024-10-01', 'YYYY-MM-DD')),
    PARTITION paths_q4_2024 VALUES LESS THAN (TO_DATE('2025-01-01', 'YYYY-MM-DD')),
    PARTITION paths_future VALUES LESS THAN (MAXVALUE)
);

-- Path nodes table partitioning by hash of path_id
CREATE TABLE WIKI_COPY.WIKI_PATH_NODES_PARTITIONED (
    node_id NUMBER PRIMARY KEY,
    path_id NUMBER,
    article_title VARCHAR2(500),
    step_number NUMBER
)
PARTITION BY HASH (path_id) PARTITIONS 16;

-- Load data statements (commented out as they would be executed only once)
-- INSERT INTO WIKI_COPY.WIKI_PATHS_PARTITIONED SELECT * FROM WIKI_COPY.WIKI_PATHS;
-- INSERT INTO WIKI_COPY.WIKI_PATH_NODES_PARTITIONED SELECT rownum as node_id, path_id, article_title, step_number FROM WIKI_COPY.WIKI_PATH_NODES;

-- Create necessary indexes on partitioned tables
CREATE INDEX WIKI_COPY.idx_paths_part_start_article ON WIKI_COPY.WIKI_PATHS_PARTITIONED(start_article) LOCAL;
CREATE INDEX WIKI_COPY.idx_paths_part_end_article ON WIKI_COPY.WIKI_PATHS_PARTITIONED(end_article) LOCAL;
CREATE INDEX WIKI_COPY.idx_paths_part_steps ON WIKI_COPY.WIKI_PATHS_PARTITIONED(steps) LOCAL;
CREATE INDEX WIKI_COPY.idx_paths_part_succeeded ON WIKI_COPY.WIKI_PATHS_PARTITIONED(succeeded) LOCAL;

CREATE INDEX WIKI_COPY.idx_nodes_part_path_id ON WIKI_COPY.WIKI_PATH_NODES_PARTITIONED(path_id) LOCAL;
CREATE INDEX WIKI_COPY.idx_nodes_part_article ON WIKI_COPY.WIKI_PATH_NODES_PARTITIONED(article_title) LOCAL;
CREATE INDEX WIKI_COPY.idx_nodes_part_step ON WIKI_COPY.WIKI_PATH_NODES_PARTITIONED(step_number) LOCAL;

-- 2. Parallel Query Optimization
-- Example of using parallel hints for large data processing

-- Count paths with parallel execution
SELECT /*+ PARALLEL(8) */
    COUNT(*) as total_paths,
    SUM(CASE WHEN succeeded = 1 THEN 1 ELSE 0 END) as successful_paths,
    ROUND(AVG(steps), 2) as avg_path_length,
    MIN(steps) as min_path_length,
    MAX(steps) as max_path_length
FROM 
    WIKI_COPY.WIKI_PATHS_PARTITIONED;

-- Find top articles with parallel processing
SELECT /*+ PARALLEL(8) */
    article_title,
    COUNT(DISTINCT path_id) as path_count,
    COUNT(*) as occurrence_count
FROM 
    WIKI_COPY.WIKI_PATH_NODES_PARTITIONED
GROUP BY 
    article_title
ORDER BY 
    path_count DESC
FETCH FIRST 50 ROWS ONLY;

-- 3. Materialized Views for Complex Graph Analytics
-- Create materialized views to pre-compute expensive network metrics

-- Create materialized view for article metrics
CREATE MATERIALIZED VIEW WIKI_COPY.MV_ARTICLE_METRICS
BUILD IMMEDIATE
REFRESH COMPLETE ON DEMAND
ENABLE QUERY REWRITE
AS
SELECT 
    article_title,
    COUNT(DISTINCT path_id) as path_count,
    COUNT(*) as occurrence_count,
    AVG(step_number) as avg_position,
    STDDEV(step_number) as position_stddev,
    MIN(step_number) as min_position,
    MAX(step_number) as max_position
FROM 
    WIKI_COPY.WIKI_PATH_NODES
GROUP BY 
    article_title;

-- Create materialized view for article connections
CREATE MATERIALIZED VIEW WIKI_COPY.MV_ARTICLE_CONNECTIONS
BUILD IMMEDIATE
REFRESH COMPLETE ON DEMAND
ENABLE QUERY REWRITE
PARALLEL 8
AS
SELECT 
    n1.article_title as source,
    n2.article_title as target,
    COUNT(DISTINCT n1.path_id) as connection_count,
    MIN(n2.step_number - n1.step_number) as min_distance,
    AVG(n2.step_number - n1.step_number) as avg_distance
FROM 
    WIKI_COPY.WIKI_PATH_NODES n1
JOIN 
    WIKI_COPY.WIKI_PATH_NODES n2 
    ON n1.path_id = n2.path_id
    AND n2.step_number > n1.step_number
GROUP BY 
    n1.article_title, n2.article_title;

-- Create materialized view for path statistics
CREATE MATERIALIZED VIEW WIKI_COPY.MV_PATH_STATISTICS
BUILD IMMEDIATE
REFRESH COMPLETE ON DEMAND
ENABLE QUERY REWRITE
AS
SELECT 
    TO_CHAR(creation_date, 'YYYY-MM-DD') as date_key,
    COUNT(*) as path_count,
    ROUND(AVG(steps), 2) as avg_steps,
    MEDIAN(steps) as median_steps,
    STDDEV(steps) as stddev_steps,
    SUM(CASE WHEN succeeded = 1 THEN 1 ELSE 0 END) as successful_paths,
    ROUND(SUM(CASE WHEN succeeded = 1 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) as success_rate
FROM 
    WIKI_COPY.WIKI_PATHS
GROUP BY 
    TO_CHAR(creation_date, 'YYYY-MM-DD');

-- 4. Bitmap Indexes for High-Cardinality Data
-- Optimize for queries that filter on many distinct values

-- Create bitmap indexes on the partitioned tables
CREATE BITMAP INDEX WIKI_COPY.bmp_idx_paths_start_article ON WIKI_COPY.WIKI_PATHS_PARTITIONED(start_article) LOCAL;
CREATE BITMAP INDEX WIKI_COPY.bmp_idx_paths_end_article ON WIKI_COPY.WIKI_PATHS_PARTITIONED(end_article) LOCAL;
CREATE BITMAP INDEX WIKI_COPY.bmp_idx_nodes_article ON WIKI_COPY.WIKI_PATH_NODES_PARTITIONED(article_title) LOCAL;

-- 5. Result Cache for Repeated Query Patterns
-- Use result cache to store query results in memory for repeated access

-- Query using result cache
SELECT /*+ RESULT_CACHE */
    article_title,
    COUNT(DISTINCT path_id) as appearing_in_paths,
    COUNT(*) as total_occurrences
FROM 
    WIKI_COPY.WIKI_PATH_NODES
WHERE 
    article_title IN (
        SELECT article_title 
        FROM WIKI_COPY.WIKI_PATH_NODES 
        GROUP BY article_title 
        HAVING COUNT(*) > 100
    )
GROUP BY 
    article_title
ORDER BY 
    appearing_in_paths DESC;

-- 6. Dynamic Sampling for Query Optimization
-- Use dynamic sampling for better execution plans on large tables

-- Query with dynamic sampling hint
SELECT /*+ DYNAMIC_SAMPLING(p 10) DYNAMIC_SAMPLING(n 10) */
    p.end_article,
    COUNT(*) as path_count,
    ROUND(AVG(p.steps), 2) as avg_steps
FROM 
    WIKI_COPY.WIKI_PATHS p
JOIN 
    WIKI_COPY.WIKI_PATH_NODES n ON p.path_id = n.path_id
WHERE 
    n.article_title = 'Philosophy'
    AND p.end_article != 'Philosophy'
GROUP BY 
    p.end_article
ORDER BY 
    path_count DESC
FETCH FIRST 20 ROWS ONLY;

-- 7. Approximate Count Distinct for Large Datasets
-- Use approximation for faster distinct counts on large datasets

-- Query using approx_count_distinct for higher performance
SELECT 
    APPROX_COUNT_DISTINCT(article_title) as approx_unique_articles,
    COUNT(*) as total_nodes
FROM 
    WIKI_COPY.WIKI_PATH_NODES;

-- 8. SQL Model Clause for Complex Analysis
-- Use SQL model clause for advanced analytical processing

-- Path trend analysis using SQL model clause
SELECT * FROM (
    SELECT 
        TO_CHAR(creation_date, 'YYYY-MM-DD') as day,
        COUNT(*) as path_count,
        AVG(steps) as avg_steps,
        SUM(CASE WHEN succeeded = 1 THEN 1 ELSE 0 END) as successful_paths
    FROM 
        WIKI_COPY.WIKI_PATHS
    GROUP BY 
        TO_CHAR(creation_date, 'YYYY-MM-DD')
)
MODEL
    PARTITION BY ()
    DIMENSION BY (day)
    MEASURES (
        path_count, 
        avg_steps, 
        successful_paths,
        0 as predicted_paths,
        0 as trend_indicator
    )
    RULES (
        predicted_paths[FOR day IN (SELECT DISTINCT day FROM WIKI_COPY.MV_PATH_STATISTICS ORDER BY day)]
            = CASE 
                WHEN day != FIRST_VALUE(day) IGNORE NULLS OVER (ORDER BY day) 
                THEN ROUND(AVG(path_count) OVER (ORDER BY day ROWS BETWEEN 3 PRECEDING AND 1 PRECEDING))
                ELSE path_count
              END,
              
        trend_indicator[ANY] = 
            CASE 
                WHEN path_count > predicted_paths THEN 1  -- Upward trend
                WHEN path_count < predicted_paths THEN -1 -- Downward trend
                ELSE 0                                    -- Stable
            END
    )
ORDER BY day;

-- 9. Memory-Optimized Analytics for Large Datasets
-- In-memory analytics optimization for faster processing

-- Enable in-memory analytics (requires proper DB configuration)
-- ALTER TABLE WIKI_COPY.WIKI_PATHS INMEMORY;
-- ALTER TABLE WIKI_COPY.WIKI_PATH_NODES INMEMORY;

-- Query using in-memory optimizations
SELECT /*+ INMEMORY */
    COUNT(*) as total_paths,
    SUM(CASE WHEN succeeded = 1 THEN 1 ELSE 0 END) as successful_paths,
    ROUND(AVG(steps), 2) as avg_steps,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY steps) as median_steps,
    STDDEV(steps) as stddev_steps
FROM 
    WIKI_COPY.WIKI_PATHS;

-- 10. Scalable Partition Pruning
-- Demonstrate partition pruning for efficient querying

-- Query that benefits from partition pruning
EXPLAIN PLAN FOR
SELECT 
    COUNT(*) as paths_count,
    AVG(steps) as avg_path_length
FROM 
    WIKI_COPY.WIKI_PATHS_PARTITIONED
WHERE 
    creation_date BETWEEN TO_DATE('2023-06-01', 'YYYY-MM-DD') AND TO_DATE('2023-09-30', 'YYYY-MM-DD');

-- Show the execution plan (displays partition pruning)
SELECT * FROM TABLE(DBMS_XPLAN.DISPLAY);

-- 11. Function-Based Indexes for Advanced Processing
-- Create function-based indexes to optimize complex filters

-- Function-based index for article categorization
CREATE INDEX WIKI_COPY.idx_article_category ON WIKI_COPY.WIKI_PATH_NODES_PARTITIONED
(
    CASE
        WHEN LOWER(article_title) LIKE '%history%' THEN 'History'
        WHEN LOWER(article_title) LIKE '%science%' THEN 'Science'
        WHEN LOWER(article_title) LIKE '%art%' THEN 'Arts'
        WHEN LOWER(article_title) LIKE '%math%' THEN 'Mathematics'
        WHEN LOWER(article_title) LIKE '%philo%' THEN 'Philosophy'
        WHEN LOWER(article_title) LIKE '%computer%' THEN 'Technology'
        WHEN LOWER(article_title) LIKE '%tech%' THEN 'Technology'
        WHEN LOWER(article_title) LIKE '%biology%' THEN 'Biology'
        WHEN LOWER(article_title) LIKE '%physics%' THEN 'Physics'
        WHEN LOWER(article_title) LIKE '%chem%' THEN 'Chemistry'
        WHEN LOWER(article_title) LIKE '%geo%' THEN 'Geography'
        WHEN LOWER(article_title) LIKE '%polit%' THEN 'Politics'
        WHEN LOWER(article_title) LIKE '%econ%' THEN 'Economics'
        WHEN LOWER(article_title) LIKE '%sport%' THEN 'Sports'
        WHEN LOWER(article_title) LIKE '%football%' THEN 'Sports'
        WHEN LOWER(article_title) LIKE '%music%' THEN 'Music'
        WHEN LOWER(article_title) LIKE '%film%' OR LOWER(article_title) LIKE '%movie%' THEN 'Film'
        ELSE 'Uncategorized'
    END
) LOCAL;

-- Query using function-based index
SELECT 
    CASE
        WHEN LOWER(article_title) LIKE '%history%' THEN 'History'
        WHEN LOWER(article_title) LIKE '%science%' THEN 'Science'
        WHEN LOWER(article_title) LIKE '%art%' THEN 'Arts'
        WHEN LOWER(article_title) LIKE '%math%' THEN 'Mathematics'
        WHEN LOWER(article_title) LIKE '%philo%' THEN 'Philosophy'
        WHEN LOWER(article_title) LIKE '%computer%' THEN 'Technology'
        WHEN LOWER(article_title) LIKE '%tech%' THEN 'Technology'
        WHEN LOWER(article_title) LIKE '%biology%' THEN 'Biology'
        WHEN LOWER(article_title) LIKE '%physics%' THEN 'Physics'
        WHEN LOWER(article_title) LIKE '%chem%' THEN 'Chemistry'
        WHEN LOWER(article_title) LIKE '%geo%' THEN 'Geography'
        WHEN LOWER(article_title) LIKE '%polit%' THEN 'Politics'
        WHEN LOWER(article_title) LIKE '%econ%' THEN 'Economics'
        WHEN LOWER(article_title) LIKE '%sport%' THEN 'Sports'
        WHEN LOWER(article_title) LIKE '%football%' THEN 'Sports'
        WHEN LOWER(article_title) LIKE '%music%' THEN 'Music'
        WHEN LOWER(article_title) LIKE '%film%' OR LOWER(article_title) LIKE '%movie%' THEN 'Film'
        ELSE 'Uncategorized'
    END as category,
    COUNT(DISTINCT article_title) as article_count,
    COUNT(DISTINCT path_id) as path_count
FROM 
    WIKI_COPY.WIKI_PATH_NODES_PARTITIONED
GROUP BY 
    CASE
        WHEN LOWER(article_title) LIKE '%history%' THEN 'History'
        WHEN LOWER(article_title) LIKE '%science%' THEN 'Science'
        WHEN LOWER(article_title) LIKE '%art%' THEN 'Arts'
        WHEN LOWER(article_title) LIKE '%math%' THEN 'Mathematics'
        WHEN LOWER(article_title) LIKE '%philo%' THEN 'Philosophy'
        WHEN LOWER(article_title) LIKE '%computer%' THEN 'Technology'
        WHEN LOWER(article_title) LIKE '%tech%' THEN 'Technology'
        WHEN LOWER(article_title) LIKE '%biology%' THEN 'Biology'
        WHEN LOWER(article_title) LIKE '%physics%' THEN 'Physics'
        WHEN LOWER(article_title) LIKE '%chem%' THEN 'Chemistry'
        WHEN LOWER(article_title) LIKE '%geo%' THEN 'Geography'
        WHEN LOWER(article_title) LIKE '%polit%' THEN 'Politics'
        WHEN LOWER(article_title) LIKE '%econ%' THEN 'Economics'
        WHEN LOWER(article_title) LIKE '%sport%' THEN 'Sports'
        WHEN LOWER(article_title) LIKE '%football%' THEN 'Sports'
        WHEN LOWER(article_title) LIKE '%music%' THEN 'Music'
        WHEN LOWER(article_title) LIKE '%film%' OR LOWER(article_title) LIKE '%movie%' THEN 'Film'
        ELSE 'Uncategorized'
    END
ORDER BY 
    path_count DESC;

-- 12. Advanced Optimizer Directives for Complex Graph Queries
-- Optimize complex joins with specialized hints

-- Optimized path connection query with join order hints
SELECT /*+ LEADING(n1 n2) USE_HASH(n2) PARALLEL(8) */
    n1.article_title as source,
    n2.article_title as target,
    COUNT(DISTINCT n1.path_id) as connection_count
FROM 
    WIKI_COPY.WIKI_PATH_NODES n1
JOIN 
    WIKI_COPY.WIKI_PATH_NODES n2 
    ON n1.path_id = n2.path_id
    AND n2.step_number = n1.step_number + 1
WHERE
    n1.article_title IN (
        SELECT article_title FROM WIKI_COPY.MV_ARTICLE_METRICS
        WHERE path_count > 50
    )
GROUP BY 
    n1.article_title, n2.article_title
HAVING
    COUNT(DISTINCT n1.path_id) > 5
ORDER BY 
    connection_count DESC; 