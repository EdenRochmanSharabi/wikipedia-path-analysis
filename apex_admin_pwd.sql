-- Set APEX admin password
BEGIN
    APEX_UTIL.SET_WORKSPACE_ID(1);
    APEX_UTIL.ADMIN_PASSWORD := 'admin';
    APEX_UTIL.SET_USERNAME('admin');
    COMMIT;
END;
/
exit
