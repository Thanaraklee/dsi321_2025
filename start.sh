#!/bin/bash

# Install dependencies
pip install -r requirements.txt 

# Install the package in editable mode
pip install -e .

# Install Playwright browsers
playwright install

# Login to X
python code/backend/scraping/x_login.py