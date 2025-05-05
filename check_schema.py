import oracledb

conn = oracledb.connect('system/Oracle21c@localhost:1521/XEPDB1')
cursor = conn.cursor()

print("=== Table Ownership ===")
cursor.execute("SELECT owner, table_name FROM all_tables WHERE table_name = 'WIKI_PATHS'")
for row in cursor.fetchall():
    owner, table_name = row
    print(f"Owner: {owner}, Table: {table_name}")
    
    # Check row count for each owner
    cursor.execute(f"SELECT COUNT(*) FROM {owner}.WIKI_PATHS")
    count = cursor.fetchone()[0]
    print(f"Row count in {owner}.WIKI_PATHS: {count}")
    
    # Check latest entries
    cursor.execute(f"SELECT path_id, start_article, end_article, steps FROM {owner}.WIKI_PATHS ORDER BY path_id DESC FETCH FIRST 3 ROWS ONLY")
    print(f"Latest entries in {owner}.WIKI_PATHS:")
    for entry in cursor.fetchall():
        print(f"  ID: {entry[0]}, Start: {entry[1]}, End: {entry[2]}, Steps: {entry[3]}")
    print()

conn.close()
print("Done!") 