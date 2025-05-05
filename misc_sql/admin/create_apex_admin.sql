-- Connect as SYS to XEPDB1
ALTER SESSION SET CONTAINER=XEPDB1;

-- Set the APEX ADMIN password
BEGIN
    APEX_UTIL.SET_SECURITY_GROUP_ID(10);
    APEX_UTIL.CHANGE_PASSWORD(
        p_user_name => 'ADMIN',
        p_old_password => null,
        p_new_password => 'Oracle21c'
    );
    COMMIT;
END;
/

-- Unlock the ADMIN account
BEGIN
    APEX_UTIL.SET_SECURITY_GROUP_ID(10);
    APEX_UTIL.UNLOCK_ACCOUNT('ADMIN');
    COMMIT;
END;
/ 