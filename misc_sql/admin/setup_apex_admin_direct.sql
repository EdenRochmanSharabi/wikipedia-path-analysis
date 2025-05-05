ALTER SESSION SET CONTAINER=XEPDB1;

-- Run script as SYSDBA to directly set the admin password in the database
BEGIN
    FOR c1 IN (SELECT username FROM dba_users WHERE username = 'APEX_PUBLIC_USER') LOOP
        EXECUTE IMMEDIATE ('ALTER USER apex_public_user ACCOUNT UNLOCK');
        EXECUTE IMMEDIATE ('ALTER USER apex_public_user IDENTIFIED BY Oracle21c');
    END LOOP;
END;
/

-- Verify APEX_INSTANCE_ADMIN exists and grant privileges
BEGIN
    EXECUTE IMMEDIATE 'GRANT DBA TO APEX_230200';
EXCEPTION
    WHEN OTHERS THEN NULL;
END;
/

-- Now let's check if we can access APEX instance admin
SELECT username FROM all_users WHERE username LIKE 'APEX%';

-- Create a direct login user for database authentication
CREATE USER apex_admin IDENTIFIED BY Oracle21c
QUOTA UNLIMITED ON USERS;

GRANT CREATE SESSION, CREATE PROCEDURE, CREATE TABLE, CREATE SEQUENCE TO apex_admin;
GRANT APEX_ADMINISTRATOR_ROLE TO apex_admin;

COMMIT; 