#!/bin/bash

# Install dependencies
pip install -r requirements.txt 

# Install the package in editable mode
pip install -e .

# Install Playwright browsers
playwright install

# Rename the example environment file
mv .env.example .env

# Login to X
python code/backend/scraping/x_login.py