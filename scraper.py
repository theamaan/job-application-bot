import json
import time
from selenium import webdriver
from selenium.webdriver.edge.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def load_config(path: str = "config.json") -> dict:
    """Load and return the configuration parameters."""
    with open(path) as f:
        return json.load(f)

def init_driver() -> webdriver.Edge:
    """Instantiate a headless Edge browser with necessary options."""
    options = Options()
    options.use_chromium = True
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-gpu")
    # Create and return the Edge WebDriver
    return webdriver.Edge(options=options)

def scrape_jobs() -> list:
    """
    Scrape job listings from Indeed.in for each title-location pair
    defined in config.json. Returns a list of job dictionaries.
    """
    cfg = load_config()
    driver = init_driver()
    results = []

    for title in cfg["job_titles"]:
        for loc in cfg["locations"]:
            # 1. Build the search URL
            query_title = title.replace(" ", "+")
            query_loc = loc.replace(" ", "+")
            url = f"https://in.indeed.com/jobs?q={query_title}&l={query_loc}"
            
            # 2. Navigate to the URL
            driver.get(url)

            # 3. Wait until job cards are present (explicit wait)
            try:
                cards = WebDriverWait(driver, 10).until(
                    EC.presence_of_all_elements_located(
                        (By.CSS_SELECTOR, "li.job_seen_beacon")
                    )
                )
            except Exception:
                # If no cards within 10s, skip this combination
                continue

            # 4. Iterate through each job card on first page
            for card in cards:
                # Extract basic fields with graceful fallback
                title_el   = card.find_element(By.CSS_SELECTOR, "h2.title")
                comp_el    = card.find_element(By.CSS_SELECTOR, "span.company")
                loc_el     = card.find_element(By.CSS_SELECTOR, "div.location") \
                            if card.find_elements(By.CSS_SELECTOR, "div.location") else None
                sal_el     = card.find_element(By.CSS_SELECTOR, "span.salaryText") \
                            if card.find_elements(By.CSS_SELECTOR, "span.salaryText") else None
                date_el    = card.find_element(By.CSS_SELECTOR, "span.date")
                
                job = {
                    "id": card.get_attribute("data-jk"),
                    "title": title_el.text.strip(),
                    "company": comp_el.text.strip(),
                    "location": loc_el.text.strip() if loc_el else "N/A",
                    "salary": int(sal_el.text.replace("₹", "").replace(",", "").split()[0])
                              if sal_el and "₹" in sal_el.text else None,
                    "skills": [],  # To be filled later or by filtering logic
                    "description": "",  # Detailed scraping can be added subsequently
                    "valid_until": "",  # Indeed does not provide expiry date here
                }
                results.append(job)

            # Be polite: wait a moment before next search
            time.sleep(2)

    driver.quit()
    return results
