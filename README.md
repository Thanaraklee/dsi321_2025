# DSI321
# CI Status
|  | |
| - | :-: |
| Security | [![Bandit](https://github.com/Thanaraklee/dsi321_2025/actions/workflows/bandit.yml/badge.svg?branch=main)](https://github.com/Thanaraklee/dsi321_2025/actions/workflows/bandit.yml) |

# Project Status
| Module / Tool | Status |
| - | :-: |
| Modern Logging (Logging, Rich) | ✅ |
| Web Scraping |✅|
| Database(LakeFS) | ✅ |
| Data Validation (Pydantic) | ✅ |
| Web Interface (Streamlit) |        |
| Orchestration (Prefect) |        |

# Dataset Quality
<!-- validation-report -->
| Check | Status |
|-------|--------|| [bold red]✘[/bold red] Record Count (≥1000) records: 25 | ❌ || [green]✔ Time Span (≥24 hours) min: 2024-10-23 00:00:00 max: 2025-05-01 00:00:00[/green] | ✅ || [green]✔ No Missing Values missing: 0[/green] | ✅ || [bold red]✘[/bold red] No 'object' dtype columns columns: username: object, tweetText: object, scrapeTime: object, tag: object, postTimeRaw: object, postTime: object | ❌ || [green]✔ No Duplicate Rows duplicates: 0[/green] | ✅ |
| Check | Status |\n|-------|--------|\n| [bold red]✘[/bold red] Record Count (≥1000) records: 25 | ❌ |\n| [green]✔ Time Span (≥24 hours) min: 2024-10-23 00:00:00 max: 2025-05-01 00:00:00[/green] | ✅ |\n| [green]✔ No Missing Values missing: 0[/green] | ✅ |\n| [bold red]✘[/bold red] No 'object' dtype columns columns: username: object, tweetText: object, scrapeTime: object, tag: object, postTimeRaw: object, postTime: object | ❌ |\n| [green]✔ No Duplicate Rows duplicates: 0[/green] | ✅ |\n

# Prepare
1. Create environment
```bash
python -m venv .venv
```

2. Activate your environment
    - Windows
        ```bash
        source .venv/Scripts/activate
        ```
    - MacOS & Linux 
        ```bash
        source .venv/bin/activate
        ```
3. Run script
```bash
bash start.sh
# or
./start.sh
```
