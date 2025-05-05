#!/bin/bash

# Script to connect to Oracle using the container's SQLPlus

echo "Connecting to Oracle database in container..."
docker exec -it oracle-apex-21c sqlplus / as sysdba 