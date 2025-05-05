-- Business Intelligence Dashboard Data Preparation
-- This file contains SQL queries to prepare data for executive and management dashboards

-- 1. Overall Network Health KPI Metrics
CREATE OR REPLACE VIEW WIKI_COPY.BI_OVERALL_METRICS AS
SELECT
    (SELECT COUNT(*) FROM WIKI_COPY.WIKI_PATHS) as total_paths,
    (SELECT COUNT(DISTINCT article_title) FROM WIKI_COPY.WIKI_PATH_NODES) as unique_articles,
    (SELECT COUNT(*) FROM WIKI_COPY.WIKI_PATH_NODES) as total_nodes,
    (SELECT ROUND(AVG(steps), 2) FROM WIKI_COPY.WIKI_PATHS) as avg_path_length,
    (SELECT ROUND(SUM(CASE WHEN succeeded = 1 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) 
     FROM WIKI_COPY.WIKI_PATHS) as overall_success_rate,
    (SELECT COUNT(DISTINCT source_article_id) FROM WIKI_COPY.FACT_ARTICLE_NETWORK) as connected_articles,
    (SELECT COUNT(*) FROM WIKI_COPY.FACT_ARTICLE_NETWORK) as total_connections,
    (SELECT ROUND(AVG(connection_count), 2) FROM WIKI_COPY.FACT_ARTICLE_NETWORK) as avg_connection_weight
FROM DUAL;

-- 2. Executive Summary - Daily Trends Dashboard
CREATE OR REPLACE VIEW WIKI_COPY.BI_DAILY_TRENDS AS
WITH daily_metrics AS (
    SELECT 
        TO_CHAR(creation_date, 'YYYY-MM-DD') as day,
        COUNT(*) as paths_collected,
        COUNT(DISTINCT start_article) as unique_sources,
        COUNT(DISTINCT end_article) as unique_destinations,
        ROUND(AVG(steps), 2) as avg_path_length,
        ROUND(STDDEV(steps), 2) as path_length_stddev,
        MIN(steps) as min_path_length,
        MAX(steps) as max_path_length,
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
    unique_sources,
    unique_destinations,
    avg_path_length,
    path_length_stddev,
    min_path_length,
    max_path_length,
    successful_paths,
    success_rate,
    -- 7-day moving averages for trend analysis
    ROUND(AVG(paths_collected) OVER (ORDER BY day ROWS BETWEEN 6 PRECEDING AND CURRENT ROW), 2) as ma7_paths,
    ROUND(AVG(success_rate) OVER (ORDER BY day ROWS BETWEEN 6 PRECEDING AND CURRENT ROW), 2) as ma7_success_rate,
    ROUND(AVG(avg_path_length) OVER (ORDER BY day ROWS BETWEEN 6 PRECEDING AND CURRENT ROW), 2) as ma7_path_length,
    -- Day-over-day changes
    paths_collected - LAG(paths_collected, 1, paths_collected) OVER (ORDER BY day) as path_count_change,
    ROUND(success_rate - LAG(success_rate, 1, success_rate) OVER (ORDER BY day), 2) as success_rate_change,
    -- Categorize day performance
    CASE
        WHEN success_rate > LAG(success_rate, 1, success_rate) OVER (ORDER BY day) AND
             paths_collected > LAG(paths_collected, 1, paths_collected) OVER (ORDER BY day)
            THEN 'Improving'
        WHEN success_rate < LAG(success_rate, 1, success_rate) OVER (ORDER BY day) AND
             paths_collected < LAG(paths_collected, 1, paths_collected) OVER (ORDER BY day)
            THEN 'Declining'
        WHEN success_rate > LAG(success_rate, 1, success_rate) OVER (ORDER BY day)
            THEN 'Mixed - Better Quality'
        WHEN paths_collected > LAG(paths_collected, 1, paths_collected) OVER (ORDER BY day)
            THEN 'Mixed - Better Volume'
        ELSE 'Stable'
    END as day_performance
FROM 
    daily_metrics
ORDER BY 
    day;

-- 3. Top Knowledge Domains by Article Count
CREATE OR REPLACE VIEW WIKI_COPY.BI_DOMAIN_DISTRIBUTION AS
WITH article_categories AS (
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
        END as domain,
        article_title
    FROM 
        (SELECT DISTINCT article_title FROM WIKI_COPY.WIKI_PATH_NODES)
)
SELECT 
    domain,
    COUNT(*) as article_count,
    ROUND(COUNT(*) * 100.0 / (SELECT COUNT(DISTINCT article_title) FROM WIKI_COPY.WIKI_PATH_NODES), 2) as percentage,
    (
        SELECT ROUND(AVG(steps), 2) 
        FROM WIKI_COPY.WIKI_PATHS p
        JOIN WIKI_COPY.WIKI_PATH_NODES n ON p.path_id = n.path_id AND n.step_number = 0
        WHERE n.article_title IN (SELECT article_title FROM article_categories WHERE domain = ac.domain)
    ) as avg_path_length,
    (
        SELECT ROUND(SUM(CASE WHEN succeeded = 1 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2)
        FROM WIKI_COPY.WIKI_PATHS p
        JOIN WIKI_COPY.WIKI_PATH_NODES n ON p.path_id = n.path_id AND n.step_number = 0
        WHERE n.article_title IN (SELECT article_title FROM article_categories WHERE domain = ac.domain)
    ) as success_rate
FROM 
    article_categories ac
GROUP BY 
    domain
ORDER BY 
    article_count DESC;

-- 4. Network Structure - Top Hub and Authority Articles
CREATE OR REPLACE VIEW WIKI_COPY.BI_TOP_ARTICLES AS
WITH centrality_metrics AS (
    SELECT 
        article_title,
        COUNT(DISTINCT path_id) as path_count,
        AVG(step_number) as avg_position,
        (
            SELECT COUNT(DISTINCT target_article_id) 
            FROM WIKI_COPY.FACT_ARTICLE_NETWORK 
            WHERE source_article_id = wpn.article_title
        ) as outgoing_links,
        (
            SELECT COUNT(DISTINCT source_article_id) 
            FROM WIKI_COPY.FACT_ARTICLE_NETWORK 
            WHERE target_article_id = wpn.article_title
        ) as incoming_links,
        (
            SELECT ROUND(SUM(connection_count), 2)
            FROM WIKI_COPY.FACT_ARTICLE_NETWORK 
            WHERE source_article_id = wpn.article_title
        ) as outgoing_weight,
        (
            SELECT ROUND(SUM(connection_count), 2)
            FROM WIKI_COPY.FACT_ARTICLE_NETWORK 
            WHERE target_article_id = wpn.article_title
        ) as incoming_weight
    FROM 
        WIKI_COPY.WIKI_PATH_NODES wpn
    GROUP BY 
        article_title
    HAVING 
        COUNT(DISTINCT path_id) >= 5
),
article_scores AS (
    SELECT
        article_title,
        path_count,
        outgoing_links,
        incoming_links,
        outgoing_weight,
        incoming_weight,
        -- Authority score (based on incoming connections)
        (incoming_links * 2 + incoming_weight + path_count) / 
            (SELECT MAX(incoming_links * 2 + incoming_weight + path_count) FROM centrality_metrics) * 100 as authority_score,
        -- Hub score (based on outgoing connections)
        (outgoing_links * 2 + outgoing_weight + path_count) / 
            (SELECT MAX(outgoing_links * 2 + outgoing_weight + path_count) FROM centrality_metrics) * 100 as hub_score,
        -- Overall importance score
        (incoming_links * 2 + incoming_weight + outgoing_links + outgoing_weight + path_count * 2) / 
            (SELECT MAX(incoming_links * 2 + incoming_weight + outgoing_links + outgoing_weight + path_count * 2) FROM centrality_metrics) * 100 as importance_score
    FROM
        centrality_metrics
)
SELECT
    article_title,
    ROUND(authority_score, 2) as authority_score,
    ROUND(hub_score, 2) as hub_score,
    ROUND(importance_score, 2) as importance_score,
    path_count,
    incoming_links,
    outgoing_links,
    CASE
        WHEN authority_score >= 75 AND hub_score >= 75 THEN 'Central Hub'
        WHEN authority_score >= 75 THEN 'Authority'
        WHEN hub_score >= 75 THEN 'Hub'
        WHEN importance_score >= 60 THEN 'Important'
        ELSE 'Regular'
    END as article_role
FROM
    article_scores
ORDER BY
    importance_score DESC
FETCH FIRST 100 ROWS ONLY;

-- 5. Path Success Factors Dashboard
CREATE OR REPLACE VIEW WIKI_COPY.BI_SUCCESS_FACTORS AS
WITH path_features AS (
    SELECT 
        p.path_id,
        p.succeeded,
        p.steps,
        p.start_article,
        p.end_article,
        (
            SELECT COUNT(DISTINCT path_id) 
            FROM WIKI_COPY.WIKI_PATH_NODES 
            WHERE article_title = p.start_article
        ) as start_article_popularity,
        (
            SELECT COUNT(DISTINCT path_id) 
            FROM WIKI_COPY.WIKI_PATH_NODES 
            WHERE article_title = p.end_article
        ) as end_article_popularity,
        (
            SELECT COUNT(DISTINCT n2.article_title)
            FROM WIKI_COPY.WIKI_PATH_NODES n1
            JOIN WIKI_COPY.WIKI_PATH_NODES n2 ON n1.path_id = p.path_id AND n2.path_id = p.path_id
            AND n2.step_number = n1.step_number + 1
        ) as unique_transitions,
        CASE
            WHEN EXISTS (
                SELECT 1 FROM WIKI_COPY.WIKI_PATH_NODES n1
                JOIN WIKI_COPY.WIKI_PATH_NODES n2 ON n1.path_id = p.path_id AND n2.path_id = p.path_id
                AND n1.article_title = n2.article_title AND n1.step_number < n2.step_number
            ) THEN 1
            ELSE 0
        END as has_loops
    FROM 
        WIKI_COPY.WIKI_PATHS p
),
success_rate_by_length AS (
    SELECT 
        steps,
        COUNT(*) as path_count,
        SUM(succeeded) as successful_count,
        ROUND(SUM(succeeded) * 100.0 / COUNT(*), 2) as success_rate
    FROM 
        path_features
    GROUP BY 
        steps
),
success_rate_by_popularity AS (
    SELECT 
        NTILE(10) OVER (ORDER BY start_article_popularity) as start_popularity_decile,
        NTILE(10) OVER (ORDER BY end_article_popularity) as end_popularity_decile,
        COUNT(*) as path_count,
        SUM(succeeded) as successful_paths,
        ROUND(SUM(succeeded) * 100.0 / COUNT(*), 2) as success_rate
    FROM 
        path_features
    GROUP BY 
        NTILE(10) OVER (ORDER BY start_article_popularity),
        NTILE(10) OVER (ORDER BY end_article_popularity)
),
loop_impact AS (
    SELECT 
        has_loops,
        COUNT(*) as path_count,
        SUM(succeeded) as successful_paths,
        ROUND(SUM(succeeded) * 100.0 / COUNT(*), 2) as success_rate,
        ROUND(AVG(steps), 2) as avg_path_length
    FROM 
        path_features
    GROUP BY 
        has_loops
)
SELECT 'Path Length' as factor_type, steps as factor_value, path_count, success_rate 
FROM success_rate_by_length
UNION ALL
SELECT 'Start Popularity Decile' as factor_type, start_popularity_decile as factor_value, path_count, success_rate
FROM success_rate_by_popularity
UNION ALL
SELECT 'End Popularity Decile' as factor_type, end_popularity_decile as factor_value, path_count, success_rate
FROM success_rate_by_popularity
UNION ALL 
SELECT 'Has Loops' as factor_type, has_loops as factor_value, path_count, success_rate
FROM loop_impact
ORDER BY factor_type, factor_value;

-- 6. Cross-Domain Navigation Analysis
CREATE OR REPLACE VIEW WIKI_COPY.BI_DOMAIN_NAVIGATION AS
WITH domain_paths AS (
    SELECT 
        p.path_id,
        CASE
            WHEN LOWER(n_start.article_title) LIKE '%history%' THEN 'History'
            WHEN LOWER(n_start.article_title) LIKE '%science%' THEN 'Science'
            WHEN LOWER(n_start.article_title) LIKE '%art%' THEN 'Arts'
            WHEN LOWER(n_start.article_title) LIKE '%math%' THEN 'Mathematics'
            WHEN LOWER(n_start.article_title) LIKE '%philo%' THEN 'Philosophy'
            WHEN LOWER(n_start.article_title) LIKE '%computer%' THEN 'Technology'
            WHEN LOWER(n_start.article_title) LIKE '%tech%' THEN 'Technology'
            WHEN LOWER(n_start.article_title) LIKE '%biology%' THEN 'Biology'
            WHEN LOWER(n_start.article_title) LIKE '%physics%' THEN 'Physics'
            WHEN LOWER(n_start.article_title) LIKE '%chem%' THEN 'Chemistry'
            WHEN LOWER(n_start.article_title) LIKE '%geo%' THEN 'Geography'
            WHEN LOWER(n_start.article_title) LIKE '%polit%' THEN 'Politics'
            WHEN LOWER(n_start.article_title) LIKE '%econ%' THEN 'Economics'
            WHEN LOWER(n_start.article_title) LIKE '%sport%' THEN 'Sports'
            WHEN LOWER(n_start.article_title) LIKE '%football%' THEN 'Sports'
            WHEN LOWER(n_start.article_title) LIKE '%music%' THEN 'Music'
            WHEN LOWER(n_start.article_title) LIKE '%film%' OR LOWER(n_start.article_title) LIKE '%movie%' THEN 'Film'
            ELSE 'Uncategorized'
        END as start_domain,
        CASE
            WHEN LOWER(n_end.article_title) LIKE '%history%' THEN 'History'
            WHEN LOWER(n_end.article_title) LIKE '%science%' THEN 'Science'
            WHEN LOWER(n_end.article_title) LIKE '%art%' THEN 'Arts'
            WHEN LOWER(n_end.article_title) LIKE '%math%' THEN 'Mathematics'
            WHEN LOWER(n_end.article_title) LIKE '%philo%' THEN 'Philosophy'
            WHEN LOWER(n_end.article_title) LIKE '%computer%' THEN 'Technology'
            WHEN LOWER(n_end.article_title) LIKE '%tech%' THEN 'Technology'
            WHEN LOWER(n_end.article_title) LIKE '%biology%' THEN 'Biology'
            WHEN LOWER(n_end.article_title) LIKE '%physics%' THEN 'Physics'
            WHEN LOWER(n_end.article_title) LIKE '%chem%' THEN 'Chemistry'
            WHEN LOWER(n_end.article_title) LIKE '%geo%' THEN 'Geography'
            WHEN LOWER(n_end.article_title) LIKE '%polit%' THEN 'Politics'
            WHEN LOWER(n_end.article_title) LIKE '%econ%' THEN 'Economics'
            WHEN LOWER(n_end.article_title) LIKE '%sport%' THEN 'Sports'
            WHEN LOWER(n_end.article_title) LIKE '%football%' THEN 'Sports'
            WHEN LOWER(n_end.article_title) LIKE '%music%' THEN 'Music'
            WHEN LOWER(n_end.article_title) LIKE '%film%' OR LOWER(n_end.article_title) LIKE '%movie%' THEN 'Film'
            ELSE 'Uncategorized'
        END as end_domain,
        p.succeeded,
        p.steps
    FROM 
        WIKI_COPY.WIKI_PATHS p
    JOIN 
        WIKI_COPY.WIKI_PATH_NODES n_start ON p.path_id = n_start.path_id AND n_start.step_number = 0
    JOIN 
        WIKI_COPY.WIKI_PATH_NODES n_end ON p.path_id = n_end.path_id AND n_end.step_number = (
            SELECT MAX(step_number) FROM WIKI_COPY.WIKI_PATH_NODES WHERE path_id = p.path_id
        )
)
SELECT 
    start_domain,
    end_domain,
    COUNT(*) as path_count,
    SUM(succeeded) as successful_paths,
    ROUND(SUM(succeeded) * 100.0 / COUNT(*), 2) as success_rate,
    ROUND(AVG(steps), 2) as avg_path_length,
    MIN(steps) as min_path_length,
    MAX(steps) as max_path_length,
    CASE 
        WHEN start_domain = end_domain THEN 'Within Domain'
        ELSE 'Cross Domain'
    END as path_type
FROM 
    domain_paths
GROUP BY 
    start_domain, end_domain
ORDER BY 
    path_count DESC;

-- 7. Network Growth Dashboard
CREATE OR REPLACE VIEW WIKI_COPY.BI_NETWORK_GROWTH AS
WITH monthly_growth AS (
    SELECT 
        TO_CHAR(creation_date, 'YYYY-MM') as month,
        COUNT(*) as new_paths,
        COUNT(DISTINCT start_article) as unique_start_articles,
        COUNT(DISTINCT end_article) as unique_end_articles,
        (
            SELECT COUNT(DISTINCT article_title) 
            FROM WIKI_COPY.WIKI_PATH_NODES n
            WHERE n.path_id IN (SELECT path_id FROM WIKI_COPY.WIKI_PATHS 
                              WHERE TO_CHAR(creation_date, 'YYYY-MM') = TO_CHAR(p.creation_date, 'YYYY-MM'))
        ) as unique_articles,
        (
            SELECT COUNT(*) 
            FROM WIKI_COPY.WIKI_PATH_NODES n
            WHERE n.path_id IN (SELECT path_id FROM WIKI_COPY.WIKI_PATHS 
                              WHERE TO_CHAR(creation_date, 'YYYY-MM') = TO_CHAR(p.creation_date, 'YYYY-MM'))
        ) as total_nodes
    FROM 
        WIKI_COPY.WIKI_PATHS p
    GROUP BY 
        TO_CHAR(creation_date, 'YYYY-MM')
),
cumulative_growth AS (
    SELECT 
        month,
        new_paths,
        unique_start_articles,
        unique_end_articles,
        unique_articles,
        total_nodes,
        SUM(new_paths) OVER (ORDER BY month) as cumulative_paths,
        SUM(unique_articles) OVER (ORDER BY month) as cumulative_articles_raw -- Will need deduplication
    FROM 
        monthly_growth
)
SELECT 
    month,
    new_paths,
    unique_articles,
    total_nodes,
    cumulative_paths,
    -- Calculate network density (ratio of actual connections to possible connections)
    ROUND(total_nodes * 100.0 / (unique_articles * unique_articles), 4) as network_density,
    -- Growth rates
    ROUND((new_paths - LAG(new_paths, 1, new_paths) OVER (ORDER BY month)) * 100.0 / 
          NULLIF(LAG(new_paths, 1, new_paths) OVER (ORDER BY month), 0), 2) as path_growth_rate,
    ROUND((unique_articles - LAG(unique_articles, 1, unique_articles) OVER (ORDER BY month)) * 100.0 / 
          NULLIF(LAG(unique_articles, 1, unique_articles) OVER (ORDER BY month), 0), 2) as article_growth_rate
FROM 
    cumulative_growth
ORDER BY 
    month;

-- 8. Knowledge Domain Clustering Effectiveness
CREATE OR REPLACE VIEW WIKI_COPY.BI_CLUSTERING_EFFECTIVENESS AS
WITH article_clusters AS (
    SELECT 
        article_title,
        cluster_id,
        level1_cluster,
        level2_cluster,
        level3_cluster,
        position_category,
        variability_category,
        popularity_category
    FROM 
        WIKI_COPY.HIERARCHICAL_ARTICLE_CLUSTERS
),
cluster_connections AS (
    SELECT 
        c1.level2_cluster as source_cluster,
        c2.level2_cluster as target_cluster,
        COUNT(*) as connection_count
    FROM 
        WIKI_COPY.WIKI_PATH_NODES n1
    JOIN 
        WIKI_COPY.WIKI_PATH_NODES n2 ON n1.path_id = n2.path_id AND n2.step_number = n1.step_number + 1
    JOIN 
        article_clusters c1 ON n1.article_title = c1.article_title
    JOIN 
        article_clusters c2 ON n2.article_title = c2.article_title
    GROUP BY 
        c1.level2_cluster, c2.level2_cluster
),
cluster_metrics AS (
    SELECT 
        level2_cluster as cluster_id,
        COUNT(DISTINCT article_title) as member_count,
        (
            SELECT COUNT(*) 
            FROM cluster_connections
            WHERE source_cluster = ac.level2_cluster AND target_cluster = ac.level2_cluster
        ) as internal_connections,
        (
            SELECT COUNT(*) 
            FROM cluster_connections
            WHERE source_cluster = ac.level2_cluster AND target_cluster != ac.level2_cluster
        ) as outgoing_connections,
        (
            SELECT COUNT(*) 
            FROM cluster_connections
            WHERE source_cluster != ac.level2_cluster AND target_cluster = ac.level2_cluster
        ) as incoming_connections
    FROM 
        article_clusters ac
    GROUP BY 
        level2_cluster
)
SELECT 
    cluster_id,
    member_count,
    internal_connections,
    outgoing_connections,
    incoming_connections,
    -- Clustering metrics
    ROUND(internal_connections * 100.0 / NULLIF(internal_connections + outgoing_connections, 0), 2) as cohesion_score,
    ROUND(incoming_connections * 100.0 / NULLIF(member_count, 0), 2) as attraction_score,
    ROUND(outgoing_connections * 100.0 / NULLIF(member_count, 0), 2) as expansion_score,
    -- Overall cluster quality score
    ROUND((internal_connections * 3.0 - outgoing_connections * 0.5 + incoming_connections * 1.0) /
          NULLIF(member_count, 0), 2) as quality_score,
    -- Cluster characterization
    CASE
        WHEN internal_connections > outgoing_connections AND internal_connections > incoming_connections
            THEN 'Isolated'
        WHEN outgoing_connections > internal_connections AND outgoing_connections > incoming_connections
            THEN 'Source'
        WHEN incoming_connections > internal_connections AND incoming_connections > outgoing_connections
            THEN 'Sink'
        ELSE 'Balanced'
    END as cluster_character
FROM 
    cluster_metrics
ORDER BY 
    quality_score DESC; 