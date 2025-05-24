# DSI321 Project
# CI Status
|  | |
| - | :- |
| Security | [![Bandit](https://github.com/Thanaraklee/dsi321_2025/actions/workflows/bandit.yml/badge.svg?branch=main)](https://github.com/Thanaraklee/dsi321_2025/actions/workflows/bandit.yml) [![CodeQL](https://github.com/Thanaraklee/dsi321_2025/actions/workflows/github-code-scanning/codeql/badge.svg)](https://github.com/Thanaraklee/dsi321_2025/actions/workflows/github-code-scanning/codeql) |
| Dataset Validation | [![Validation](https://github.com/Thanaraklee/dsi321_2025/actions/workflows/validation.yml/badge.svg)](https://github.com/Thanaraklee/dsi321_2025/actions/workflows/validation.yml) |

# Dataset Quality
| | |
| - | :- |
| Contains at least 1,000 records | [![Quality Row](https://github.com/Thanaraklee/dsi321_2025/actions/workflows/qa_row.yml/badge.svg)](https://github.com/Thanaraklee/dsi321_2025/actions/workflows/qa_row.yml) |
| Covers a full 24-hour time range | [![Quality Cover 24-hour](https://github.com/Thanaraklee/dsi321_2025/actions/workflows/qa_time.yml/badge.svg)](https://github.com/Thanaraklee/dsi321_2025/actions/workflows/qa_time.yml) |
| At least 90% data completeness | [![Quality Missing](https://github.com/Thanaraklee/dsi321_2025/actions/workflows/qa_missing.yml/badge.svg)](https://github.com/Thanaraklee/dsi321_2025/actions/workflows/qa_missing.yml) |
| No columns with data type 'object' | [![Quality Data Type](https://github.com/Thanaraklee/dsi321_2025/actions/workflows/qa_datatype.yml/badge.svg)](https://github.com/Thanaraklee/dsi321_2025/actions/workflows/qa_datatype.yml) |
| No duplicate records | [![Quality Duplicate](https://github.com/Thanaraklee/dsi321_2025/actions/workflows/qa_duplicate.yml/badge.svg)](https://github.com/Thanaraklee/dsi321_2025/actions/workflows/qa_duplicate.yml) |
- dataset (`data/data.parquet`)
# Overview
This system was developed to Track and analyze public data related to Thammasat University in academic terms using real-time data extraction and natural language processing (NLP) techniques to:
- Check comments and articles mentioning TU
- Analyze the sentiment and topic of the content
- Alert the PR department when important information is found
- Adjust the communication strategy to suit the situation
- Analyze the public opinion situation on the university

# Benefits
- **Educational Benefits**
    - Learn to implement a real-world data pipeline using Python and open-source tools.
    - Gain hands-on experience with Docker, lakeFS, Streamlit, and Prefect.
    - Understand CI/CD, data validation, and modular architecture in data engineering.

- **Practical Benefits**
    - Offers a working template for social media data collection and analysis.
    - Supports real-time incremental scraping with scheduled execution.
    - Easy deployment with Docker for both development and production environments.

- **Organizational Benefits**
    - Promotes reproducibility and scalability using lakeFS and orchestration tools.
    - Validated datasets ensure reliable business or academic insights.
    - Can be adapted for sentiment analysis, market research, or public opinion monitoring.

# Project Status
| Module / Tool | Status |
| - | :-: |
| Modern Logging (Logging, Rich) | ✅ |
| Web Scraping |✅|
| Database(LakeFS) | ✅ |
| Data Validation (Pydantic) | ✅ |
| Orchestration (Prefect) Part 1: All tweets|✅|
| Orchestration (Prefect) Part 2: Only new tweets|✅|
| ML (Word Cloud)|✅|
| Web Interface (Streamlit) |✅|

# Resources
- **Tools Used**
    - **Web Scraping**: Python `requests`, `Selenium` for X login/scraping
    - **Data Validation**: `Pydantic`
    - **Data Storage**: `lakeFS`
    - **Orchestration**: `Prefect`
    - **Visualization**: Stream`lit
    - **Logging**: `Rich`, Custom Logger
    - **CI/CD**: GitHub Actions (`Bandit`, `CodeQL`, Dataset Validation)

- **Hardware Requirements**
    - Docker-compatible environment
    - Local or cloud system with:
        - At least 4 GB RAM
        - Internet access for X data
        - Port availability for Prefect UI (default: `localhost:4200`)

# Risks and Mitigation Strategies
|**Risk**|**Description**|**Mitigation**|
|-|-|-|
|**API Rate Limit**| X API may enforce rate limits or ban IPs during scraping| Use randomized intervals, rotate IPs, or apply for API access|
|**ML Limitations**| Current ML component is a simple word cloud, which lacks depth | Extend with NLP (e.g., sentiment analysis, keyword clustering)|
|**Docker Setup Issues**| Misconfiguration may prevent services from running correctly   | Provide a well-documented `docker-compose.yml` and startup script (`start.sh`) |
|**Data Schema Drift**| Changes in X’s HTML/CSS may break scraping| Use robust selectors and frequently monitor scraping modules|
|**Validation Failures**| Malformed data might bypass or crash the pipeline| Enforce strict schema validation using Pydantic before storage|


# Project Structure
```
.
├── config                          # Configuration files for Docker, logging, and paths
│   ├── docker                        
│   │   ├── Dockerfile.cli          # Dockerfile for CLI usage
│   │   └── Dockerfile.worker       # Dockerfile for worker services
│   ├── logging
│   │   └── modern_log.py           # Custom logging configuration
│   └── path_config.py              # Path configuration for file management
├── src                             # Source code directory
│   ├── backend                     # Backend logic for scraping, validation, loading
│   │   ├── load
│   │   │   └── lakefs_loader.py    # Module for loading data to lakeFS
│   │   ├── pipeline
│   │   │   ├── incremental_scrape_flow.py   # Scraping flow for incremental data
│   │   │   └── initial_scrape_flow.py       # Scraping flow for initial/full data
│   │   ├── scraping
│   │   │   ├── x_login.py          # Script to log in to X 
│   │   │   └── x_scraping.py       # Script to scrape data from X
│   │   └── validation
│   │   │   └── validate.py         # Data validation logic
│   └── fronend                     # Frontend components (Note: typo, should be "frontend")
│       └── streamlit.py            # Streamlit app for data display
├── test                            # Unit and integration test files
├── .env.example                    # Example of environment variable file
├── .gitignore                      # Git ignore rules
├── README.md                       # Project documentation
├── docker-compose.yml              # Docker Compose configuration
├── pyproject.toml                  # Python project configuration
├── requirements.txt                # Python package requirements
└── start.sh                        # Startup script for the project
```



# Prepare
1. Create a virtual environment
```bash
python -m venv .venv
```
2. Activate the virtual environment
    - Windows
        ```bash
        source .venv/Scripts/activate
        ```
    - macOS & Linux
        ```bash
        source .venv/bin/activate
        ```
3. Run the startup script
```bash
bash start.sh
# or
./start.sh
```

# Running Prefect
1. Start the Prefect server
```bash
docker compose --profile server up -d
```
2. Connect to the CLI container
```bash
docker compose run cli
```
3. Run the initial scraping flow (to collect all tweets for base data)
```bash
python src/backend/pipeline/initial_scrape_flow.py
```
4. Schedule scraping every 15 minutes (incremental updates)
```bash
python src/backend/pipeline/incremental_scrape_flow.py
```
- **View the Prefect flow UI**
Open your browser and go to: http://localhost:42000 
