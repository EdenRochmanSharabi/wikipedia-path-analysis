-- Check system schema
SELECT column_name FROM user_tab_columns WHERE table_name = 'WIKI_PATHS' ORDER BY column_id;

-- Check wiki_user schema
SELECT column_name FROM all_tab_columns 
WHERE table_name = 'WIKI_PATHS' 
AND owner = 'WIKI_USER'
ORDER BY column_id;

EXIT; 