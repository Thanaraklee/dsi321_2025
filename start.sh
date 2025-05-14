#!/bin/bash
# This script is used to set up a Python virtual environment and install the required packages for the project.

if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python -m venv .venv
else
    echo "Virtual environment already exists."
fi

# Activate the virtual environment
# Check the operating system and activate the virtual environment accordingly
if [[ "$OSTYPE" == "darwin"* ]]; then
  # For macOS
  source .venv/bin/activate
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
  # For Linux
  source .venv/bin/activate
elif [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" ]]; then
  # For Windows (Git Bash or Cygwin)
  source .venv/Scripts/activate
else
  echo "Unsupported operating system: $OSTYPE"
  exit 1
fi

echo "== Step 1: Install Python dependencies =="
read -p "Install dependencies from requirements.txt? (y/n): " install_req
if [[ $install_req == "y" ]]; then
    python -m pip install --upgrade pip
    python -m pip install -r requirements.txt
    pip install -e .
fi

echo "== Step 2: Install Playwright Browsers =="
read -p "Install Playwright browsers? (y/n): " install_playwright
if [[ $install_playwright == "y" ]]; then
    playwright install
fi

echo "== Step 3: Environment File =="
if [ -f ".env.example" ] && [ ! -f ".env" ]; then
    read -p "Copy .env.example to .env? (y/n): " copy_env
    if [[ $copy_env == "y" ]]; then
        cp .env.example .env
    fi
fi

echo "== Step 4: X Login =="
read -p "Run login to X now? (y/n): " login_x
if [[ $login_x == "y" ]]; then
    python src/backend/scraping/x_login.py
fi

echo "== Step 5: Docker Compose (server) =="
read -p "Start Docker containers with --profile server? (y/n): " start_server
if [[ $start_server == "y" ]]; then
    docker compose --profile server up -d
fi

echo "== Step 6: Docker Compose (worker) =="
read -p "Start Docker containers with --profile worker (build)? (y/n): " start_worker
if [[ $start_worker == "y" ]]; then
    docker compose --profile worker up --build -d
fi

echo "== Step 7: Run CLI Container =="
read -p "Run CLI Container? (y/n): " run_initial
if [[ $run_initial == "y" ]]; then
    docker compose run cli
fi


echo "✅ Setup complete."
