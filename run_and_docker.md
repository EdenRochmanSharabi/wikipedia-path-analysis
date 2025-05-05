# Docker Containers and Database Operations Guide

This guide provides detailed information about the Docker containers in this project, how to manage them, and how to perform database operations between containers.

## Docker Containers Overview

The project uses three Docker containers:

1. **apex-database** - Oracle Database container for storing Wikipedia path data
2. **apex-ords** - Oracle REST Data Services container for accessing APEX
3. **external-project-db** - External container from another project with a separate database

### Container Details

#### 1. Oracle Database (apex-database)

- **Image:** `container-registry.oracle.com/database/free:latest`
- **Purpose:** Primary database for storing all Wikipedia path analysis data
- **Ports:**
  - 1521:1521 (Oracle Database listener)
  - 5500:5500 (Enterprise Manager Express)
- **Environment Variables:**
  - ORACLE_PWD=oracle
  - ORACLE_CHARACTERSET=AL32UTF8
- **Volumes:**
  - apex-database-volume:/opt/oracle/oradata
- **Network:** apex-network
- **Hostname:** apexdatabase
- **Healthcheck:** SQL query to verify database is running

#### 2. Oracle ORDS (apex-ords)

- **Image:** `container-registry.oracle.com/database/ords:latest`
- **Purpose:** Provides the REST interface and hosts Oracle APEX application
- **Ports:**
  - 8080:8080 (Web interface)
- **Volumes:**
  - ./ords_secrets:/opt/oracle/variables
  - ./ords_config:/etc/ords/config
- **Network:** apex-network
- **Dependencies:** Waits for apex-database to be healthy before starting

#### 3. External Project Database (external-project-db)

- **External container** from another project
- **Purpose:** Contains external data that can be imported into the main project
- **Access:** Through its exposed ports (varies depending on configuration)

## Starting and Stopping Containers

### Starting All Containers

To start both project containers:

```bash
docker-compose up -d
```

This command starts the containers in detached mode. The `-d` flag runs the containers in the background.

### Stopping All Containers

To stop all project containers:

```bash
docker-compose down
```

This command stops and removes the containers, but preserves the volumes.

### Starting/Stopping Individual Containers

To start/stop individual containers:

```bash
# Start only the database
docker-compose up -d oracle-database

# Start only ORDS
docker-compose up -d oracle-ords

# Stop only the database
docker-compose stop oracle-database

# Stop only ORDS
docker-compose stop oracle-ords
```

## Accessing Containers

### Accessing Oracle Database Container

```bash
docker exec -it apex-database bash
```

Once inside the container, you can connect to the database using SQL*Plus:

```bash
sqlplus system/oracle@//localhost:1521/FREE
```

Or use the oracle_connect.sh script from the oracle_setup directory:

```bash
./oracle_setup/oracle_connect.sh
```

### Accessing ORDS Container

```bash
docker exec -it apex-ords bash
```

### Viewing Container Logs

```bash
# View database container logs
docker logs apex-database

# View ORDS container logs
docker logs apex-ords

# Follow logs in real-time
docker logs -f apex-database
```

## Accessing Oracle APEX

1. Start both containers:
   ```bash
   docker-compose up -d
   ```

2. Wait for both containers to fully initialize (check with `docker ps`)

3. Access APEX in your web browser:
   ```
   http://localhost:8080/ords/apex
   ```

4. Default login credentials:
   - Workspace: INTERNAL
   - Username: ADMIN
   - Password: oracle  (or as configured in setup scripts)

## Database Operations

### Checking Database Status

You can verify the database status using:

```bash
docker exec apex-database sqlplus -S / as sysdba @healthcheck.sql
```

Or check using the script in oracle_setup:

```bash
./oracle_setup/check_apex_status.sh
```

### Copying Database from External Container to Project Container

To copy a database from your external project container to the Wikipedia project database:

1. **Export the source database:**

   ```bash
   # Execute from your host machine
   docker exec -it external-project-db bash -c "expdp username/password@service_name \
     directory=DATA_PUMP_DIR dumpfile=export.dmp logfile=export.log \
     schemas=source_schema"
   ```

2. **Copy the dump file from source to destination:**

   ```bash
   # Create a temporary directory on your host
   mkdir -p temp_transfer
   
   # Copy from source container to host
   docker cp external-project-db:/opt/oracle/admin/XE/dpdump/export.dmp ./temp_transfer/
   
   # Copy from host to destination container
   docker cp ./temp_transfer/export.dmp apex-database:/opt/oracle/admin/FREE/dpdump/
   ```

3. **Import into the destination database:**

   ```bash
   docker exec -it apex-database bash -c "impdp system/oracle@//localhost:1521/FREE \
     directory=DATA_PUMP_DIR dumpfile=export.dmp logfile=import.log \
     remap_schema=source_schema:target_schema"
   ```

### Using Python Script for Database Copy

The project includes a specialized Python script for copying specific database schemas:

```bash
python src/db/copy_wiki_db.py --source_schema SOURCE_SCHEMA --target_schema TARGET_SCHEMA
```

This script:
- Creates a target schema if it doesn't exist
- Copies all tables, indexes, and constraints
- Preserves data integrity during the copy
- Optimizes the process for large datasets

## Troubleshooting

### Common Issues and Solutions

1. **Container fails to start:**
   - Check logs: `docker logs apex-database`
   - Verify ports are not already in use: `netstat -an | grep 1521`

2. **Cannot connect to database:**
   - Ensure the container is running: `docker ps`
   - Check the healthcheck status: `docker inspect apex-database | grep -A 10 Health`
   - Verify network connectivity: `docker network inspect apex-network`

3. **APEX is inaccessible:**
   - Ensure both containers are running: `docker ps`
   - Check ORDS logs: `docker logs apex-ords`
   - Verify ORDS is properly configured: `docker exec -it apex-ords ls -la /etc/ords/config`

### Resetting the Oracle APEX Password

If you need to reset the APEX admin password:

```bash
docker exec -it apex-database sqlplus -S / as sysdba @oracle_setup/set_apex_password.sql
```

### Recreating Containers

If you need to completely recreate the containers:

```bash
# Stop and remove containers, networks, and volumes
docker-compose down -v

# Recreate and start containers
docker-compose up -d
```

## Advanced Operations

### Running Custom SQL Scripts

To run custom SQL scripts against the database:

```bash
docker exec -i apex-database sqlplus username/password@//localhost:1521/FREE < your_script.sql
```

Or for scripts in the ETL_SQL directory:

```bash
docker exec -i apex-database sqlplus username/password@//localhost:1521/FREE < ETL_SQL/01_path_analysis.sql
```

### Database Backup and Restore

To backup the entire database:

```bash
docker exec -it apex-database bash -c "expdp system/oracle@//localhost:1521/FREE \
  full=y directory=DATA_PUMP_DIR dumpfile=fullbackup.dmp logfile=fullbackup.log"
```

To restore from a backup:

```bash
docker exec -it apex-database bash -c "impdp system/oracle@//localhost:1521/FREE \
  full=y directory=DATA_PUMP_DIR dumpfile=fullbackup.dmp logfile=fullrestore.log"
```

## Docker Compose Configuration

For reference, the docker-compose.yml file used to define the containers:

```yaml
version: '3'

services:
  oracle-database:
    container_name: apex-database
    image: container-registry.oracle.com/database/free:latest
    ports:
      - "1521:1521"
      - "5500:5500"
    environment:
      - ORACLE_PWD=oracle
      - ORACLE_CHARACTERSET=AL32UTF8
    volumes:
      - apex-database-volume:/opt/oracle/oradata
    networks:
      - apex-network
    hostname: apexdatabase
    healthcheck:
      test: ["CMD", "sqlplus", "-L", "sys/oracle@//localhost:1521/FREE as sysdba", "@healthcheck.sql"]
      interval: 30s
      timeout: 10s
      retries: 10

  oracle-ords:
    container_name: apex-ords
    image: container-registry.oracle.com/database/ords:latest
    ports:
      - "8080:8080"
    volumes:
      - ./ords_secrets:/opt/oracle/variables
      - ./ords_config:/etc/ords/config
    networks:
      - apex-network
    depends_on:
      oracle-database:
        condition: service_healthy

networks:
  apex-network:
    external: true

volumes:
  apex-database-volume:
    external: true 
```

The third container (external-project-db) is managed separately from this docker-compose file. 