import json
import datetime
import pytz
import logging
from typing import List, Dict

#─────────────────────────────────────────────────#
# Configure logging to capture filtering decisions
logging.basicConfig(
    filename='logs/filter.log',
    filemode='a',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
#─────────────────────────────────────────────────#

def load_config(path: str = "config.json") -> Dict:
    """Load and parse the JSON configuration file."""
    try:
        with open(path) as f:
            return json.load(f)
    except Exception as e:
        logging.warning(f"Could not load config.json: {e}")
        return {}

def skill_match(job_skills: List[str], required_skills: List[str]) -> int:
    """Compute percentage of required skills present."""
    if not job_skills:
        return 0
    matched = set(s.lower() for s in job_skills) & set(r.lower() for r in required_skills)
    return int((len(matched) / len(required_skills)) * 100)

def is_within_salary(salary: int, cfg: Dict) -> bool:
    """Check salary falls within configured bounds."""
    if salary is None:
        return False
    low, high = cfg["salary_range"]["min"], cfg["salary_range"]["max"]
    return low <= salary <= high

def is_within_radius(location: str, cfg_locations: List[str]) -> bool:
    """Simple substring match for allowed locations."""
    return any(city.lower() in location.lower() for city in cfg_locations)

def is_priority(job: Dict) -> bool:
    """Flag listings with urgent keywords."""
    terms = ['urgent', 'immediate joiner', 'priority']
    return any(t in job.get("description", "").lower() for t in terms)

def convert_time(utc_string: str, target_tz: str) -> str:
    """Convert UTC timestamp to date in target timezone."""
    try:
        utc_dt = datetime.datetime.strptime(utc_string, "%Y-%m-%dT%H:%M:%SZ")
        local = utc_dt.replace(tzinfo=pytz.UTC).astimezone(pytz.timezone(target_tz))
        return local.strftime("%Y-%m-%d")
    except Exception:
        return "N/A"

def filter_jobs(jobs: List[Dict], cfg: Dict) -> Dict:
    """Apply filters and return matched jobs with stats."""
    matched = []
    total = len(jobs)
    # Read or initialize cache of seen job IDs
    try:
        with open("cache.txt") as c:
            seen = set(c.read().splitlines())
    except FileNotFoundError:
        seen = set()
        open("cache.txt", "w").close()

    for job in jobs:
        jid    = job.get("id", job.get("title", ""))
        comp   = job.get("company", "")
        sal    = job.get("salary", 0)
        loc    = job.get("location", "")
        skills = job.get("skills", [])
        expiry = job.get("valid_until", "")

        # Skip blacklisted companies
        if comp in cfg.get("blocklist_companies", []):
            logging.info(f"Skip {jid}: company blocked")
            continue
        # Skip already seen jobs
        if jid in seen:
            logging.info(f"Skip {jid}: already processed")
            continue
        # Salary filter
        if not is_within_salary(sal, cfg):
            logging.info(f"Skip {jid}: salary {sal} out of range")
            continue
        # Location filter
        if not is_within_radius(loc, cfg["locations"]):
            logging.info(f"Skip {jid}: location {loc} not desired")
            continue

        # Compute skill match score
        score = skill_match(skills, cfg["required_skills"])
        if score < 60:
            logging.info(f"Skip {jid}: low skill match {score}%")
            continue

        # Passed all filters → record it
        matched.append({
            "title": job.get("title", ""),
            "match_score": score,
            "salary_compliance": True,
            "priority": "high" if is_priority(job) else "normal",
            "valid_until": convert_time(expiry, cfg["timezone"])
        })

        # Add to cache
        with open("cache.txt", "a") as c:
            c.write(jid + "\n")

    return {
        "matched_jobs": matched,
        "stats": {
            "total_scraped": total,
            "filtered": len(matched),
            "match_rate": f"{int(len(matched)/total*100)}%"
        }
    }
