alter session set container=XEPDB1;

INSERT INTO system.wiki_path_nodes (node_id, path_id, step_number, article) VALUES (1, 1, 1, 'Philosophy');
INSERT INTO system.wiki_path_nodes (node_id, path_id, step_number, article) VALUES (2, 1, 2, 'Reality');
INSERT INTO system.wiki_path_nodes (node_id, path_id, step_number, article) VALUES (3, 1, 3, 'Science');
INSERT INTO system.wiki_path_nodes (node_id, path_id, step_number, article) VALUES (4, 1, 4, 'Mathematics');

COMMIT; 