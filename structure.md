# Wikipedia Link Network Project Structure

This document provides a detailed overview of the project structure after cleanup and reorganization. 

## Overview

The project explores Wikipedia's hyperlink network to understand navigational patterns, particularly focusing on the hypothesis that most paths lead to the Philosophy article when following the first non-parenthesized link. 

The codebase has been reorganized into a logical directory structure with clear separation of concerns:

```
.
├── docker-compose.yml       # Docker configuration for Oracle and ORDS
├── Dockerfile               # Docker image for the crawler application
├── entrypoint.sh            # Container entrypoint script
├── ETL_SQL/                 # SQL analysis scripts
├── images/                  # Visualization images
│   └── graphs/              # Network graph visualizations
├── logs/                    # Application logs
├── old_files/               # Archived unnecessary/duplicate files
├── oracle_apex/             # Oracle APEX installation files
├── oracle_setup/            # Oracle DB and APEX setup scripts
├── ords_config/             # ORDS configuration files
├── ords_secrets/            # ORDS connection credentials
├── reports/                 # Analysis reports and HTML outputs
├── requirements.txt         # Python dependencies
├── scripts/                 # Shell scripts for running crawlers
└── src/                     # Source code
    ├── analysis/            # Path analysis scripts
    ├── crawlers/            # Wikipedia crawler implementations
    ├── dashboard/           # Visualization dashboard
    ├── db/                  # Database utilities
    ├── wiki_core.py         # Core Wikipedia crawler functionality
    └── wiki_single_article.py # Single article crawler
```

## Core Components in Detail

### Docker Setup

- **docker-compose.yml** (1015B): Docker Compose configuration that defines two containers:
  - `oracle-database`: Oracle database container with proper configuration for APEX
  - `oracle-ords`: Oracle REST Data Services container for web interfaces
  
- **Dockerfile** (934B): Defines the application container with Python dependencies for the Wikipedia crawler
  
- **entrypoint.sh** (995B): Container entrypoint script that initializes the application environment and starts the crawler

### Source Code (`src/`)

#### Core Modules

- **wiki_core.py** (15KB): Core functionality for Wikipedia article parsing and link extraction. Contains classes and functions for:
  - HTML parsing of Wikipedia pages
  - Link extraction algorithms
  - Content filtering
  - Path tracking logic
  
- **wiki_single_article.py** (2.3KB): Simplified version for crawling a single article and its immediate links. Used for testing and specific article analysis.

#### Crawlers (`src/crawlers/`)

- **parallel_wiki_crawler.py** (22KB): Multi-threaded crawler that processes multiple article paths concurrently. Features:
  - Thread pool management
  - Connection pooling for database access
  - Work queue implementation
  - Rate limiting to avoid Wikipedia API restrictions
  
- **large_wiki_graph_crawler.py** (24KB): Enhanced crawler for large-scale data collection. Additional features:
  - Memory-efficient graph representation
  - Incremental database commits
  - Checkpoint/resume capability
  - Performance monitoring

#### Database Utilities (`src/db/`)

- **copy_wiki_db.py** (9.6KB): Creates an analytical copy of the production database to allow analysis without affecting ongoing data collection. Implements:
  - Schema duplication
  - Data copying with optimized performance
  - Index rebuilding
  - Statistics gathering
  
- **wiki_db_storage.py** (8.0KB): Database access layer for storing crawler results. Handles:
  - Connection management
  - Transaction control
  - Bulk inserts
  - Data integrity checks
  
- **query_database.py** (8.1KB): Utility for executing analytical queries against the database. Provides:
  - Query execution framework
  - Result formatting
  - Query performance statistics
  - Parameterized query support

#### Analysis (`src/analysis/`)

- **analyze_wiki_paths.py** (12KB): Comprehensive path analysis tool that processes the collected data to:
  - Calculate path statistics
  - Identify common patterns
  - Detect key articles in the network
  - Generate reports on path distributions

#### Dashboard (`src/dashboard/`)

- **wiki_dashboard.py** (28KB): Visualization dashboard for the Wikipedia path analysis. Features:
  - Interactive path exploration
  - Network visualization
  - Statistical summaries
  - Export functionality for reports and images

### Scripts (`scripts/`)

- **run_crawler.sh** (3.6KB): Shell script for executing the standard Wikipedia crawler with:
  - Command-line parameter handling
  - Environment setup
  - Logging configuration
  - Error handling
  
- **run_large_crawler.sh** (2.4KB): Script for running the large-scale crawler with:
  - Resource allocation settings
  - Extended runtime configuration
  - Monitoring setup
  - Checkpoint management

### SQL Analysis (`ETL_SQL/`)

- **01_path_analysis.sql** (3.2KB): Basic path metrics and statistics
- **02_network_analysis.sql** (8.3KB): Graph analysis for node importance and connectivity
- **03_statistical_analysis.sql** (15KB): Advanced statistical measures and distributions
- **04_data_modeling.sql** (16KB): Star schema and dimensional modeling for analytics
- **05_big_data_techniques.sql** (14KB): Performance optimization for large datasets
- **06_business_intelligence_dashboard.sql** (20KB): SQL for dashboard visualizations
- **07_oracle_apex_visualizations.sql** (23KB): Integration with Oracle APEX for web-based reporting
- **README.md** (8.1KB): Documentation of the SQL analysis framework
- **WIKI_ANALYSIS_REPORT.md** (10KB): Analytical findings and interpretations

### Oracle Setup (`oracle_setup/`)

- **check_apex_status.sh** (798B): Script to verify Oracle APEX installation status
- **oracle_connect.sh** (179B): Utility script for connecting to Oracle database
- **00_start_apex_ords_installer.sh** (93B): Initiates APEX and ORDS installation
- **unattended_apex_install_23c.sh** (4.5KB): Automated APEX installation script
- **healthcheck.sql** (81B): SQL script for database health verification

### Oracle APEX (`oracle_apex/`)

- **apex_23.1.zip** (244MB): Oracle APEX installation package
- **apex/** directory: Extracted APEX files for installation
- **META-INF/** directory: APEX metadata
- **apex_install.log**: Installation log file

### ORDS Setup

- **ords_config/**: Oracle REST Data Services configuration directory
- **ords_secrets/conn_string.txt** (50B): Connection string for ORDS to database

### Images and Visualizations

- **images/graphs/**: Network visualization graphs:
  - **wiki_path_network.png** (488KB): Complete network visualization
  - **common_endpoints.png** (35KB): Frequently reached articles
  - **common_articles.png** (53KB): Articles appearing in many paths
  - **path_length_distribution.png** (32KB): Statistical distribution of path lengths
  
- **images/**: Path examples:
  - **Python_to_philosophy.png** (285KB): Path from Python article to Philosophy
  - **Computer_to_philosophy.png** (342KB): Path from Computer article to Philosophy
  - **Banana_to_philosophy.png** (280KB): Path from Banana article to Philosophy
  - **wiki_specific_graph.png** (280KB): Specific subgraph visualization
  - **complete_path.png** (114KB): Example of a complete path visualization

### Reports (`reports/`)

- **wiki_path_analysis.html** (3.7KB): HTML report with interactive visualizations

### Other Files

- **requirements.txt** (134B): Python package dependencies for the project
- **README.md** (6.8KB): Project overview and documentation

## Old Files Archive (`old_files/`)

The `old_files` directory contains files that were deemed unnecessary, duplicate, or obsolete during the project cleanup:

### Backup Files

All `.bak` files were moved to this directory. These are backup copies of the main Python scripts:
- **analyze_wiki_paths.py.bak** (12KB)
- **check_football_paths.py.bak** (2.6KB)
- **check_paths.py.bak** (3.5KB)
- **check_philosophy_paths.py.bak** (4.6KB)
- **check_wiki_tables.py.bak** (3.1KB)
- **copy_wiki_db.py.bak** (9.6KB)
- **drop_tables.py.bak** (2.5KB)
- **query_database.py.bak** (8.1KB)
- **test_database.py.bak** (3.5KB)
- **update_analysis_scripts.py.bak** (3.0KB)
- **verify_database_clone.py.bak** (3.7KB)
- **wiki_dashboard.py.bak** (28KB)
- **wiki_db_storage.py.bak** (8.0KB)

### Utility Scripts (`old_files/utility_scripts/`)

Utility scripts that are no longer needed or have been replaced by more comprehensive solutions:
- **drop_tables.py** (2.5KB): Script for dropping database tables, no longer needed for regular operations
- **test_database.py** (3.4KB): Basic database connection testing, superseded by more robust solutions
- **update_analysis_scripts.py** (3.0KB): Script for updating analysis scripts, now managed through source control
- **verify_database_clone.py** (3.7KB): Database clone verification, integrated into the main copy_wiki_db.py

### Path Checking Scripts (`old_files/path_check_scripts/`)

Various specialized path checking scripts that have been consolidated into the main analysis framework:
- **check_football_paths.py** (2.6KB): Specialized script for football-related articles
- **check_philosophy_paths.py** (4.6KB): Script focused specifically on paths to Philosophy
- **check_paths.py** (3.5KB): Generic path checking utility
- **check_wiki_tables.py** (3.0KB): Database table verification for wiki paths
- **science_path_verifier.py** (4.8KB): Verification script for science-related article paths
- **science_path_visualizer.py** (2.2KB): Specialized visualization for science paths

### Database Scripts (`old_files/database_scripts/`)

Database management scripts that have been replaced or are no longer needed:
- **clone_database.sh** (2.0KB): Shell script for database cloning, replaced by copy_wiki_db.py
- **rman_clone_database.sh** (2.4KB): Oracle RMAN-based cloning script, not used in current workflow
- **export_wiki_data.sh** (4.2KB): Data export script, functionality now in the main application

### APEX Admin Scripts (`old_files/apex_admin_scripts/`)

Oracle APEX administration scripts that are not needed for regular operation:
- **simple_admin_reset.sql** (1.1KB): APEX admin password reset script
- **disable_complexity_requirements.sql** (1.5KB): Script to disable password complexity requirements
- **create_admin_user.sql** (875B): Admin user creation script
- **edit_password_requirements.sql** (1.6KB): Password policy modification script
- **set_apex_password_secure.sql** (666B): Secure password setting script
- **set_apex_password.sql** (493B): Basic password setting script
- **reset_apex_admin_fixed.sql** (580B): Fixed version of admin reset script
- **setup_apex_listener_fixed.sql** (430B): Fixed APEX listener setup
- **reset_apex_admin.sql** (646B): Admin reset script
- **setup_apex_listener.sql** (343B): APEX listener setup script
- **check_apex.sql** (463B): APEX installation verification script

### Logs (`old_files/logs/`)

- **nohup.out** (44GB): Very large log file from previous crawler runs, archived to save space

### Miscellaneous

- **Oracle install files/**: Directory containing Oracle installation files, moved to archive as installation is complete
- **.DS_Store** (12KB): macOS file system metadata file, not relevant to the project

## Relationships Between Components

### Data Flow

1. The **crawlers** (src/crawlers/) collect Wikipedia path data using the core functionality in **wiki_core.py**
2. Data is stored in the Oracle database via **wiki_db_storage.py**
3. The **analysis** scripts process this data to extract insights
4. **ETL_SQL** scripts perform advanced analytics on the database
5. Results are visualized through the **dashboard** or exported as reports

### Execution Flow

1. **docker-compose.yml** starts the Oracle and ORDS containers
2. **scripts/run_crawler.sh** or **scripts/run_large_crawler.sh** initiates the data collection
3. Database copy is created via **src/db/copy_wiki_db.py** for analysis
4. SQL analysis is performed using scripts in **ETL_SQL/**
5. Results are visualized using **src/dashboard/wiki_dashboard.py**

## Conclusion

This project has been reorganized from a messy structure into a clean, logical hierarchy. The key improvements include:

1. Clear separation of concerns with dedicated directories for specific functionality
2. Removal of duplicate and obsolete files to the old_files directory
3. Logical grouping of related functionality
4. Improved documentation in README.md and this structure.md
5. Better organization of visualization assets and reports

The new structure makes the project more maintainable, easier to understand, and better prepared for future development. 