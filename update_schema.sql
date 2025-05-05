alter session set container=XEPDB1;

-- Modify the wiki_paths table
ALTER TABLE system.wiki_paths ADD (
  succeeded NUMBER(1) DEFAULT 0,
  target_depth NUMBER DEFAULT 3,
  crawl_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Modify the wiki_path_nodes table
ALTER TABLE system.wiki_path_nodes ADD (
  article_title VARCHAR2(255),
  article_url VARCHAR2(1000)
);

-- Update the existing nodes with article_title same as article
UPDATE system.wiki_path_nodes SET article_title = article;

-- Create a sequence for path_id if it doesn't exist
BEGIN
  EXECUTE IMMEDIATE 'CREATE SEQUENCE system.wiki_path_seq START WITH 2 INCREMENT BY 1';
EXCEPTION
  WHEN OTHERS THEN
    IF SQLCODE = -955 THEN NULL; -- Sequence already exists
    ELSE RAISE;
    END IF;
END;
/

-- Create a sequence for node_id if it doesn't exist
BEGIN
  EXECUTE IMMEDIATE 'CREATE SEQUENCE system.wiki_node_seq START WITH 5 INCREMENT BY 1';
EXCEPTION
  WHEN OTHERS THEN
    IF SQLCODE = -955 THEN NULL; -- Sequence already exists
    ELSE RAISE;
    END IF;
END;
/

COMMIT; 