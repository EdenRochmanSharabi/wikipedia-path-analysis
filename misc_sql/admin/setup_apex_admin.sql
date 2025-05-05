-- Change admin password
BEGIN
    APEX_UTIL.SET_SECURITY_GROUP_ID(10);
    APEX_UTIL.CREATE_USER(
        p_user_name       => 'ADMIN',
        p_email_address   => 'admin@example.com',
        p_web_password    => 'admin',
        p_developer_privs => 'ADMIN:CREATE:DATA_LOADER:EDIT:HELP:MONITOR:SQL',
        p_change_password_on_first_use => 'N');
    COMMIT;
END;
/
exit
