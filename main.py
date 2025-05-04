import json
from filter_jobs import load_config, filter_jobs
from scraper import scrape_jobs

def main():
    # 1. Load configuration
    config = load_config("config.json")

    # 2. Scrape real job listings via Selenium + Edge
    jobs = scrape_jobs()

    # 3. Filter the scraped job list
    result = filter_jobs(jobs, config)

    # 4. Persist output to JSON file
    with open("output.json", "w") as f:
        json.dump(result, f, indent=2)

    print("Job scraping and filtering complete. See 'output.json' for results.")

if __name__ == "__main__":
    main()

