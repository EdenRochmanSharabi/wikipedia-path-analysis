-- Basic Path Analysis (For WIKI_COPY schema)
-- This file contains SQL queries for analyzing Wikipedia paths

-- 1. Count total paths and articles
SELECT 
    COUNT(*) as total_paths,
    (SELECT COUNT(DISTINCT article_title) FROM WIKI_COPY.WIKI_PATH_NODES) as total_articles,
    (SELECT COUNT(*) FROM WIKI_COPY.WIKI_PATH_NODES) as total_nodes
FROM WIKI_COPY.WIKI_PATHS;

-- 2. Path length distribution 
SELECT 
    steps, 
    COUNT(*) as path_count,
    ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM WIKI_COPY.WIKI_PATHS), 2) as percentage
FROM 
    WIKI_COPY.WIKI_PATHS
GROUP BY 
    steps
ORDER BY 
    steps;

-- 3. Top 20 most common starting articles
SELECT 
    start_article, 
    COUNT(*) as path_count,
    ROUND(AVG(steps), 2) as avg_path_length,
    MIN(steps) as min_path_length,
    MAX(steps) as max_path_length
FROM 
    WIKI_COPY.WIKI_PATHS
GROUP BY 
    start_article
ORDER BY 
    path_count DESC
FETCH FIRST 20 ROWS ONLY;

-- 4. Top 20 most common ending articles
SELECT 
    end_article, 
    COUNT(*) as path_count,
    ROUND(AVG(steps), 2) as avg_path_length,
    SUM(CASE WHEN succeeded = 1 THEN 1 ELSE 0 END) as successful_paths,
    ROUND(SUM(CASE WHEN succeeded = 1 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) as success_rate
FROM 
    WIKI_COPY.WIKI_PATHS
GROUP BY 
    end_article
ORDER BY 
    path_count DESC
FETCH FIRST 20 ROWS ONLY;

-- 5. Most common articles appearing in paths overall
SELECT 
    article_title, 
    COUNT(DISTINCT path_id) as appears_in_paths,
    COUNT(*) as total_occurrences,
    ROUND(AVG(step_number), 2) as avg_position
FROM 
    WIKI_COPY.WIKI_PATH_NODES
GROUP BY 
    article_title
ORDER BY 
    appears_in_paths DESC
FETCH FIRST 30 ROWS ONLY;

-- 6. Articles that most commonly lead to Philosophy
WITH philosophy_paths AS (
    SELECT path_id
    FROM WIKI_COPY.WIKI_PATHS
    WHERE end_article = 'Philosophy'
)
SELECT 
    n.article_title,
    COUNT(DISTINCT n.path_id) as path_count
FROM 
    WIKI_COPY.WIKI_PATH_NODES n
JOIN
    philosophy_paths p ON n.path_id = p.path_id
WHERE
    n.article_title != 'Philosophy'
GROUP BY
    n.article_title
ORDER BY
    path_count DESC
FETCH FIRST 20 ROWS ONLY;

-- 7. Common path patterns (article pairs that frequently appear together)
WITH article_pairs AS (
    SELECT 
        n1.path_id,
        n1.article_title as article1,
        n2.article_title as article2
    FROM 
        WIKI_COPY.WIKI_PATH_NODES n1
    JOIN 
        WIKI_COPY.WIKI_PATH_NODES n2 
        ON n1.path_id = n2.path_id
        AND n1.step_number < n2.step_number
        AND n2.step_number = n1.step_number + 1
)
SELECT 
    article1,
    article2,
    COUNT(*) as pair_count
FROM 
    article_pairs
GROUP BY 
    article1, article2
ORDER BY 
    pair_count DESC
FETCH FIRST 30 ROWS ONLY;

-- 8. Path success rate by time period (using creation_date)
SELECT 
    TO_CHAR(creation_date, 'YYYY-MM-DD') as creation_day,
    COUNT(*) as total_paths,
    SUM(CASE WHEN succeeded = 1 THEN 1 ELSE 0 END) as successful_paths,
    ROUND(SUM(CASE WHEN succeeded = 1 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) as success_rate,
    ROUND(AVG(steps), 2) as avg_path_length
FROM 
    WIKI_COPY.WIKI_PATHS
GROUP BY 
    TO_CHAR(creation_date, 'YYYY-MM-DD')
ORDER BY 
    creation_day; 