alter session set container=XEPDB1;
CREATE TABLE system.wiki_paths (
  path_id NUMBER PRIMARY KEY,
  start_article VARCHAR2(255),
  end_article VARCHAR2(255),
  steps NUMBER
);
CREATE TABLE system.wiki_path_nodes (
  node_id NUMBER PRIMARY KEY,
  path_id NUMBER,
  step_number NUMBER,
  article VARCHAR2(255),
  CONSTRAINT fk_path_id FOREIGN KEY (path_id) REFERENCES system.wiki_paths(path_id)
);
INSERT INTO system.wiki_paths (path_id, start_article, end_article, steps) VALUES (1, 'Philosophy', 'Mathematics', 4);
