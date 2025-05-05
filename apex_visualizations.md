# Creating Wikipedia Path Visualizations in Oracle APEX

Follow these steps to create visualizations of your Wikipedia path data using Oracle APEX.

## Login to APEX

1. Open your browser and navigate to http://localhost:8080/apex
2. Enter the following credentials:
   - Workspace: WIKISPACE
   - Username: WIKI_ADMIN 
   - Password: Oracle21c

## Create a New Application

1. Click on "App Builder" in the top navigation
2. Click "Create" button
3. Select "New Application"
4. Enter "Wikipedia Paths" as the Name
5. Click "Add Page"
6. Choose "Dashboard" as the page type
7. Click "Create Application"

## Create a Wiki Paths Report

1. From the application builder, click on your "Wikipedia Paths" application
2. Click "Create Page"
3. Select "Report" and then "Interactive Report"
4. Enter "Wiki Paths" as the Page Name and click "Next"
5. For Navigation Menu, select "Create a new navigation menu entry" and click "Next"
6. For Table / View, select "WIKI_PATHS" from the WIKI_USER schema
7. Click "Create Page"

## Create a Path Details Report

1. Again click "Create Page" 
2. Select "Report" and then "Interactive Report"
3. Enter "Path Details" as the Page Name and click "Next"
4. For Navigation Menu, select "Create a new navigation menu entry" and click "Next"
5. For Table / View, select "WIKI_PATH_NODES" from the WIKI_USER schema
6. Click "Create Page"
7. After the page is created, go to Page Designer
8. Add a page item P3_PATH_ID as a Hidden field
9. Modify the report's SQL query to:

```sql
SELECT node_id, path_id, step_number, article_title, article_url
FROM wiki_user.wiki_path_nodes
WHERE path_id = :P3_PATH_ID
ORDER BY step_number
```

## Create a Chart of Most Common Articles

1. Click "Create Page" again
2. Select "Chart" as the page type
3. Choose "Bar Chart" and click "Next"
4. Enter "Common Articles" as the Page Name and click "Next"
5. For Navigation Menu, select "Create a new navigation menu entry" and click "Next"
6. For SQL Query, enter:

```sql
SELECT article_title, COUNT(*) as frequency
FROM wiki_user.wiki_path_nodes
GROUP BY article_title
HAVING COUNT(*) > 1
ORDER BY frequency DESC
FETCH FIRST 10 ROWS ONLY
```

7. Set Label Column to "ARTICLE_TITLE" and Value Column to "FREQUENCY"
8. Click "Create Page"

## Create a Wiki Path Network Visualization

1. Click "Create Page" again
2. Select "Blank Page" and click "Next"
3. Enter "Path Network" as the Page Name and click "Next"
4. Add a Region of type "D3 Force Directed Network Chart"
5. For the SQL Query, use:

```sql
SELECT 
    src.article_title as source,
    dst.article_title as target,
    COUNT(*) as weight
FROM 
    wiki_user.wiki_path_nodes src,
    wiki_user.wiki_path_nodes dst
WHERE 
    src.path_id = dst.path_id
    AND dst.step_number = src.step_number + 1
GROUP BY
    src.article_title, dst.article_title
ORDER BY 
    weight DESC
```

6. Set the Source Column to "SOURCE", Target Column to "TARGET", and Weight Column to "WEIGHT"

## Run Your Application

1. Click the "Run Application" button
2. Navigate through your application to view the various reports and visualizations

You can further enhance your application by:

1. Adding links between the Wiki Paths report and the Path Details report
2. Creating a dashboard that combines multiple visualizations
3. Adding filters to explore the data from different angles
4. Creating a search page to find specific paths or articles 