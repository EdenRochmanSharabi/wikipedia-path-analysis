alter session set container=XEPDB1;
begin
    apex_util.set_security_group_id(10);
    apex_util.create_user(
        p_user_name       => 'ADMIN',
        p_email_address   => 'admin@example.com',
        p_web_password    => 'admin',
        p_developer_privs => 'ADMIN:CREATE:DATA_LOADER:EDIT:HELP:MONITOR:SQL',
        p_change_password_on_first_use => 'N');
    commit;
end;
/
