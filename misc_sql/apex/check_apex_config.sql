ALTER SESSION SET CONTAINER=XEPDB1;

-- Check if instance_admin package is available
BEGIN
  DBMS_OUTPUT.PUT_LINE('Checking if APEX_INSTANCE_ADMIN package is available:');
  DBMS_OUTPUT.PUT_LINE('----------------------------------------');
  FOR cur IN (SELECT object_name, status 
              FROM all_objects 
              WHERE object_name LIKE 'APEX_INSTANCE_ADMIN%' 
              AND object_type = 'PACKAGE') LOOP
    DBMS_OUTPUT.PUT_LINE(cur.object_name || ' - ' || cur.status);
  END LOOP;
END;
/

-- Check available APEX workspaces
COLUMN workspace_id FORMAT 9999
COLUMN workspace FORMAT A30
COLUMN schema FORMAT A30

SELECT workspace_id, workspace, schema
FROM apex_workspaces
ORDER BY workspace_id;

-- Check available APEX users
COLUMN user_id FORMAT 9999
COLUMN user_name FORMAT A30
COLUMN workspace FORMAT A20

SELECT u.user_id, u.user_name, w.workspace 
FROM apex_workspace_apex_users u
JOIN apex_workspaces w ON u.workspace_id = w.workspace_id
ORDER BY w.workspace;

-- Check APEX REST config
BEGIN
  DBMS_OUTPUT.PUT_LINE('Checking APEX_REST_CONFIG:');
  DBMS_OUTPUT.PUT_LINE('----------------------------------------');
  FOR cur IN (SELECT owner, object_name, status 
              FROM all_objects 
              WHERE object_name LIKE 'APEX_REST%' 
              AND object_type = 'PACKAGE') LOOP
    DBMS_OUTPUT.PUT_LINE(cur.owner || '.' || cur.object_name || ' - ' || cur.status);
  END LOOP;
END;
/ 