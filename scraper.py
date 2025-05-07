import json
import time
import logging
import sys
import argparse
import random
from typing import Dict, Any, List
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException
from selenium_stealth import stealth

logger = logging.getLogger(__name__)

def configure_logging(log_level: str = "INFO") -> None:
    """Configure logging with file and console handlers."""
    logger.setLevel(log_level)
    
    if logger.hasHandlers():
        logger.handlers.clear()

    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    ch = logging.StreamHandler()
    ch.setFormatter(formatter)
    
    fh = logging.FileHandler('jobs_scraper.log')
    fh.setFormatter(formatter)

    logger.addHandler(ch)
    logger.addHandler(fh)

def load_config():
    """Load configuration file with validation."""
    logger.debug("Loading configuration from: %s", path)
    try:
        with open(path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        required_keys = {'job_titles', 'locations'}
        if not required_keys.issubset(config.keys()):
            raise ValueError("Missing required config keys")
        
        logger.info("Loaded %d job titles and %d locations",
                   len(config['job_titles']), len(config['locations']))
        return config
    except Exception as e:
        logger.error("Config load failed: %s", str(e), exc_info=True)
        raise

def init_driver() -> webdriver.Chrome:
    """Initialize headless Chrome driver with stealth settings."""
    logger.debug("Initializing WebDriver")
    try:
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--log-level=3")
        options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        driver = webdriver.Chrome(options=options)
        stealth(driver,
                languages=["en-US", "en"],
                vendor="Google Inc.",
                platform="Win32",
                webgl_vendor="Intel Inc.",
                renderer="Intel Iris OpenGL Engine",
                fix_hairline=True)
        driver.set_page_load_timeout(30)
        logger.info("WebDriver initialized successfully")
        return driver
    except Exception as e:
        logger.critical("Driver initialization failed: %s", str(e), exc_info=True)
        raise

def parse_salary(salary_text: str) -> int:
    """Parse salary text to extract numerical value."""
    if not salary_text:
        return None
    cleaned = salary_text.replace('₹', '').replace(',', '')
    parts = cleaned.split()
    if parts:
        try:
            return int(parts[0])
        except ValueError:
            return None
    return None

def scrape_jobs() -> List[Dict[str, Any]]:
    """Main scraping function with optimized execution flow."""
    logger.info("Starting job scraping process")
    driver = None
    results = []
    
    try:
        config = load_config()
        driver = init_driver()

        for title in config['job_titles']:
            logger.info("Processing job title: '%s'", title)
            
            for location in config['locations']:
                logger.info("Searching in location: '%s'", location)
                
                search_url = (
                    "https://example.com/search?"
                    f"q={title.replace(' ', '+')}"
                    f"&l={location.replace(' ', '+')}"
                )
                logger.debug("Generated search URL: %s", search_url)

                try:
                    driver.get(search_url)
                    time.sleep(random.uniform(2, 5))
                    WebDriverWait(driver, 15).until(
                        EC.presence_of_element_located((By.ID, "mosaic-provider-jobcards"))
                    )
                    
                    job_cards_data = driver.execute_script('return window.mosaic.providerData["mosaic-provider-jobcards"];')
                    if job_cards_data:
                        jobs = job_cards_data.get("metaData", {}).get("mosaicProviderJobCardsModel", {}).get("results", [])
                        logger.info("Found %d job listings", len(jobs))
                        for job in jobs:
                            job_data = {}
                            job_data['id'] = job.get("jobKey")
                            job_data['title'] = job.get("jobTitle")
                            job_data['company'] = job.get("companyName")
                            job_data['location'] = job.get("formattedLocation")
                            salary = job.get("salarySnippet", {}).get("text")
                            job_data['salary'] = parse_salary(salary) if salary else None
                            job_data['url'] = f"https://example.com/job/{job_data['id']}"
                            if job_data['id']:
                                results.append(job_data)
                                logger.debug("Processed job: %s", job_data['id'])
                    else:
                        logger.warning("No job cards data found for %s in %s", title, location)
                    
                    time.sleep(random.uniform(1, 3))

                except Exception as e:
                    logger.warning("Search failed for %s in %s: %s", title, location, str(e))
                    continue

        logger.info("Completed scraping. Total jobs collected: %d", len(results))
        return results

    except Exception as e:
        logger.critical("Scraping process failed: %s", str(e), exc_info=True)
        raise
    finally:
        if driver:
            driver.quit()
            logger.info("WebDriver resources released")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Indeed Job Scraper')
    parser.add_argument('--log-level', default='INFO',
                        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
                        help='Set logging verbosity level')
    
    args = parser.parse_args()
    
    configure_logging(args.log_level.upper())
    
    try:
        logger.info("Script execution started")
        jobs = scrape_jobs()
        logger.info("Script completed successfully. Jobs found: %d", len(jobs))
        sys.exit(0)
    except Exception as e:
        logger.critical("Fatal error terminated execution: %s", str(e))
        sys.exit(1)
