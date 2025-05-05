BEGIN
    apex_instance_admin.add_workspace(
        p_workspace_id => null,
        p_workspace => 'WIKISPACE',
        p_primary_schema => 'WIKI_USER',
        p_additional_schemas => null
    );
    
    apex_util.set_security_group_id(p_security_group_id => apex_util.find_security_group_id('WIKISPACE'));
    
    apex_util.create_user(
        p_user_name => 'WIKI_ADMIN',
        p_email_address => 'admin@example.com',
        p_web_password => 'Oracle21c',
        p_developer_privs => 'ADMIN:CREATE:DATA_LOADER:EDIT:HELP:MONITOR:SQL',
        p_default_schema => 'WIKI_USER',
        p_allow_access_to_schemas => null
    );
    
    COMMIT;
END;
/ 