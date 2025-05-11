
echo "== Run initial scrape flow =="
read -p "Run initial scrape flow? (y/n): " run_initial
if [[ $run_initial == "y" ]]; then
    python src/backend/pipeline/initial_scrape_flow.py
fi

echo "== Run incremental scrape flow =="
read -p "Run incremental scrape flow? (y/n): " run_incremental
if [[ $run_incremental == "y" ]]; then
    python src/backend/pipeline/incremental_scrape_flow.py
fi