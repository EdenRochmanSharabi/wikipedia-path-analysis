SET PAGESIZE 100
SET LINESIZE 150
SET FEEDBACK ON
SET HEADING ON

-- Check for wiki tables across all schemas
SELECT owner, table_name FROM all_tables WHERE table_name LIKE '%WIKI%' ORDER BY owner, table_name;

-- Get all user-created tables
SELECT owner, table_name FROM all_tables 
WHERE owner NOT IN ('SYS','SYSTEM','OUTLN','ANONYMOUS','APEX_PUBLIC_USER','APEX_REST_PUBLIC_USER',
                   'APPQOSSYS','AUDSYS','CTXSYS','DBSFWUSER','DBSNMP','DIP','DVF','DVSYS',
                   'GGSYS','GSMADMIN_INTERNAL','GSMCATUSER','GSMUSER','LBACSYS','MDDATA',
                   'MDSYS','OJVMSYS','OLAPSYS','ORACLE_OCM','ORDDATA','ORDPLUGINS','ORDSYS',
                   'REMOTE_SCHEDULER_AGENT','XDB','XS$NULL')
ORDER BY owner, table_name; 