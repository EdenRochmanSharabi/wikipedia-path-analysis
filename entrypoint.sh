#!/bin/bash
set -e

# Install Oracle client from the provided files
echo "Installing Oracle client..."
find /tmp/oracle -name "*.zip" -type f | xargs -I{} unzip -o {} -d $ORACLE_HOME
echo "Oracle client installed."

# Set up tnsnames.ora
mkdir -p $TNS_ADMIN
cat > $TNS_ADMIN/tnsnames.ora << EOF
XE =
  (DESCRIPTION =
    (ADDRESS = (PROTOCOL = TCP)(HOST = host.docker.internal)(PORT = 1521))
    (CONNECT_DATA =
      (SERVER = DEDICATED)
      (SERVICE_NAME = XE)
    )
  )
EOF

echo "Oracle client setup completed."
echo "Running your commands..."

# Run the provided command, or python3 copy_wiki_db.py by default
if [ $# -eq 0 ]; then
    python3 copy_wiki_db.py
    
    # Update analysis scripts to use the new schema
    echo "Updating analysis scripts..."
    python3 update_analysis_scripts.py check_paths.py check_football_paths.py check_philosophy_paths.py
    
    # Test the copied database
    echo "Testing the copied database..."
    python3 check_paths.py
else
    exec "$@"
fi 