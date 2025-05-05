-- Advanced Statistical Analysis for Wikipedia Paths
-- This file contains SQL queries for performing statistical analysis on the Wikipedia path data

-- 1. Basic Statistical Measures for Path Length
WITH path_stats AS (
    SELECT 
        steps,
        COUNT(*) as frequency
    FROM 
        WIKI_COPY.WIKI_PATHS
    GROUP BY 
        steps
),
total_paths AS (
    SELECT 
        COUNT(*) as total,
        AVG(steps) as mean_steps,
        MEDIAN(steps) as median_steps,
        STDDEV(steps) as stddev_steps,
        PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY steps) as q1_steps,
        PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY steps) as q3_steps,
        MIN(steps) as min_steps,
        MAX(steps) as max_steps
    FROM 
        WIKI_COPY.WIKI_PATHS
)
SELECT 
    p.steps,
    p.frequency,
    ROUND(p.frequency * 100.0 / t.total, 2) as percentage,
    ROUND(p.frequency * 100.0 / SUM(p.frequency) OVER (), 2) as cumulative_percentage,
    CASE 
        WHEN p.steps < t.mean_steps - 2*t.stddev_steps THEN 'Extremely Short'
        WHEN p.steps < t.mean_steps - t.stddev_steps THEN 'Short'
        WHEN p.steps > t.mean_steps + t.stddev_steps THEN 'Long'
        WHEN p.steps > t.mean_steps + 2*t.stddev_steps THEN 'Extremely Long'
        ELSE 'Average'
    END as length_category,
    t.mean_steps,
    t.median_steps,
    t.stddev_steps,
    t.q1_steps,
    t.q3_steps,
    t.q3_steps - t.q1_steps as iqr_steps
FROM 
    path_stats p,
    total_paths t
ORDER BY 
    steps;

-- 2. Z-Score Analysis for Path Length Outliers
WITH path_stats AS (
    SELECT 
        path_id,
        steps,
        (SELECT AVG(steps) FROM WIKI_COPY.WIKI_PATHS) as mean_steps,
        (SELECT STDDEV(steps) FROM WIKI_COPY.WIKI_PATHS) as stddev_steps
    FROM 
        WIKI_COPY.WIKI_PATHS
)
SELECT 
    path_id,
    start_article,
    end_article,
    steps,
    ROUND((steps - mean_steps) / stddev_steps, 2) as z_score,
    CASE 
        WHEN (steps - mean_steps) / stddev_steps < -2 THEN 'Significantly Shorter'
        WHEN (steps - mean_steps) / stddev_steps < -1 THEN 'Shorter than Average'
        WHEN (steps - mean_steps) / stddev_steps > 2 THEN 'Significantly Longer'
        WHEN (steps - mean_steps) / stddev_steps > 1 THEN 'Longer than Average'
        ELSE 'Average Length'
    END as path_category,
    creation_date,
    succeeded
FROM 
    WIKI_COPY.WIKI_PATHS p
JOIN 
    path_stats ps ON p.path_id = ps.path_id
WHERE 
    ABS((steps - mean_steps) / stddev_steps) > 2  -- Only showing significant outliers
ORDER BY 
    ABS((steps - mean_steps) / stddev_steps) DESC;

-- 3. Time Series Analysis of Path Data
WITH daily_stats AS (
    SELECT 
        TO_CHAR(creation_date, 'YYYY-MM-DD') as day,
        COUNT(*) as paths_collected,
        ROUND(AVG(steps), 2) as avg_path_length,
        MEDIAN(steps) as median_path_length,
        STDDEV(steps) as stddev_path_length,
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
    median_path_length,
    stddev_path_length,
    successful_paths,
    success_rate,
    -- Moving averages (3-day window)
    ROUND(AVG(paths_collected) OVER (ORDER BY day ROWS BETWEEN 2 PRECEDING AND CURRENT ROW), 2) as moving_avg_paths,
    ROUND(AVG(avg_path_length) OVER (ORDER BY day ROWS BETWEEN 2 PRECEDING AND CURRENT ROW), 2) as moving_avg_length,
    ROUND(AVG(success_rate) OVER (ORDER BY day ROWS BETWEEN 2 PRECEDING AND CURRENT ROW), 2) as moving_avg_success_rate,
    -- Day-over-day changes
    paths_collected - LAG(paths_collected, 1, paths_collected) OVER (ORDER BY day) as path_count_change,
    ROUND(avg_path_length - LAG(avg_path_length, 1, avg_path_length) OVER (ORDER BY day), 2) as avg_length_change,
    ROUND(success_rate - LAG(success_rate, 1, success_rate) OVER (ORDER BY day), 2) as success_rate_change
FROM 
    daily_stats
ORDER BY 
    day;

-- 4. Correlation Analysis Between Path Length and Success Rate
WITH article_stats AS (
    SELECT 
        start_article,
        COUNT(*) as paths_count,
        ROUND(AVG(steps), 2) as avg_steps,
        ROUND(STDDEV(steps), 2) as stddev_steps,
        SUM(CASE WHEN succeeded = 1 THEN 1 ELSE 0 END) as successful_paths,
        ROUND(SUM(CASE WHEN succeeded = 1 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) as success_rate
    FROM 
        WIKI_COPY.WIKI_PATHS
    GROUP BY 
        start_article
    HAVING 
        COUNT(*) >= 10  -- Only considering articles with sufficient data
)
SELECT 
    start_article,
    paths_count,
    avg_steps,
    stddev_steps,
    successful_paths,
    success_rate,
    -- Correlation score: normalized product of inverse path length and success rate
    -- Higher values indicate shorter paths with higher success rates
    ROUND((100 - LEAST(avg_steps * 5, 100)) * success_rate / 100, 2) as efficiency_score,
    -- Categorize the efficiency
    CASE 
        WHEN (100 - LEAST(avg_steps * 5, 100)) * success_rate / 100 > 75 THEN 'Highly Efficient'
        WHEN (100 - LEAST(avg_steps * 5, 100)) * success_rate / 100 > 50 THEN 'Efficient'
        WHEN (100 - LEAST(avg_steps * 5, 100)) * success_rate / 100 > 25 THEN 'Moderate'
        ELSE 'Inefficient'
    END as efficiency_category
FROM 
    article_stats
ORDER BY 
    efficiency_score DESC;

-- 5. Statistical Distribution of Node Centrality Measures
WITH node_occurrences AS (
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
path_total AS (
    SELECT COUNT(*) as total_paths FROM WIKI_COPY.WIKI_PATHS
),
node_stats AS (
    SELECT 
        article_title,
        path_count,
        occurrence_count,
        ROUND(path_count * 100.0 / (SELECT total_paths FROM path_total), 2) as path_coverage,
        ROUND(avg_position, 2) as avg_position,
        ROUND(position_stddev, 2) as position_stddev,
        -- Centrality score: combination of path coverage and position stability
        ROUND(path_count * 100.0 / (SELECT total_paths FROM path_total) * 
              (1 / (CASE WHEN position_stddev = 0 THEN 0.1 ELSE position_stddev END)), 2) as centrality_score
    FROM 
        node_occurrences
    WHERE
        path_count >= 5  -- Minimum threshold to avoid noise
)
SELECT 
    article_title,
    path_count,
    occurrence_count,
    path_coverage,
    avg_position,
    position_stddev,
    centrality_score,
    -- Statistical percentile ranking
    NTILE(100) OVER (ORDER BY centrality_score) as centrality_percentile,
    -- Z-score for centrality (how many standard deviations from the mean)
    ROUND((centrality_score - (SELECT AVG(centrality_score) FROM node_stats)) / 
           (SELECT STDDEV(centrality_score) FROM node_stats), 2) as centrality_z_score,
    -- Categorization based on percentiles
    CASE 
        WHEN NTILE(100) OVER (ORDER BY centrality_score) > 95 THEN 'Super Central'
        WHEN NTILE(100) OVER (ORDER BY centrality_score) > 75 THEN 'Highly Central'
        WHEN NTILE(100) OVER (ORDER BY centrality_score) > 50 THEN 'Moderately Central'
        WHEN NTILE(100) OVER (ORDER BY centrality_score) > 25 THEN 'Peripheral'
        ELSE 'Very Peripheral'
    END as centrality_category
FROM 
    node_stats
ORDER BY 
    centrality_score DESC;

-- 6. Path Success Regression Analysis
-- Model path success probability using logistic regression concepts
WITH path_features AS (
    SELECT 
        path_id,
        start_article,
        end_article,
        steps,
        succeeded,
        -- Feature 1: Path length (normalized)
        (steps - (SELECT MIN(steps) FROM WIKI_COPY.WIKI_PATHS)) / 
        ((SELECT MAX(steps) FROM WIKI_COPY.WIKI_PATHS) - (SELECT MIN(steps) FROM WIKI_COPY.WIKI_PATHS)) as norm_steps,
        -- Feature 2: End article popularity (by occurrence in paths)
        (SELECT COUNT(*) FROM WIKI_COPY.WIKI_PATH_NODES WHERE article_title = p.end_article) as end_popularity,
        -- Feature 3: Start article popularity (by occurrence in paths)
        (SELECT COUNT(*) FROM WIKI_COPY.WIKI_PATH_NODES WHERE article_title = p.start_article) as start_popularity
    FROM 
        WIKI_COPY.WIKI_PATHS p
),
feature_stats AS (
    SELECT 
        -- Normalize the popularity features
        path_id,
        succeeded,
        norm_steps,
        start_popularity / (SELECT MAX(start_popularity) FROM path_features) as norm_start_pop,
        end_popularity / (SELECT MAX(end_popularity) FROM path_features) as norm_end_pop
    FROM 
        path_features
)
SELECT 
    -- Calculate pseudo-logistic regression scores (higher = more likely to succeed)
    path_id,
    succeeded,
    ROUND(norm_steps, 2) as normalized_steps,
    ROUND(norm_start_pop, 2) as normalized_start_popularity,
    ROUND(norm_end_pop, 2) as normalized_end_popularity,
    -- Simplified logistic regression model score (negative coefficient for steps, positive for popularity)
    ROUND((-1.5 * norm_steps + 0.8 * norm_start_pop + 0.7 * norm_end_pop), 2) as success_score,
    -- Probability estimation using logistic function
    ROUND(1 / (1 + EXP(-(-1.5 * norm_steps + 0.8 * norm_start_pop + 0.7 * norm_end_pop))), 2) as success_probability,
    -- Compare prediction with actual outcome
    CASE 
        WHEN (1 / (1 + EXP(-(-1.5 * norm_steps + 0.8 * norm_start_pop + 0.7 * norm_end_pop))) > 0.5 AND succeeded = 1 THEN 'True Positive'
        WHEN (1 / (1 + EXP(-(-1.5 * norm_steps + 0.8 * norm_start_pop + 0.7 * norm_end_pop))) > 0.5 AND succeeded = 0 THEN 'False Positive'
        WHEN (1 / (1 + EXP(-(-1.5 * norm_steps + 0.8 * norm_start_pop + 0.7 * norm_end_pop))) <= 0.5 AND succeeded = 1 THEN 'False Negative'
        ELSE 'True Negative'
    END as prediction_result
FROM 
    feature_stats
ORDER BY 
    success_probability DESC;

-- 7. Wikipedia Category Distribution Inference
-- Inferring article categories based on network patterns and titles
WITH article_keywords AS (
    SELECT 
        article_title,
        -- Extract words from title and analyze for category inference
        REGEXP_SUBSTR(article_title, '^[A-Za-z]+') as first_word,
        REGEXP_SUBSTR(article_title, '[A-Za-z]+$') as last_word,
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
            WHEN LOWER(article_title) LIKE '%baseball%' THEN 'Sports'
            WHEN LOWER(article_title) LIKE '%basketball%' THEN 'Sports'
            WHEN LOWER(article_title) LIKE '%music%' THEN 'Music'
            WHEN LOWER(article_title) LIKE '%film%' THEN 'Film'
            WHEN LOWER(article_title) LIKE '%movie%' THEN 'Film'
            ELSE 'Uncategorized'
        END as inferred_category
    FROM 
        (SELECT DISTINCT article_title FROM WIKI_COPY.WIKI_PATH_NODES)
),
connection_patterns AS (
    SELECT 
        n1.article_title,
        k1.inferred_category,
        n2.article_title as connected_to,
        k2.inferred_category as connected_category,
        COUNT(DISTINCT n1.path_id) as connection_count
    FROM 
        WIKI_COPY.WIKI_PATH_NODES n1
    JOIN 
        WIKI_COPY.WIKI_PATH_NODES n2 
        ON n1.path_id = n2.path_id
        AND n2.step_number = n1.step_number + 1
    JOIN
        article_keywords k1 ON n1.article_title = k1.article_title
    JOIN
        article_keywords k2 ON n2.article_title = k2.article_title
    GROUP BY 
        n1.article_title, k1.inferred_category, n2.article_title, k2.inferred_category
)
SELECT 
    inferred_category,
    COUNT(DISTINCT article_title) as article_count,
    -- Distribution of topics
    ROUND(COUNT(DISTINCT article_title) * 100.0 / (
        SELECT COUNT(DISTINCT article_title) FROM article_keywords
    ), 2) as category_percentage,
    -- Most common connections between categories
    LISTAGG(connected_category || ' (' || COUNT(DISTINCT connected_to) || ')', ', ') 
        WITHIN GROUP (ORDER BY COUNT(DISTINCT connected_to) DESC) as top_connected_categories,
    -- Category interconnection score (higher means more diverse connections)
    COUNT(DISTINCT connected_category) / 
        NULLIF(COUNT(DISTINCT article_title), 0) as category_diversity_score
FROM 
    connection_patterns
GROUP BY 
    inferred_category
ORDER BY 
    article_count DESC;

-- 8. Article Volatility Analysis (How stable are articles in the network?)
WITH position_stats AS (
    SELECT 
        article_title,
        path_id,
        step_number,
        COUNT(*) OVER (PARTITION BY article_title) as article_occurrences,
        AVG(step_number) OVER (PARTITION BY article_title) as avg_step,
        STDDEV(step_number) OVER (PARTITION BY article_title) as stddev_step,
        MIN(step_number) OVER (PARTITION BY article_title) as min_step,
        MAX(step_number) OVER (PARTITION BY article_title) as max_step
    FROM 
        WIKI_COPY.WIKI_PATH_NODES
),
volatility_measures AS (
    SELECT DISTINCT
        article_title,
        article_occurrences,
        ROUND(avg_step, 2) as avg_position,
        ROUND(stddev_step, 2) as position_stddev,
        min_step as earliest_position,
        max_step as latest_position,
        max_step - min_step as position_range,
        -- Coefficient of variation (standardized measure of dispersion)
        ROUND(stddev_step / NULLIF(avg_step, 0) * 100, 2) as position_cv,
        -- Position entropy (measure of unpredictability)
        ROUND(stddev_step * LOG(2, NULLIF(max_step - min_step + 1, 0)), 2) as position_entropy
    FROM 
        position_stats
    WHERE 
        article_occurrences >= 10  -- Only analyzing articles with sufficient data
)
SELECT 
    article_title,
    article_occurrences,
    avg_position,
    position_stddev,
    earliest_position,
    latest_position,
    position_range,
    position_cv,
    position_entropy,
    -- Volatility score (composite measure of multiple volatility factors)
    ROUND((position_cv + position_entropy + position_range) / 3, 2) as volatility_score,
    -- Categorize volatility
    CASE 
        WHEN (position_cv + position_entropy + position_range) / 3 > 100 THEN 'Extremely Volatile'
        WHEN (position_cv + position_entropy + position_range) / 3 > 75 THEN 'Highly Volatile'
        WHEN (position_cv + position_entropy + position_range) / 3 > 50 THEN 'Moderately Volatile'
        WHEN (position_cv + position_entropy + position_range) / 3 > 25 THEN 'Somewhat Stable'
        ELSE 'Very Stable'
    END as volatility_category
FROM 
    volatility_measures
ORDER BY 
    volatility_score DESC; 