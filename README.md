# Wikipedia Path Analysis with Oracle Database

## Project Overview

This project explores the fascinating phenomenon of Wikipedia's "first link" paths—where following the first link in each article often leads to the Philosophy page. The system is designed to crawl Wikipedia, store article paths in an Oracle database, and generate rich visualizations and reports to analyze the resulting network.

## Technical Journey

### 1. Initial Setup
- **Database**: Deployed Oracle 21c XE using Docker for a robust, production-grade relational backend.
- **Schema Design**: Created normalized tables for paths (`WIKI_PATHS`) and path nodes (`WIKI_PATH_NODES`), supporting efficient queries and analytics.
- **Python Integration**: Developed Python scripts for crawling, data storage, and analysis, using `oracledb`, `pandas`, `networkx`, and `matplotlib`.

### 2. Data Collection & Crawler Evolution
- **Crawling Logic**: Implemented a multi-threaded crawler that follows the first link in each Wikipedia article, storing each path and its nodes in the database.
- **Batch & Timed Crawls**: Ran small test batches, then scaled up to large, timed crawls (5+ hours) to collect tens of thousands of paths.
- **Error Handling**: Addressed issues with Oracle's case-sensitive column names and schema selection, ensuring all data was stored and queried from the correct schema.

### 3. Debugging & Problem Solving
- **Schema Mismatches**: Discovered that data was split between two schemas (`SYSTEM` and `WIKI_USER`). Refactored all queries and scripts to always select the schema with the most data, ensuring consistency and completeness.
- **Visualization Issues**: Fixed bugs in the visualization scripts to handle large graphs, edge attributes, and Oracle's SQL quirks.
- **Dependency Management**: Ensured all required Python libraries (including `scipy` for network analysis) were installed and compatible.

### 4. Analysis & Reporting
- **Visualizations**: Generated bar charts, network graphs (spring and circular layouts), and path length histograms to reveal key patterns in the data.
- **HTML Report**: Built a comprehensive, interactive HTML report using Jinja2 templates, combining statistics, sample paths, and all visualizations.
- **Automation**: Finalized scripts so that running `python visualize_wiki_data.py` and `python generate_wiki_report.py` always produces an up-to-date, recruiter-ready report.

## How to Use

1. **Start Oracle XE with Docker** (see `DOCUMENTATION.md` for details).
2. **Run the Crawler**: Use the provided scripts to collect Wikipedia paths into the database.
3. **Generate Visualizations**:
   ```bash
   python visualize_wiki_data.py
   ```
4. **Generate the Report**:
   ```bash
   python generate_wiki_report.py
   open reports/wiki_path_report.html
   ```

## What You'll See
- **Key statistics**: Total paths, unique articles, network size, density, and more.
- **Visualizations**: Article frequency, network structure, and path length distributions.
- **Sample paths**: Real examples of how Wikipedia articles connect.

## Lessons Learned
- **Production-Grade Data Engineering**: Handling real-world database quirks, schema management, and large-scale data collection.
- **Network Science**: Applying graph theory to real Wikipedia data.
- **Automation & Reporting**: Building a pipeline from raw crawl to polished, interactive report.

---

This project is a showcase of end-to-end data engineering, network analysis, and robust Python/SQL integration. Perfect for demonstrating technical depth, problem-solving, and the ability to deliver production-ready analytics. 