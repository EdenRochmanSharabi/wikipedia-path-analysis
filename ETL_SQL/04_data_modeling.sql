-- Logical Data Modeling for Wikipedia Network Analysis
-- This file contains SQL queries that demonstrate advanced data modeling techniques for graph data

-- 1. Star Schema Transformation
-- Transform the graph data into a dimensional model for analytical queries

-- Dimension: Article
CREATE OR REPLACE VIEW WIKI_COPY.DIM_ARTICLE AS
SELECT 
    article_title as article_id,
    article_title as article_name,
    REGEXP_SUBSTR(article_title, '^[A-Za-z]+') as first_word,
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
    END as inferred_category,
    -- Popularity metrics
    (SELECT COUNT(*) FROM WIKI_COPY.WIKI_PATH_NODES WHERE article_title = a.article_title) as occurrence_count,
    (SELECT COUNT(DISTINCT path_id) FROM WIKI_COPY.WIKI_PATH_NODES WHERE article_title = a.article_title) as path_count
FROM 
    (SELECT DISTINCT article_title FROM WIKI_COPY.WIKI_PATH_NODES) a;

-- Dimension: Date
CREATE OR REPLACE VIEW WIKI_COPY.DIM_DATE AS
SELECT DISTINCT
    TO_CHAR(creation_date, 'YYYYMMDD') as date_id,
    creation_date as full_date,
    TO_CHAR(creation_date, 'YYYY-MM-DD') as date_string,
    EXTRACT(YEAR FROM creation_date) as year,
    EXTRACT(MONTH FROM creation_date) as month,
    EXTRACT(DAY FROM creation_date) as day,
    TO_CHAR(creation_date, 'Month') as month_name,
    TO_CHAR(creation_date, 'Day') as day_name
FROM 
    WIKI_COPY.WIKI_PATHS;

-- Dimension: Path Type
CREATE OR REPLACE VIEW WIKI_COPY.DIM_PATH_TYPE AS
SELECT DISTINCT
    CASE 
        WHEN steps <= 5 THEN 'S'
        WHEN steps <= 10 THEN 'M'
        WHEN steps <= 15 THEN 'L'
        ELSE 'XL'
    END || '_' || 
    CASE 
        WHEN succeeded = 1 THEN 'SUCCESS'
        ELSE 'FAIL'
    END as path_type_id,
    CASE 
        WHEN steps <= 5 THEN 'Short'
        WHEN steps <= 10 THEN 'Medium'
        WHEN steps <= 15 THEN 'Long'
        ELSE 'Extra Long'
    END as length_category,
    CASE 
        WHEN succeeded = 1 THEN 'Successful'
        ELSE 'Failed'
    END as success_status,
    steps as path_length,
    succeeded as is_successful
FROM 
    WIKI_COPY.WIKI_PATHS;

-- Fact: Path Summary
CREATE OR REPLACE VIEW WIKI_COPY.FACT_PATH_SUMMARY AS
SELECT 
    p.path_id,
    TO_CHAR(p.creation_date, 'YYYYMMDD') as date_id,
    p.start_article as start_article_id,
    p.end_article as end_article_id,
    CASE 
        WHEN p.steps <= 5 THEN 'S'
        WHEN p.steps <= 10 THEN 'M'
        WHEN p.steps <= 15 THEN 'L'
        ELSE 'XL'
    END || '_' || 
    CASE 
        WHEN p.succeeded = 1 THEN 'SUCCESS'
        ELSE 'FAIL'
    END as path_type_id,
    p.steps as path_length,
    p.succeeded as is_successful,
    -- Path metrics
    (SELECT COUNT(*) FROM WIKI_COPY.WIKI_PATH_NODES WHERE path_id = p.path_id) as node_count,
    (SELECT COUNT(DISTINCT article_title) FROM WIKI_COPY.WIKI_PATH_NODES WHERE path_id = p.path_id) as unique_article_count
FROM 
    WIKI_COPY.WIKI_PATHS p;

-- Fact: Article Network
CREATE OR REPLACE VIEW WIKI_COPY.FACT_ARTICLE_NETWORK AS
SELECT 
    n1.article_title as source_article_id,
    n2.article_title as target_article_id,
    COUNT(DISTINCT n1.path_id) as connection_count,
    MIN(n2.step_number - n1.step_number) as min_distance,
    MAX(n2.step_number - n1.step_number) as max_distance,
    AVG(n2.step_number - n1.step_number) as avg_distance
FROM 
    WIKI_COPY.WIKI_PATH_NODES n1
JOIN 
    WIKI_COPY.WIKI_PATH_NODES n2 
    ON n1.path_id = n2.path_id
    AND n2.step_number > n1.step_number
GROUP BY 
    n1.article_title, n2.article_title;

-- 2. Graph Model Optimization
-- Create graph-optimized views for network analysis algorithms

-- Adjacency List Representation
CREATE OR REPLACE VIEW WIKI_COPY.GRAPH_ADJACENCY_LIST AS
WITH direct_connections AS (
    SELECT 
        n1.article_title as source,
        n2.article_title as target,
        COUNT(DISTINCT n1.path_id) as weight
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
    LISTAGG(target || ':' || weight, ',') WITHIN GROUP (ORDER BY weight DESC) as adjacent_nodes
FROM
    direct_connections
GROUP BY
    source;

-- Edge List for Graph Processing
CREATE OR REPLACE VIEW WIKI_COPY.GRAPH_EDGE_LIST AS
SELECT 
    n1.article_title as source,
    n2.article_title as target,
    COUNT(DISTINCT n1.path_id) as weight,
    MIN(n2.step_number - n1.step_number) as min_distance,
    AVG(n2.step_number - n1.step_number) as avg_distance
FROM 
    WIKI_COPY.WIKI_PATH_NODES n1
JOIN 
    WIKI_COPY.WIKI_PATH_NODES n2 
    ON n1.path_id = n2.path_id
    AND n2.step_number = n1.step_number + 1
GROUP BY 
    n1.article_title, n2.article_title;

-- Node Properties for Graph Analysis
CREATE OR REPLACE VIEW WIKI_COPY.GRAPH_NODE_PROPERTIES AS
WITH node_stats AS (
    SELECT 
        article_title,
        COUNT(DISTINCT path_id) as path_count,
        COUNT(*) as occurrence_count,
        AVG(step_number) as avg_position,
        STDDEV(step_number) as position_stddev
    FROM 
        WIKI_COPY.WIKI_PATH_NODES
    GROUP BY 
        article_title
),
outgoing AS (
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
    ns.article_title as node_id,
    ns.path_count,
    ns.occurrence_count,
    ROUND(ns.avg_position, 2) as avg_position,
    ROUND(ns.position_stddev, 2) as position_stddev,
    NVL(o.outgoing_count, 0) as out_degree,
    NVL(i.incoming_count, 0) as in_degree,
    NVL(o.outgoing_count, 0) + NVL(i.incoming_count, 0) as degree,
    -- PageRank approximation (simplified)
    ROUND(ns.path_count * (1 + NVL(i.incoming_count, 0) * 0.5) / 
          (1 + NVL(o.outgoing_count, 0) * 0.25), 2) as pagerank_estimate
FROM 
    node_stats ns
LEFT JOIN
    outgoing o ON ns.article_title = o.article_title  
LEFT JOIN
    incoming i ON ns.article_title = i.article_title;

-- 3. Temporal Graph Model
-- Track network evolution over time

CREATE OR REPLACE VIEW WIKI_COPY.TEMPORAL_GRAPH_SNAPSHOT AS
WITH time_periods AS (
    SELECT 
        TO_CHAR(creation_date, 'YYYY-MM-DD') as period,
        path_id
    FROM 
        WIKI_COPY.WIKI_PATHS
),
temporal_edges AS (
    SELECT 
        tp.period,
        n1.article_title as source,
        n2.article_title as target,
        COUNT(DISTINCT n1.path_id) as weight
    FROM 
        WIKI_COPY.WIKI_PATH_NODES n1
    JOIN 
        WIKI_COPY.WIKI_PATH_NODES n2 
        ON n1.path_id = n2.path_id
        AND n2.step_number = n1.step_number + 1
    JOIN
        time_periods tp ON n1.path_id = tp.path_id
    GROUP BY 
        tp.period, n1.article_title, n2.article_title
)
SELECT 
    period, 
    source, 
    target, 
    weight,
    -- Cumulative sum of weights over time
    SUM(weight) OVER (
        PARTITION BY source, target 
        ORDER BY period 
        ROWS UNBOUNDED PRECEDING
    ) as cumulative_weight
FROM 
    temporal_edges
ORDER BY 
    period, source, target;

-- 4. Hierarchical Clustering Model
-- Group articles by similarity in network position

CREATE OR REPLACE VIEW WIKI_COPY.HIERARCHICAL_ARTICLE_CLUSTERS AS
WITH article_features AS (
    SELECT 
        article_title,
        AVG(step_number) as avg_position,
        STDDEV(step_number) as position_stddev,
        COUNT(DISTINCT path_id) as path_count,
        MIN(step_number) as min_position,
        MAX(step_number) as max_position
    FROM 
        WIKI_COPY.WIKI_PATH_NODES
    GROUP BY 
        article_title
    HAVING
        COUNT(DISTINCT path_id) >= 5  -- Minimum threshold for meaningful clustering
),
position_clusters AS (
    SELECT 
        article_title,
        NTILE(5) OVER (ORDER BY avg_position) as position_cluster,
        NTILE(5) OVER (ORDER BY position_stddev) as variability_cluster,
        NTILE(5) OVER (ORDER BY path_count) as popularity_cluster
    FROM 
        article_features
),
cluster_mapping AS (
    SELECT
        CASE position_cluster
            WHEN 1 THEN 'Very Early'
            WHEN 2 THEN 'Early'
            WHEN 3 THEN 'Middle'
            WHEN 4 THEN 'Late'
            WHEN 5 THEN 'Very Late'
        END as position_category,
        CASE variability_cluster
            WHEN 1 THEN 'Very Stable'
            WHEN 2 THEN 'Stable'
            WHEN 3 THEN 'Moderate'
            WHEN 4 THEN 'Variable'
            WHEN 5 THEN 'Highly Variable'
        END as variability_category,
        CASE popularity_cluster
            WHEN 1 THEN 'Very Rare'
            WHEN 2 THEN 'Uncommon'
            WHEN 3 THEN 'Moderate'
            WHEN 4 THEN 'Popular'
            WHEN 5 THEN 'Very Popular'
        END as popularity_category
    FROM
        (SELECT DISTINCT position_cluster, variability_cluster, popularity_cluster FROM position_clusters)
)
SELECT 
    pc.article_title,
    pc.position_cluster,
    pc.variability_cluster,
    pc.popularity_cluster,
    CASE pc.position_cluster
        WHEN 1 THEN 'Very Early'
        WHEN 2 THEN 'Early'
        WHEN 3 THEN 'Middle'
        WHEN 4 THEN 'Late'
        WHEN 5 THEN 'Very Late'
    END as position_category,
    CASE pc.variability_cluster
        WHEN 1 THEN 'Very Stable'
        WHEN 2 THEN 'Stable'
        WHEN 3 THEN 'Moderate'
        WHEN 4 THEN 'Variable'
        WHEN 5 THEN 'Highly Variable'
    END as variability_category,
    CASE pc.popularity_cluster
        WHEN 1 THEN 'Very Rare'
        WHEN 2 THEN 'Uncommon'
        WHEN 3 THEN 'Moderate'
        WHEN 4 THEN 'Popular'
        WHEN 5 THEN 'Very Popular'
    END as popularity_category,
    -- Composite cluster identifier
    pc.position_cluster || '-' || pc.variability_cluster || '-' || pc.popularity_cluster as cluster_id,
    -- Hierarchical cluster levels
    pc.position_cluster as level1_cluster,
    pc.position_cluster || '-' || pc.variability_cluster as level2_cluster,
    pc.position_cluster || '-' || pc.variability_cluster || '-' || pc.popularity_cluster as level3_cluster
FROM 
    position_clusters pc;

-- 5. Community Detection Model
-- Identify densely connected article communities 

CREATE OR REPLACE VIEW WIKI_COPY.ARTICLE_COMMUNITIES AS
WITH article_connections AS (
    SELECT 
        n1.article_title as source,
        n2.article_title as target,
        COUNT(DISTINCT n1.path_id) as connection_strength
    FROM 
        WIKI_COPY.WIKI_PATH_NODES n1
    JOIN 
        WIKI_COPY.WIKI_PATH_NODES n2 
        ON n1.path_id = n2.path_id
        AND n2.step_number = n1.step_number + 1
    GROUP BY 
        n1.article_title, n2.article_title
),
connection_matrix AS (
    SELECT 
        source, 
        target, 
        connection_strength,
        -- Normalized connection strength
        connection_strength / (
            SELECT MAX(connection_strength) FROM article_connections
        ) as norm_strength
    FROM 
        article_connections
),
community_seeds AS (
    -- Identify potential community core articles
    SELECT 
        source as article,
        SUM(norm_strength) as connectivity_score
    FROM 
        connection_matrix
    GROUP BY 
        source
    ORDER BY 
        connectivity_score DESC
    FETCH FIRST 20 ROWS ONLY
),
community_assignment AS (
    -- Assign each article to its most strongly connected community
    SELECT 
        cm.target as article,
        cs.article as community_seed,
        SUM(cm.norm_strength) as connection_to_community
    FROM 
        connection_matrix cm
    JOIN 
        community_seeds cs ON cm.source = cs.article
    GROUP BY 
        cm.target, cs.article
),
best_community AS (
    -- Select the strongest community for each article
    SELECT 
        article,
        MAX(connection_to_community) as strongest_connection
    FROM 
        community_assignment
    GROUP BY 
        article
)
SELECT 
    ca.article,
    ca.community_seed,
    -- Determine the strength of community membership
    ca.connection_to_community,
    ca.connection_to_community / bc.strongest_connection as community_membership_strength,
    CASE 
        WHEN ca.connection_to_community / bc.strongest_connection >= 0.8 THEN 'Core Member'
        WHEN ca.connection_to_community / bc.strongest_connection >= 0.5 THEN 'Strong Member'
        WHEN ca.connection_to_community / bc.strongest_connection >= 0.3 THEN 'Member'
        ELSE 'Peripheral'
    END as membership_type
FROM 
    community_assignment ca
JOIN 
    best_community bc ON ca.article = bc.article 
                      AND ca.connection_to_community = bc.strongest_connection
ORDER BY 
    ca.community_seed, 
    ca.connection_to_community DESC;

-- 6. Path Pattern Analysis
-- Identify and classify common path patterns in the data

CREATE OR REPLACE VIEW WIKI_COPY.PATH_PATTERNS AS
WITH path_segments AS (
    -- Create 3-article path segments
    SELECT 
        n1.path_id,
        n1.article_title as article1,
        n2.article_title as article2,
        n3.article_title as article3,
        n1.step_number as segment_start
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
),
pattern_frequencies AS (
    -- Count segment frequencies
    SELECT 
        article1,
        article2,
        article3,
        COUNT(*) as pattern_count,
        COUNT(DISTINCT path_id) as path_count
    FROM 
        path_segments
    GROUP BY 
        article1, article2, article3
    HAVING 
        COUNT(*) >= 3  -- Minimum occurrence threshold
),
pattern_categories AS (
    -- Classify patterns
    SELECT 
        article1,
        article2,
        article3,
        pattern_count,
        path_count,
        CASE 
            WHEN article1 = article3 THEN 'Loop'
            ELSE 'Linear'
        END as pattern_type,
        -- Pattern uniqueness
        pattern_count / (
            SELECT SUM(pattern_count) FROM pattern_frequencies
        ) as frequency_ratio,
        -- Pattern significance
        NTILE(10) OVER (ORDER BY pattern_count DESC) as significance_decile
    FROM 
        pattern_frequencies
)
SELECT 
    article1,
    article2,
    article3,
    pattern_count,
    path_count,
    pattern_type,
    ROUND(frequency_ratio * 100, 4) as frequency_percentage,
    significance_decile,
    CASE 
        WHEN significance_decile = 1 THEN 'Very High'
        WHEN significance_decile <= 3 THEN 'High'
        WHEN significance_decile <= 7 THEN 'Medium'
        ELSE 'Low'
    END as significance_level,
    article1 || ' → ' || article2 || ' → ' || article3 as pattern_string
FROM 
    pattern_categories
ORDER BY 
    pattern_count DESC; 