# DSI321
# CI Status
|  | |
| - | :- |
| Security | [![Bandit](https://github.com/Thanaraklee/dsi321_2025/actions/workflows/bandit.yml/badge.svg?branch=main)](https://github.com/Thanaraklee/dsi321_2025/actions/workflows/bandit.yml) [![CodeQL](https://github.com/Thanaraklee/dsi321_2025/actions/workflows/github-code-scanning/codeql/badge.svg)](https://github.com/Thanaraklee/dsi321_2025/actions/workflows/github-code-scanning/codeql) |
| Dataset Validation | [![Validation](https://github.com/Thanaraklee/dsi321_2025/actions/workflows/validation.yml/badge.svg)](https://github.com/Thanaraklee/dsi321_2025/actions/workflows/validation.yml) |

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
| Web Interface (Streamlit) |   |

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
