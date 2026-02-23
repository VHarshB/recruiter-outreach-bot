# scraper.py
# ================================================================
#  FINDS FRESH INTERNSHIP POSTINGS — runs once per day
#
#  Sources:
#    1. GitHub SimplifyJobs (community list, updated daily)
#    2. Simplify.jobs new postings feed
#    3. Indeed RSS feed (public, no login needed)
#    4. JobSpy library (searches Indeed + Google Jobs at once)
#
#  Returns a clean list of jobs posted in the last 24 hours
#  Each job: {company, domain, role, job_url, location, source}
# ================================================================

import re
import time
import logging
import requests
from datetime import datetime, timedelta
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from config import SCRAPER

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

HOURS_FRESH   = SCRAPER["hours_fresh"]
KEYWORDS      = [k.lower() for k in SCRAPER["keywords"]]
EXCLUDE       = [k.lower() for k in SCRAPER["exclude_keywords"]]


# ── HELPERS ───────────────────────────────────────────────────────

def extract_domain(url):
    """Pull just the domain from a URL. e.g. https://stripe.com/jobs → stripe.com"""
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.replace("www.", "")
        return domain
    except:
        return ""


def is_relevant(title):
    """Check if job title matches our keywords and doesn't match exclusions."""
    title_lower = title.lower()
    has_keyword  = any(kw in title_lower for kw in KEYWORDS)
    has_excluded = any(ex in title_lower for ex in EXCLUDE)
    return has_keyword and not has_excluded


def clean_company_name(name):
    """Remove common suffixes like Inc., LLC, Corp. from company names."""
    for suffix in [", Inc.", " Inc.", ", LLC", " LLC", ", Corp.", " Corp.",
                   ", Ltd.", " Ltd.", " Technologies", " Solutions"]:
        name = name.replace(suffix, "")
    return name.strip()


def deduplicate(jobs):
    """Remove duplicate jobs based on company + role combination."""
    seen = set()
    unique = []
    for job in jobs:
        key = f"{job['company'].lower()}|{job['role'].lower()}"
        if key not in seen:
            seen.add(key)
            unique.append(job)
    return unique


# ── SOURCE 1: GITHUB SIMPLIFYJOBS ────────────────────────────────

def scrape_github_simplifyjobs():
    """
    Reads the SimplifyJobs Summer Internships README from GitHub.
    This is a community-maintained markdown table updated multiple times daily.
    Completely free, no API key needed.
    """
    logging.info("🔍 Source 1: GitHub SimplifyJobs...")
    jobs = []

    # The repo README contains a markdown table of all internships
    url = "https://raw.githubusercontent.com/SimplifyJobs/Summer2026-Internships/dev/README.md"

    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        content = resp.text

        # Parse markdown table rows — format: | Company | Role | Location | Link | Date |
        lines = content.split("\n")
        for line in lines:
            if not line.startswith("|") or "---" in line or "Company" in line:
                continue

            cols = [c.strip() for c in line.split("|") if c.strip()]
            if len(cols) < 3:
                continue

            company_raw = cols[0]
            role_raw    = cols[1] if len(cols) > 1 else ""
            location    = cols[2] if len(cols) > 2 else "United States"
            link_col    = cols[3] if len(cols) > 3 else ""

            # Extract company name (remove markdown links)
            company = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', company_raw).strip()
            company = clean_company_name(company)

            # Extract job URL from markdown link format [text](url)
            url_match = re.search(r'\(([^)]+)\)', link_col)
            job_url   = url_match.group(1) if url_match else ""

            # Extract role name
            role = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', role_raw).strip()

            # Skip if role doesn't match our keywords
            if not role or not is_relevant(role):
                continue

            # Skip roles that are closed (marked with 🔒)
            if "🔒" in line:
                continue

            domain = extract_domain(job_url) if job_url else f"{company.lower().replace(' ', '')}.com"

            jobs.append({
                "company":  company,
                "domain":   domain,
                "role":     role,
                "job_url":  job_url,
                "location": location,
                "source":   "github_simplifyjobs",
            })

        logging.info(f"  ✅ GitHub SimplifyJobs: found {len(jobs)} relevant jobs")

    except Exception as e:
        logging.error(f"  ❌ GitHub SimplifyJobs failed: {e}")

    return jobs


# ── SOURCE 2: SIMPLIFY.JOBS NEW POSTINGS ─────────────────────────

def scrape_simplify_jobs():
    """
    Scrapes Simplify.jobs which badges newly posted internships.
    Filters to jobs posted in the last 24 hours.
    """
    logging.info("🔍 Source 2: Simplify.jobs...")
    jobs = []

    url = "https://simplify.jobs/jobs?category=Software+Engineering&experience=Internship&remote=false"

    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(resp.text, "html.parser")

        # Job cards on simplify.jobs
        job_cards = soup.find_all("div", class_=re.compile(r"job|card|listing", re.I))

        for card in job_cards[:80]:  # check first 80 cards
            try:
                # Extract text content
                text = card.get_text(separator=" ", strip=True)

                # Look for "new" badge or recent time indicators
                is_new = any(indicator in text.lower() for indicator in
                             ["new", "today", "1 day", "just posted", "hours ago"])

                if not is_new:
                    continue

                # Try to find role title
                title_el = card.find(["h2", "h3", "a"], class_=re.compile(r"title|role|job-name", re.I))
                role = title_el.get_text(strip=True) if title_el else ""

                if not role or not is_relevant(role):
                    continue

                # Company name
                comp_el = card.find(["span", "div", "p"], class_=re.compile(r"company|employer", re.I))
                company = comp_el.get_text(strip=True) if comp_el else ""
                company = clean_company_name(company)

                # Job link
                link_el = card.find("a", href=True)
                job_url = "https://simplify.jobs" + link_el["href"] if link_el and link_el["href"].startswith("/") else (link_el["href"] if link_el else "")

                if not company:
                    continue

                domain = f"{company.lower().replace(' ', '').replace('-', '')}.com"

                jobs.append({
                    "company":  company,
                    "domain":   domain,
                    "role":     role,
                    "job_url":  job_url,
                    "location": "United States",
                    "source":   "simplify_jobs",
                })

            except Exception:
                continue

        logging.info(f"  ✅ Simplify.jobs: found {len(jobs)} relevant new jobs")

    except Exception as e:
        logging.error(f"  ❌ Simplify.jobs failed: {e}")

    return jobs


# ── SOURCE 3: INDEED RSS FEED ─────────────────────────────────────

def scrape_indeed_rss():
    """
    Indeed provides a public RSS feed — no scraping, no login, fully legal.
    We search for CS internships and filter to last 24 hours.
    """
    logging.info("🔍 Source 3: Indeed RSS...")
    jobs = []

    # Indeed RSS URLs for different search terms
    search_terms = [
        "software+engineer+intern",
        "backend+engineer+intern",
        "fullstack+intern",
        "machine+learning+intern",
    ]

    cutoff = datetime.now() - timedelta(hours=HOURS_FRESH)

    for term in search_terms:
        rss_url = (
            f"https://www.indeed.com/rss?q={term}&l=United+States"
            f"&fromage=1&sort=date&jt=internship"
        )

        try:
            resp = requests.get(rss_url, headers=HEADERS, timeout=15)
            soup = BeautifulSoup(resp.text, "xml")

            items = soup.find_all("item")

            for item in items:
                try:
                    role    = item.find("title").get_text(strip=True) if item.find("title") else ""
                    company = item.find("source").get_text(strip=True) if item.find("source") else ""
                    job_url = item.find("link").get_text(strip=True) if item.find("link") else ""
                    pub_date_str = item.find("pubDate").get_text(strip=True) if item.find("pubDate") else ""

                    # Parse publish date
                    if pub_date_str:
                        try:
                            from email.utils import parsedate_to_datetime
                            pub_date = parsedate_to_datetime(pub_date_str).replace(tzinfo=None)
                            if pub_date < cutoff:
                                continue  # too old
                        except:
                            pass  # if we can't parse date, include it anyway

                    # Clean up role (Indeed appends company sometimes)
                    role = role.split(" - ")[0].strip() if " - " in role else role
                    company = clean_company_name(company)

                    if not is_relevant(role) or not company:
                        continue

                    domain = extract_domain(job_url) if job_url else ""
                    # Indeed URLs don't show company domain — we'll guess it
                    if not domain or "indeed.com" in domain:
                        domain = f"{company.lower().replace(' ', '').replace('-', '')}.com"

                    jobs.append({
                        "company":  company,
                        "domain":   domain,
                        "role":     role,
                        "job_url":  job_url,
                        "location": "United States",
                        "source":   "indeed_rss",
                    })

                except Exception:
                    continue

            time.sleep(1)  # be polite between RSS requests

        except Exception as e:
            logging.error(f"  ❌ Indeed RSS ({term}) failed: {e}")

    logging.info(f"  ✅ Indeed RSS: found {len(jobs)} relevant jobs")
    return jobs


# ── SOURCE 4: JOBSPY LIBRARY ──────────────────────────────────────

def scrape_jobspy():
    """
    JobSpy is a Python library that legally scrapes Indeed + Google Jobs.
    pip install jobspy
    Returns structured job data including company, role, location, URL.
    """
    logging.info("🔍 Source 4: JobSpy (Indeed + Google Jobs)...")
    jobs = []

    try:
        from jobspy import scrape_jobs
        import pandas as pd

        results = scrape_jobs(
            site_name=["indeed", "google"],
            search_term="software engineer intern",
            location="United States",
            results_wanted=50,
            hours_old=HOURS_FRESH,
            country_indeed="USA",
        )

        if results is None or results.empty:
            logging.info("  ⚠️ JobSpy returned no results")
            return []

        for _, row in results.iterrows():
            try:
                role    = str(row.get("title", ""))
                company = clean_company_name(str(row.get("company", "")))
                job_url = str(row.get("job_url", ""))
                location = str(row.get("location", ""))

                if not is_relevant(role) or not company or company == "nan":
                    continue

                domain = extract_domain(job_url) if job_url else \
                         f"{company.lower().replace(' ', '').replace('-', '')}.com"

                jobs.append({
                    "company":  company,
                    "domain":   domain,
                    "role":     role,
                    "job_url":  job_url,
                    "location": location,
                    "source":   "jobspy",
                })

            except Exception:
                continue

        logging.info(f"  ✅ JobSpy: found {len(jobs)} relevant jobs")

    except ImportError:
        logging.warning("  ⚠️ JobSpy not installed. Run: pip install jobspy")
    except Exception as e:
        logging.error(f"  ❌ JobSpy failed: {e}")

    return jobs


# ── MAIN SCRAPER FUNCTION ─────────────────────────────────────────

def get_fresh_jobs():
    """
    Runs all 4 scrapers, combines results, deduplicates, and returns
    a clean list of fresh CS internship postings.

    Returns: list of dicts with keys:
        company, domain, role, job_url, location, source
    """
    logging.info("=" * 55)
    logging.info("🚀 Starting job scraper...")
    logging.info("=" * 55)

    all_jobs = []

    # Run all 4 scrapers
    all_jobs += scrape_github_simplifyjobs()
    time.sleep(2)
    all_jobs += scrape_simplify_jobs()
    time.sleep(2)
    all_jobs += scrape_indeed_rss()
    time.sleep(2)
    all_jobs += scrape_jobspy()

    # Remove duplicates (same company + role from multiple sources)
    unique_jobs = deduplicate(all_jobs)

    logging.info("=" * 55)
    logging.info(f"📋 Total unique relevant jobs found: {len(unique_jobs)}")
    logging.info("=" * 55)

    return unique_jobs


# ── QUICK TEST ────────────────────────────────────────────────────
if __name__ == "__main__":
    # Run this file directly to test scrapers:
    # python scraper.py
    jobs = get_fresh_jobs()
    print(f"\n✅ Found {len(jobs)} jobs\n")
    for i, job in enumerate(jobs[:10], 1):
        print(f"{i}. {job['company']} — {job['role']}")
        print(f"   Source: {job['source']} | URL: {job['job_url'][:60]}...")
        print()
