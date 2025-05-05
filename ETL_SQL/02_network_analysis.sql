-- Network Analysis Queries for Wikipedia Paths
-- These queries analyze the graph structure of the Wikipedia navigation paths

-- 1. Identify most common "hub" articles (articles with many incoming and outgoing links)
WITH article_connections AS (
    -- Get outgoing connections (article followed by next article)
    SELECT 
        n1.article_title, 
        n2.article_title as next_article,
        COUNT(DISTINCT n1.path_id) as path_count
    FROM 
        WIKI_COPY.WIKI_PATH_NODES n1
    JOIN 
        WIKI_COPY.WIKI_PATH_NODES n2 
        ON n1.path_id = n2.path_id
        AND n2.step_number = n1.step_number + 1
    GROUP BY 
        n1.article_title, n2.article_title
),
outgoing_count AS (
    SELECT 
        article_title,
        COUNT(DISTINCT next_article) as outgoing_connections,
        SUM(path_count) as total_outgoing_paths
    FROM 
        article_connections
    GROUP BY 
        article_title
),
incoming_count AS (
    SELECT 
        next_article as article_title,
        COUNT(DISTINCT article_title) as incoming_connections,
        SUM(path_count) as total_incoming_paths
    FROM 
        article_connections
    GROUP BY 
        next_article
)
SELECT 
    COALESCE(o.article_title, i.article_title) as article,
    NVL(incoming_connections, 0) as incoming,
    NVL(outgoing_connections, 0) as outgoing,
    NVL(incoming_connections, 0) + NVL(outgoing_connections, 0) as total_connections,
    NVL(total_incoming_paths, 0) as incoming_path_count,
    NVL(total_outgoing_paths, 0) as outgoing_path_count
FROM 
    outgoing_count o
FULL OUTER JOIN 
    incoming_count i ON o.article_title = i.article_title
ORDER BY 
    total_connections DESC
FETCH FIRST 30 ROWS ONLY;

-- 2. Identify strongly connected paths (where connections happen more frequently)
WITH article_pairs AS (
    SELECT 
        n1.article_title as source,
        n2.article_title as target,
        COUNT(DISTINCT n1.path_id) as path_count
    FROM 
        WIKI_COPY.WIKI_PATH_NODES n1
    JOIN 
        WIKI_COPY.WIKI_PATH_NODES n2 
        ON n1.path_id = n2.path_id
        AND n2.step_number = n1.step_number + 1
    GROUP BY 
        n1.article_title, n2.article_title
)
SELECT 
    source,
    target,
    path_count,
    ROUND(path_count * 100.0 / (
        SELECT COUNT(DISTINCT path_id) FROM WIKI_COPY.WIKI_PATHS
    ), 2) as percentage_of_total_paths
FROM 
    article_pairs
WHERE 
    path_count > 10  -- Only strong connections
ORDER BY 
    path_count DESC;

-- 3. Identify bottleneck articles (articles that many paths must go through)
WITH path_positions AS (
    SELECT 
        article_title,
        COUNT(DISTINCT path_id) as appears_in_paths,
        ROUND(AVG(step_number), 2) as avg_position
    FROM 
        WIKI_COPY.WIKI_PATH_NODES
    GROUP BY 
        article_title
),
total_paths AS (
    SELECT COUNT(*) as count FROM WIKI_COPY.WIKI_PATHS
)
SELECT 
    article_title,
    appears_in_paths,
    ROUND(appears_in_paths * 100.0 / (SELECT count FROM total_paths), 2) as percentage_of_paths,
    avg_position
FROM 
    path_positions
WHERE 
    appears_in_paths > (SELECT count * 0.05 FROM total_paths)  -- Appears in more than 5% of paths
ORDER BY 
    percentage_of_paths DESC;

-- 4. Determine common path segments (sequences of 3+ articles that occur together frequently)
WITH three_article_segments AS (
    SELECT 
        n1.path_id,
        n1.article_title as article1,
        n2.article_title as article2,
        n3.article_title as article3
    FROM 
        WIKI_COPY.WIKI_PATH_NODES n1
    JOIN 
        WIKI_COPY.WIKI_PATH_NODES n2 
        ON n1.path_id = n2.path_id
        AND n2.step_number = n1.step_number + 1
    JOIN 
        WIKI_COPY.WIKI_PATH_NODES n3
        ON n2.path_id = n3.path_id
        AND n3.step_number = n2.step_number + 1
)
SELECT 
    article1,
    article2,
    article3,
    COUNT(*) as segment_count
FROM 
    three_article_segments
GROUP BY 
    article1, article2, article3
HAVING 
    COUNT(*) > 5  -- Occurs in at least 5 paths
ORDER BY 
    segment_count DESC
FETCH FIRST 20 ROWS ONLY;

-- 5. Identify circular references in the network
WITH circular_paths AS (
    SELECT 
        n1.path_id,
        n1.article_title,
        n1.step_number as first_occurrence,
        n2.step_number as second_occurrence
    FROM 
        WIKI_COPY.WIKI_PATH_NODES n1
    JOIN 
        WIKI_COPY.WIKI_PATH_NODES n2 
        ON n1.path_id = n2.path_id
        AND n1.article_title = n2.article_title
        AND n1.step_number < n2.step_number
)
SELECT 
    path_id,
    article_title,
    first_occurrence,
    second_occurrence,
    second_occurrence - first_occurrence as loop_length
FROM 
    circular_paths
ORDER BY 
    loop_length,
    path_id;

-- 6. Identify common "bridges" between domain categories
-- This looks for articles that commonly connect different subject domains
-- This relies on a heuristic to identify domain by the first word in article titles
WITH article_domain AS (
    SELECT 
        article_title,
        REGEXP_SUBSTR(article_title, '^[A-Za-z]+') as domain_indicator
    FROM 
        WIKI_COPY.WIKI_PATH_NODES
    WHERE 
        REGEXP_SUBSTR(article_title, '^[A-Za-z]+') IS NOT NULL
),
domain_transitions AS (
    SELECT 
        n1.path_id,
        n1.article_title as from_article,
        ad1.domain_indicator as from_domain,
        n2.article_title as to_article,
        ad2.domain_indicator as to_domain
    FROM 
        WIKI_COPY.WIKI_PATH_NODES n1
    JOIN 
        WIKI_COPY.WIKI_PATH_NODES n2 
        ON n1.path_id = n2.path_id
        AND n2.step_number = n1.step_number + 1
    JOIN 
        article_domain ad1 ON n1.article_title = ad1.article_title
    JOIN 
        article_domain ad2 ON n2.article_title = ad2.article_title
    WHERE 
        ad1.domain_indicator != ad2.domain_indicator
)
SELECT 
    from_domain,
    to_domain,
    from_article,
    to_article,
    COUNT(*) as transition_count
FROM 
    domain_transitions
GROUP BY 
    from_domain, to_domain, from_article, to_article
ORDER BY 
    transition_count DESC
FETCH FIRST 30 ROWS ONLY;

-- 7. Centrality analysis - find the most "central" articles in the graph
-- This is a simplified approximation of centrality in SQL
WITH article_occurrences AS (
    SELECT 
        article_title,
        COUNT(DISTINCT path_id) as path_count,
        AVG(step_number) as avg_position,
        MIN(step_number) as min_position,
        MAX(step_number) as max_position,
        STDDEV(step_number) as position_stddev
    FROM 
        WIKI_COPY.WIKI_PATH_NODES
    GROUP BY 
        article_title
),
total_paths AS (
    SELECT COUNT(*) as count FROM WIKI_COPY.WIKI_PATHS
)
SELECT 
    article_title,
    path_count,
    ROUND(path_count * 100.0 / (SELECT count FROM total_paths), 2) as path_percentage,
    ROUND(avg_position, 2) as avg_position,
    ROUND(position_stddev, 2) as position_stddev,
    -- Centrality approximation: high path coverage with middle-range positioning
    ROUND(path_count * 100.0 / (SELECT count FROM total_paths) / 
          (ABS(avg_position - 10) + 1), 2) as centrality_score
FROM 
    article_occurrences
WHERE 
    path_count > 5  -- Minimum threshold to avoid noise
ORDER BY 
    centrality_score DESC
FETCH FIRST 30 ROWS ONLY;

-- 8. Path structure complexity - how "branched" is the network from each article
WITH outgoing_branches AS (
    SELECT 
        n1.article_title,
        COUNT(DISTINCT n2.article_title) as distinct_next_articles
    FROM 
        WIKI_COPY.WIKI_PATH_NODES n1
    JOIN 
        WIKI_COPY.WIKI_PATH_NODES n2 
        ON n1.path_id = n2.path_id
        AND n2.step_number = n1.step_number + 1
    GROUP BY 
        n1.article_title
),
incoming_branches AS (
    SELECT 
        n2.article_title,
        COUNT(DISTINCT n1.article_title) as distinct_prev_articles
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
    NVL(distinct_next_articles, 0) as outgoing_branches,
    NVL(distinct_prev_articles, 0) as incoming_branches,
    NVL(distinct_next_articles, 0) + NVL(distinct_prev_articles, 0) as branching_factor
FROM 
    outgoing_branches o
FULL OUTER JOIN 
    incoming_branches i ON o.article_title = i.article_title
ORDER BY 
    branching_factor DESC
FETCH FIRST 30 ROWS ONLY; 