-- Oracle APEX Visualizations for Wikipedia Network Analysis
-- This file contains SQL scripts for creating Oracle APEX visualizations based on our analysis

-- =====================================================================
-- APPLICATION SETUP
-- =====================================================================

-- 1. Create APEX Application (Execute via SQL Workshop in APEX)
BEGIN
    -- Create application with ID 100 (can be changed as needed)
    APEX_APPLICATION_INSTALL.SET_APPLICATION_ID(100);
    APEX_APPLICATION_INSTALL.SET_APPLICATION_NAME('Wikipedia Network Analysis');
    APEX_APPLICATION_INSTALL.SET_APPLICATION_ALIAS('WIKINETWORK');
    APEX_APPLICATION_INSTALL.SET_AUTHENTICATION('APEX_ACCOUNTS');
    APEX_APPLICATION_INSTALL.SET_APPLICATION_ALIAS('WIKINETWORK');
    APEX_APPLICATION_INSTALL.SET_SCHEMA(NVL(v('APP_SCHEMA'),'WIKI_COPY'));
END;
/

-- =====================================================================
-- PAGE 1: EXECUTIVE DASHBOARD
-- =====================================================================

-- 2. Create Overall KPI Region
DECLARE
    l_region_id NUMBER;
BEGIN
    l_region_id := APEX_REGION.CREATE_STATIC_REGION(
        p_page_id       => 1,
        p_region_name   => 'Wikipedia Network Overview',
        p_region_title  => 'Network Key Performance Indicators',
        p_position      => 'BODY',
        p_template      => 'Standard',
        p_display_point => 'BODY'
    );

    -- Add KPI Cards
    APEX_REGION.CREATE_REPORT_REGION(
        p_page_id         => 1,
        p_sub_region_name => 'Network KPIs',
        p_parent_region_id => l_region_id,
        p_source           => 'SELECT 
                                 total_paths, 
                                 unique_articles, 
                                 overall_success_rate, 
                                 avg_path_length,
                                 total_connections
                               FROM WIKI_COPY.BI_OVERALL_METRICS',
        p_template         => 'Cards',
        p_display_point    => 'SUB_REGIONS'
    );
END;
/

-- 3. Create Path Length Distribution Chart
DECLARE
    l_region_id NUMBER;
BEGIN
    l_region_id := APEX_REGION.CREATE_CHART_REGION(
        p_page_id          => 1,
        p_region_name      => 'Path Length Distribution',
        p_region_title     => 'Path Length Distribution',
        p_chart_type       => 'bar',
        p_position         => 'BODY',
        p_display_point    => 'BODY',
        p_source           => 'SELECT 
                                 steps as "Path Length", 
                                 frequency as "Count", 
                                 percentage as "Percentage" 
                               FROM 
                                 (
                                   WITH path_stats AS (
                                     SELECT 
                                       steps,
                                       COUNT(*) as frequency
                                     FROM 
                                       WIKI_COPY.WIKI_PATHS
                                     GROUP BY 
                                       steps
                                   )
                                   SELECT 
                                     p.steps,
                                     p.frequency,
                                     ROUND(p.frequency * 100.0 / (SELECT COUNT(*) FROM WIKI_COPY.WIKI_PATHS), 2) as percentage
                                   FROM 
                                     path_stats p
                                 )
                               ORDER BY "Path Length"'
    );
    
    -- Set chart attributes
    APEX_JAVASCRIPT.ADD_ATTRIBUTE(
        p_value      => 'Path Length Distribution - Shows the frequency of different path lengths',
        p_add_comma  => FALSE,
        p_region_id  => l_region_id,
        p_attribute  => 'chart-description'
    );
END;
/

-- 4. Create Success Rate vs Path Length Chart
DECLARE
    l_region_id NUMBER;
BEGIN
    l_region_id := APEX_REGION.CREATE_CHART_REGION(
        p_page_id          => 1,
        p_region_name      => 'Success Rate by Path Length',
        p_region_title     => 'Success Rate vs Path Length',
        p_chart_type       => 'line',
        p_position         => 'BODY',
        p_display_point    => 'BODY',
        p_source           => 'SELECT 
                                 factor_value as "Path Length", 
                                 success_rate as "Success Rate" 
                               FROM 
                                 WIKI_COPY.BI_SUCCESS_FACTORS
                               WHERE 
                                 factor_type = ''Path Length''
                               ORDER BY 
                                 factor_value'
    );
END;
/

-- 5. Create Daily Trends Chart
DECLARE
    l_region_id NUMBER;
BEGIN
    l_region_id := APEX_REGION.CREATE_CHART_REGION(
        p_page_id          => 1,
        p_region_name      => 'Daily Collection Trends',
        p_region_title     => 'Daily Path Collection Trends',
        p_chart_type       => 'combination',
        p_position         => 'BODY',
        p_display_point    => 'BODY',
        p_source           => 'SELECT 
                                 day as "Date", 
                                 paths_collected as "Paths Collected", 
                                 success_rate as "Success Rate",
                                 ma7_paths as "7-Day Moving Average"
                               FROM 
                                 WIKI_COPY.BI_DAILY_TRENDS
                               ORDER BY 
                                 day'
    );
END;
/

-- 6. Create Domain Distribution Pie Chart
DECLARE
    l_region_id NUMBER;
BEGIN
    l_region_id := APEX_REGION.CREATE_CHART_REGION(
        p_page_id          => 1,
        p_region_name      => 'Knowledge Domain Distribution',
        p_region_title     => 'Knowledge Domain Distribution',
        p_chart_type       => 'pie',
        p_position         => 'BODY',
        p_display_point    => 'BODY',
        p_source           => 'SELECT 
                                 domain as "Domain", 
                                 article_count as "Article Count" 
                               FROM 
                                 WIKI_COPY.BI_DOMAIN_DISTRIBUTION
                               ORDER BY 
                                 article_count DESC'
    );
END;
/

-- =====================================================================
-- PAGE 2: NETWORK STRUCTURE ANALYSIS
-- =====================================================================

-- 7. Create Top Hub Articles Interactive Report
DECLARE
    l_region_id NUMBER;
BEGIN
    l_region_id := APEX_REGION.CREATE_REPORT_REGION(
        p_page_id          => 2,
        p_region_name      => 'Top Hub Articles',
        p_region_title     => 'Top Articles by Network Centrality',
        p_template         => 'Interactive Report',
        p_position         => 'BODY',
        p_display_point    => 'BODY',
        p_source           => 'SELECT 
                                 article_title,
                                 ROUND(authority_score, 2) as authority_score,
                                 ROUND(hub_score, 2) as hub_score,
                                 ROUND(importance_score, 2) as importance_score,
                                 path_count,
                                 incoming_links,
                                 outgoing_links,
                                 article_role
                               FROM 
                                 WIKI_COPY.BI_TOP_ARTICLES
                               ORDER BY 
                                 importance_score DESC'
    );
END;
/

-- 8. Create Network Centrality Bubble Chart
DECLARE
    l_region_id NUMBER;
BEGIN
    l_region_id := APEX_REGION.CREATE_CHART_REGION(
        p_page_id          => 2,
        p_region_name      => 'Article Centrality Visualization',
        p_region_title     => 'Article Centrality (Hub vs Authority)',
        p_chart_type       => 'bubble',
        p_position         => 'BODY',
        p_display_point    => 'BODY',
        p_source           => 'SELECT 
                                 article_title as "Article",
                                 hub_score as "Hub Score",
                                 authority_score as "Authority Score",
                                 path_count as "Size",
                                 article_role as "Category"
                               FROM 
                                 WIKI_COPY.BI_TOP_ARTICLES
                               WHERE 
                                 importance_score > 40
                               ORDER BY 
                                 importance_score DESC'
    );
END;
/

-- 9. Create Network Graph Visualization
DECLARE
    l_region_id NUMBER;
BEGIN
    l_region_id := APEX_REGION.CREATE_REGION(
        p_page_id          => 2,
        p_region_name      => 'Network Graph Visualization',
        p_region_title     => 'Wikipedia Link Network Graph',
        p_region_source    => 'SELECT 
                                 source as "Source", 
                                 target as "Target",
                                 weight as "Weight"
                               FROM 
                                 WIKI_COPY.GRAPH_EDGE_LIST
                               WHERE 
                                 weight > 5
                               ORDER BY 
                                 weight DESC',
        p_position         => 'BODY',
        p_template         => 'D3Force',
        p_display_point    => 'BODY'
    );
END;
/

-- 10. Create Community Structure Analysis
DECLARE
    l_region_id NUMBER;
BEGIN
    l_region_id := APEX_REGION.CREATE_CHART_REGION(
        p_page_id          => 2,
        p_region_name      => 'Community Structure',
        p_region_title     => 'Community Connection Strength',
        p_chart_type       => 'heatmap',
        p_position         => 'BODY',
        p_display_point    => 'BODY',
        p_source           => 'WITH cluster_connections AS (
                                 SELECT 
                                   c1.level2_cluster as source_cluster,
                                   c2.level2_cluster as target_cluster,
                                   COUNT(*) as connection_count
                                 FROM 
                                   WIKI_COPY.WIKI_PATH_NODES n1
                                 JOIN 
                                   WIKI_COPY.WIKI_PATH_NODES n2 ON n1.path_id = n2.path_id AND n2.step_number = n1.step_number + 1
                                 JOIN 
                                   WIKI_COPY.HIERARCHICAL_ARTICLE_CLUSTERS c1 ON n1.article_title = c1.article_title
                                 JOIN 
                                   WIKI_COPY.HIERARCHICAL_ARTICLE_CLUSTERS c2 ON n2.article_title = c2.article_title
                                 GROUP BY 
                                   c1.level2_cluster, c2.level2_cluster
                               )
                               SELECT 
                                 source_cluster as "Source Cluster",
                                 target_cluster as "Target Cluster",
                                 connection_count as "Connection Strength"
                               FROM 
                                 cluster_connections
                               WHERE 
                                 connection_count > 10
                               ORDER BY 
                                 connection_count DESC'
    );
END;
/

-- =====================================================================
-- PAGE 3: TIME SERIES & GROWTH ANALYSIS
-- =====================================================================

-- 11. Create Network Growth Chart
DECLARE
    l_region_id NUMBER;
BEGIN
    l_region_id := APEX_REGION.CREATE_CHART_REGION(
        p_page_id          => 3,
        p_region_name      => 'Network Growth Over Time',
        p_region_title     => 'Network Growth Over Time',
        p_chart_type       => 'line',
        p_position         => 'BODY',
        p_display_point    => 'BODY',
        p_source           => 'SELECT 
                                 month as "Month", 
                                 cumulative_paths as "Cumulative Paths",
                                 unique_articles as "Unique Articles" 
                               FROM 
                                 WIKI_COPY.BI_NETWORK_GROWTH
                               ORDER BY 
                                 month'
    );
END;
/

-- 12. Create Network Density Evolution Chart
DECLARE
    l_region_id NUMBER;
BEGIN
    l_region_id := APEX_REGION.CREATE_CHART_REGION(
        p_page_id          => 3,
        p_region_name      => 'Network Density Evolution',
        p_region_title     => 'Network Density Over Time',
        p_chart_type       => 'line',
        p_position         => 'BODY',
        p_display_point    => 'BODY',
        p_source           => 'SELECT 
                                 month as "Month", 
                                 network_density as "Network Density" 
                               FROM 
                                 WIKI_COPY.BI_NETWORK_GROWTH
                               ORDER BY 
                                 month'
    );
END;
/

-- 13. Create Growth Rate Comparisons
DECLARE
    l_region_id NUMBER;
BEGIN
    l_region_id := APEX_REGION.CREATE_CHART_REGION(
        p_page_id          => 3,
        p_region_name      => 'Growth Rate Comparisons',
        p_region_title     => 'Month-over-Month Growth Rates',
        p_chart_type       => 'bar',
        p_position         => 'BODY',
        p_display_point    => 'BODY',
        p_source           => 'SELECT 
                                 month as "Month", 
                                 path_growth_rate as "Path Growth Rate (%)",
                                 article_growth_rate as "Article Growth Rate (%)" 
                               FROM 
                                 WIKI_COPY.BI_NETWORK_GROWTH
                               WHERE 
                                 month > (SELECT MIN(month) FROM WIKI_COPY.BI_NETWORK_GROWTH)
                               ORDER BY 
                                 month'
    );
END;
/

-- =====================================================================
-- PAGE 4: PATH SUCCESS ANALYSIS
-- =====================================================================

-- 14. Create Success Factors Comparison
DECLARE
    l_region_id NUMBER;
BEGIN
    l_region_id := APEX_REGION.CREATE_CHART_REGION(
        p_page_id          => 4,
        p_region_name      => 'Success Factors Analysis',
        p_region_title     => 'Path Success Factors Comparison',
        p_chart_type       => 'line',
        p_position         => 'BODY',
        p_display_point    => 'BODY',
        p_source           => 'SELECT 
                                 factor_type || '': '' || factor_value as "Factor",
                                 success_rate as "Success Rate (%)" 
                               FROM 
                                 WIKI_COPY.BI_SUCCESS_FACTORS
                               ORDER BY 
                                 factor_type, factor_value'
    );
END;
/

-- 15. Create Regression Analysis Visualization
DECLARE
    l_region_id NUMBER;
BEGIN
    l_region_id := APEX_REGION.CREATE_CHART_REGION(
        p_page_id          => 4,
        p_region_name      => 'Path Length vs Success Probability',
        p_region_title     => 'Regression: Path Length vs Success Probability',
        p_chart_type       => 'scatter',
        p_position         => 'BODY',
        p_display_point    => 'BODY',
        p_source           => 'WITH path_features AS (
                                 SELECT 
                                   p.path_id,
                                   p.succeeded,
                                   p.steps,
                                   -- Feature 1: Path length (normalized)
                                   (steps - (SELECT MIN(steps) FROM WIKI_COPY.WIKI_PATHS)) / 
                                   ((SELECT MAX(steps) FROM WIKI_COPY.WIKI_PATHS) - (SELECT MIN(steps) FROM WIKI_COPY.WIKI_PATHS)) as norm_steps,
                                   -- Simplified probability calculation
                                   ROUND(1 / (1 + EXP(-(1.5 - steps/5))), 2) as predicted_probability
                                 FROM 
                                   WIKI_COPY.WIKI_PATHS p
                               )
                               SELECT 
                                 steps as "Path Length",
                                 succeeded as "Actual Success",
                                 predicted_probability as "Predicted Probability"
                               FROM 
                                 path_features
                               WHERE 
                                 MOD(path_id, 10) = 0  -- Sample 10% for readability
                               ORDER BY 
                                 path_id'
    );
END;
/

-- 16. Create Cross-Domain Success Rate Analysis
DECLARE
    l_region_id NUMBER;
BEGIN
    l_region_id := APEX_REGION.CREATE_CHART_REGION(
        p_page_id          => 4,
        p_region_name      => 'Cross-Domain Success Rates',
        p_region_title     => 'Path Success Rates by Knowledge Domain',
        p_chart_type       => 'heatmap',
        p_position         => 'BODY',
        p_display_point    => 'BODY',
        p_source           => 'SELECT 
                                 start_domain as "Start Domain",
                                 end_domain as "End Domain",
                                 success_rate as "Success Rate (%)" 
                               FROM 
                                 WIKI_COPY.BI_DOMAIN_NAVIGATION
                               WHERE 
                                 path_count > 10
                               ORDER BY 
                                 success_rate DESC'
    );
END;
/

-- =====================================================================
-- PAGE 5: CLUSTER ANALYSIS
-- =====================================================================

-- 17. Create Cluster Quality Metrics
DECLARE
    l_region_id NUMBER;
BEGIN
    l_region_id := APEX_REGION.CREATE_CHART_REGION(
        p_page_id          => 5,
        p_region_name      => 'Cluster Quality Metrics',
        p_region_title     => 'Cluster Quality Analysis',
        p_chart_type       => 'bar',
        p_position         => 'BODY',
        p_display_point    => 'BODY',
        p_source           => 'SELECT 
                                 cluster_id as "Cluster ID",
                                 cohesion_score as "Cohesion Score",
                                 attraction_score as "Attraction Score",
                                 expansion_score as "Expansion Score",
                                 quality_score as "Overall Quality Score" 
                               FROM 
                                 WIKI_COPY.BI_CLUSTERING_EFFECTIVENESS
                               ORDER BY 
                                 quality_score DESC'
    );
END;
/

-- 18. Create Cluster Character Distribution
DECLARE
    l_region_id NUMBER;
BEGIN
    l_region_id := APEX_REGION.CREATE_CHART_REGION(
        p_page_id          => 5,
        p_region_name      => 'Cluster Character Distribution',
        p_region_title     => 'Cluster Type Distribution',
        p_chart_type       => 'pie',
        p_position         => 'BODY',
        p_display_point    => 'BODY',
        p_source           => 'SELECT 
                                 cluster_character as "Cluster Type",
                                 COUNT(*) as "Count" 
                               FROM 
                                 WIKI_COPY.BI_CLUSTERING_EFFECTIVENESS
                               GROUP BY 
                                 cluster_character
                               ORDER BY 
                                 "Count" DESC'
    );
END;
/

-- 19. Create Cluster Membership Interactive Report
DECLARE
    l_region_id NUMBER;
BEGIN
    l_region_id := APEX_REGION.CREATE_REPORT_REGION(
        p_page_id          => 5,
        p_region_name      => 'Cluster Membership Details',
        p_region_title     => 'Top Articles by Cluster',
        p_template         => 'Interactive Report',
        p_position         => 'BODY',
        p_display_point    => 'BODY',
        p_source           => 'WITH article_metrics AS (
                                 SELECT 
                                   c.article_title,
                                   c.level2_cluster as cluster_id,
                                   COUNT(DISTINCT n.path_id) as path_count
                                 FROM 
                                   WIKI_COPY.HIERARCHICAL_ARTICLE_CLUSTERS c
                                 JOIN
                                   WIKI_COPY.WIKI_PATH_NODES n ON c.article_title = n.article_title
                                 GROUP BY 
                                   c.article_title, c.level2_cluster
                               )
                               SELECT 
                                 cluster_id as "Cluster ID",
                                 article_title as "Article",
                                 path_count as "Path Count"
                               FROM 
                                 article_metrics
                               WHERE 
                                 (cluster_id, path_count) IN (
                                   SELECT 
                                     cluster_id, 
                                     MAX(path_count) 
                                   FROM 
                                     article_metrics 
                                   GROUP BY 
                                     cluster_id
                                 )
                               ORDER BY 
                                 path_count DESC'
    );
END;
/

-- =====================================================================
-- APEX DASHBOARD CONFIGURATION SCRIPT
-- =====================================================================
-- Note: The code above provides SQL for defining the visualizations.
-- In practice, some aspects of APEX dashboard configuration such as layout, 
-- colors, and interactive features would be set through the APEX UI or by
-- additional API calls not fully shown here.
--
-- To deploy this in an actual Oracle APEX environment:
-- 1. Create a new APEX application through the APEX Builder
-- 2. Run the SQL above in SQL Workshop
-- 3. Enhance the visualizations using the APEX Page Designer
-- 4. Set appropriate application themes and navigation
-- 5. Create Dashboard login and user management settings
-- ===================================================================== 