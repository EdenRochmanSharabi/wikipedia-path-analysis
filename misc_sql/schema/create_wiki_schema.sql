ALTER SESSION SET CONTAINER=XEPDB1;

-- Create a new schema user for our Wikipedia data
CREATE USER wiki_user IDENTIFIED BY Oracle21c
QUOTA UNLIMITED ON USERS
DEFAULT TABLESPACE USERS
TEMPORARY TABLESPACE TEMP;

-- Grant necessary privileges
GRANT CREATE SESSION, CREATE TABLE, CREATE VIEW, CREATE SEQUENCE, CREATE PROCEDURE TO wiki_user;
GRANT SELECT ANY DICTIONARY TO wiki_user;

-- Copy the tables from SYSTEM to the new schema
CREATE TABLE wiki_user.WIKI_PATHS AS SELECT * FROM system.WIKI_PATHS;
CREATE TABLE wiki_user.WIKI_PATH_NODES AS SELECT * FROM system.WIKI_PATH_NODES;

-- Create the index
CREATE INDEX wiki_user.idx_path_id ON wiki_user.WIKI_PATH_NODES(path_id);

-- Add the constraints
ALTER TABLE wiki_user.WIKI_PATHS ADD CONSTRAINT pk_wiki_paths PRIMARY KEY (path_id);
ALTER TABLE wiki_user.WIKI_PATH_NODES ADD CONSTRAINT pk_wiki_path_nodes PRIMARY KEY (node_id);
ALTER TABLE wiki_user.WIKI_PATH_NODES ADD CONSTRAINT fk_wiki_path_nodes FOREIGN KEY (path_id) REFERENCES wiki_user.WIKI_PATHS(path_id);

COMMIT; 