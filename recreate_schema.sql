alter session set container=XEPDB1;

-- Drop existing tables if they exist
BEGIN
    EXECUTE IMMEDIATE 'DROP TABLE WIKI_PATH_NODES';
EXCEPTION
    WHEN OTHERS THEN
        IF SQLCODE != -942 THEN
            RAISE;
        END IF;
END;
/

BEGIN
    EXECUTE IMMEDIATE 'DROP TABLE WIKI_PATHS';
EXCEPTION
    WHEN OTHERS THEN
        IF SQLCODE != -942 THEN
            RAISE;
        END IF;
END;
/

-- Create WIKI_PATHS table
CREATE TABLE WIKI_PATHS (
    path_id       NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    start_article VARCHAR2(500) NOT NULL,
    end_article   VARCHAR2(500) NOT NULL,
    steps         NUMBER NOT NULL,
    succeeded     NUMBER(1) DEFAULT 1,
    creation_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create WIKI_PATH_NODES table
CREATE TABLE WIKI_PATH_NODES (
    node_id       NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    path_id       NUMBER REFERENCES WIKI_PATHS(path_id),
    step_number   NUMBER NOT NULL,
    article_title VARCHAR2(500) NOT NULL,
    article_url   VARCHAR2(1000)
);

-- Create indexes for performance
CREATE INDEX idx_path_nodes_path_id ON WIKI_PATH_NODES(path_id);
CREATE INDEX idx_path_nodes_article ON WIKI_PATH_NODES(article_title);
CREATE INDEX idx_paths_start ON WIKI_PATHS(start_article);
CREATE INDEX idx_paths_end ON WIKI_PATHS(end_article);

COMMIT;

-- Display the table structure to confirm
DESCRIBE WIKI_PATHS;
DESCRIBE WIKI_PATH_NODES;

EXIT; 