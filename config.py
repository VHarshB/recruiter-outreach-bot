# config.py
# ================================================================
#  ALL SETTINGS IN ONE PLACE — Edit this file, nothing else
#  Your personal info is pre-filled from your resume.
#
#  SECRETS (Gmail password, Apollo key) are loaded from .env
#  Never hardcode passwords here — always use .env
# ================================================================

import os
from dotenv import load_dotenv

# Load secrets from .env file — must happen before anything else
load_dotenv()

# ── SECRETS FROM .env ─────────────────────────────────────────────
_GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD", "")
_APOLLO_API_KEY     = os.getenv("APOLLO_API_KEY", "")

# Warn immediately at startup if secrets are missing
if not _GMAIL_APP_PASSWORD:
    print(
        "\n⚠️  WARNING: GMAIL_APP_PASSWORD not set in .env file!\n"
        "   Emails will NOT send until you add it.\n"
        "   See README.md → 'Gmail Setup' for instructions.\n"
    )

if not _APOLLO_API_KEY:
    print(
        "ℹ️  INFO: APOLLO_API_KEY not set — Apollo email lookup will be skipped.\n"
        "   Other 4 free methods will still run. Add key to .env for best results.\n"
    )

# ── YOUR PERSONAL INFO (pre-filled from resume) ──────────────────
YOUR_INFO = {
    "name":        "Harsh Vaishya",
    "first_name":  "Harsh",
    "email":       "hvaishya@asu.edu",
    "phone":       "(480) 465-1376",
    "university":  "Arizona State University",
    "short_uni":   "ASU",
    "year":        "Junior",
    "gpa":         "3.6",
    "grad_year":   "May 2027",
    "linkedin":    "linkedin.com/in/harsh-asu/",
    "github":      "github.com/VHarshB",
    "portfolio":   "harshvaishya.tech",
    "major":       "Computer Science",
    "seeking":     "Summer 2026 internship",
}

# ── YOUR TOP ACHIEVEMENTS (used to personalize emails) ────────────
ACHIEVEMENTS = {

    # Used when job mentions: ML, AI, NLP, LLM, vector, embeddings
    "ml_ai": {
        "hook": "I recently won 1st place at Hack SoDA 2024 building Faith — "
                "a Chrome extension with a FastAPI backend and PostgreSQL pipeline "
                "that delivered real-time mental health support to 50+ beta users.",
        "keywords": ["ml", "ai", "nlp", "machine learning", "llm", "vector",
                     "embedding", "deep learning", "data science", "nlp"]
    },

    # Used when job mentions: AWS, cloud, Docker, Kubernetes, Lambda, GCP
    "cloud_devops": {
        "hook": "I deployed an AWS Lambda + Docker system that monitors 200+ ASU courses "
                "24/7 at 2-minute intervals, reducing DB response time by 65% — "
                "serving 100+ real users.",
        "keywords": ["aws", "cloud", "docker", "kubernetes", "lambda", "gcp",
                     "devops", "infrastructure", "terraform", "ci/cd", "azure"]
    },

    # Used when job mentions: React, frontend, UI, Next.js, web
    "frontend": {
        "hook": "I built EnKoat's enterprise management portal in React.js + Node.js, "
                "handling 50+ daily quote submissions with real-time validation — "
                "cutting submission errors by 40%.",
        "keywords": ["react", "frontend", "ui", "next.js", "nextjs", "web",
                     "typescript", "javascript", "tailwind", "vue", "angular"]
    },

    # Used when job mentions: API, backend, microservices, REST, database
    "backend": {
        "hook": "I architected a microservices CRM platform on AWS EC2 with Docker, "
                "processing 25K+ customer records with real-time D3.js analytics — "
                "finishing Top 5 at OHack 2024.",
        "keywords": ["api", "backend", "microservices", "rest", "graphql",
                     "node", "fastapi", "spring", "django", "database", "sql",
                     "postgresql", "mongodb", "redis", "systems"]
    },

    # Default fallback — used when no specific keyword match found
    "default": {
        "hook": "I've won 4 hackathons at ASU including 1st place at Hack SoDA 2024, "
                "building full-stack products used by real users — most recently "
                "an AI diary app with sub-200ms response times using FastAPI + ChromaDB.",
        "keywords": []
    },
}

# ── EMAIL SENDING SETTINGS ────────────────────────────────────────
EMAIL_SETTINGS = {
    "gmail_user":          YOUR_INFO["email"],
    "gmail_app_password":  _GMAIL_APP_PASSWORD,   # ← loaded from .env
    "daily_limit":         35,
    "delay_min_seconds":   45,
    "delay_max_seconds":   90,
    "send_hour":           8,                      # run at 8 AM daily
    "followup_after_days": 5,
}

# ── FREE EMAIL FINDING SETTINGS ───────────────────────────────────
EMAIL_FINDER = {
    "apollo_api_key":    _APOLLO_API_KEY,          # ← loaded from .env
    "max_per_company":   3,
    "smtp_verify":       True,
    "asu_alumni_search": True,
}

# ── DATABASE SETTINGS ─────────────────────────────────────────────
DATABASE = {
    "path": "internship_tracker.db",
}

# ── JOB SCRAPING SETTINGS ─────────────────────────────────────────
SCRAPER = {
    "hours_fresh": 24,
    "keywords": [
        "software engineer intern",
        "software engineering intern",
        "software developer intern",
        "backend intern",
        "frontend intern",
        "fullstack intern",
        "full stack intern",
        "swe intern",
        "cs intern",
        "computer science intern",
        "ml intern",
        "machine learning intern",
        "data engineer intern",
    ],
    "exclude_keywords": [
        "senior", "lead", "manager", "director", "phd", "mba",
        "5+ years", "3+ years", "clearance required"
    ],
    "locations": [
        "United States",
        "Remote",
    ],
}

# ── NOTIFICATION SETTINGS ─────────────────────────────────────────
NOTIFICATIONS = {
    "send_daily_summary":  True,
    "summary_recipient":   YOUR_INFO["email"],
    "notify_on_error":     True,
}
