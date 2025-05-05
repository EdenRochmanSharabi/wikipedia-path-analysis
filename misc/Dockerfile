FROM ubuntu:22.04

# Install basic utilities
RUN apt-get update && \
    apt-get install -y libaio1 wget unzip python3 python3-pip && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Set environment variables
ENV ORACLE_HOME=/opt/oracle/instantclient
ENV LD_LIBRARY_PATH=$ORACLE_HOME:$LD_LIBRARY_PATH
ENV PATH=$ORACLE_HOME:$PATH
ENV TNS_ADMIN=$ORACLE_HOME/network/admin

# Create directory for Oracle client
RUN mkdir -p $ORACLE_HOME

# Copy Oracle installation files
COPY ["Oracle install files", "/tmp/oracle"]

# We'll install the client files in the entrypoint script
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Install Python Oracle client
RUN pip3 install oracledb

WORKDIR /app

# Copy Python scripts
COPY copy_wiki_db.py /app/
COPY update_analysis_scripts.py /app/
COPY check_paths.py /app/
COPY check_football_paths.py /app/
COPY check_philosophy_paths.py /app/

ENTRYPOINT ["/entrypoint.sh"] 