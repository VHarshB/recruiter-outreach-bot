# 🚀 Internship Email Automation — Project Overview
### Built for: Harsh Vaishya | ASU CS Junior | Summer 2026

---

## What This Project Does (Plain English)

Every morning this system wakes up and does 5 things automatically:
1. **Finds** fresh CS internship postings from 4 sources (posted in last 24 hrs)
2. **Finds** recruiter emails using 5 free methods — no paid tools
3. **Personalizes** your email using Harsh's real resume details + company info
4. **Sends** 30–40 emails and never contacts the same recruiter twice
5. **Follows up** automatically after 5 days + sends YOU a daily summary

---

## File Structure

```
internship_mailer/
│
├── main.py                  ← The brain — runs everything in order
│
├── config.py                ← All your settings in one place
│                              (your name, Gmail, daily limits, etc.)
│
├── scraper.py               ← STEP 1: Finds fresh internship postings
│                              Sources: GitHub SimplifyJobs, Simplify.jobs,
│                              Indeed RSS, JobSpy (Google Jobs + Indeed)
│
├── email_finder.py          ← STEP 2: Finds recruiter emails for free
│                              Method 1: Apollo.io API (50 free/month)
│                              Method 2: Scrape company careers/about page
│                              Method 3: Google dorking (search for @company.com)
│                              Method 4: Guess pattern + SMTP verify (no email sent)
│                              Method 5: Search for ASU alumni at that company
│
├── database.py              ← STEP 3: SQLite tracker
│                              - Logs every recruiter ever contacted
│                              - Tracks company contact count (max 3 per company)
│                              - Tracks follow-up dates
│
├── emailer.py               ← STEP 4 & 5: Sends emails via Gmail
│                              - Personalized template using Harsh's real resume
│                              - Auto-tweaks per recruiter (5 rotating personalizations)
│                              - Follow-up sender
│                              - Daily summary to Harsh
│
├── templates.py             ← All email templates in one place
│                              - Main cold email (uses Harsh's hackathon wins + projects)
│                              - Follow-up email
│                              - Daily summary email
│
├── internship_tracker.db    ← Auto-created SQLite database (don't touch)
│
├── .env                     ← Your secrets (Gmail password, Apollo key) — NEVER share
│
├── requirements.txt         ← All Python libraries to install
│
└── README.md                ← Step-by-step setup instructions
```

---

## How The Files Talk To Each Other

```
main.py
  │
  ├──► scraper.py         → returns list of {company, role, job_url, domain}
  │
  ├──► email_finder.py    → takes domain, returns list of recruiter emails
  │
  ├──► database.py        → checks/logs who was contacted, skips duplicates
  │
  ├──► templates.py       → builds personalized email text per recruiter
  │
  └──► emailer.py         → sends the emails, sends you daily summary
```

---

## Harsh's Info Pre-Loaded Into Templates

Pulled directly from your resume — no need to edit templates manually:

| Field | Value |
|-------|-------|
| Name | Harsh Vaishya |
| University | Arizona State University (ASU) |
| Year | Junior (graduating May 2027) |
| GPA | 3.6 / 4.0 |
| Email | hvaishya@asu.edu |
| Phone | (480) 465-1376 |
| LinkedIn | linkedin.com/in/harsh-asu/ |
| GitHub | github.com/VHarshB |
| Portfolio | harshvaishya.tech |
| Best Achievement | 🏆 1st Place Hack SoDA 2024 (Faith app) |
| Top Project | Intelligent Academic Registration System (100+ users, AWS) |
| Stack | React, FastAPI, Node.js, AWS, Docker, PostgreSQL |

---

## Email Personalization Logic

The script picks **1 of 5 personalization hooks** per email based on the job description keywords:

| If job mentions... | Personalization line added |
|-------------------|--------------------------|
| `AWS` / `cloud` / `Docker` | Mentions AWS Lambda + Docker deployment project |
| `React` / `frontend` / `UI` | Mentions EnKoat portal (50+ daily submissions) |
| `ML` / `AI` / `NLP` | Mentions Tom Riddle AI (ChromaDB, sub-200ms) |
| `API` / `backend` / `microservices` | Mentions CRM platform (25K+ records) |
| `fullstack` / `general` | Mentions 1st place hackathon win (Faith app) |

---

## Daily Email Limit & Safety Rules

| Rule | Setting |
|------|---------|
| Max emails per day | 35 (sweet spot of 30–40) |
| Max recruiters per company | 3 |
| Follow-up after | 5 days |
| Max follow-ups per person | 1 |
| Send window | 8:00 AM – 11:00 AM (best open rates) |
| Delay between emails | 45–90 seconds random (avoids spam detection) |

---

## Setup Steps (Quick View)

1. `pip install -r requirements.txt`
2. Create `.env` file with your Gmail + Apollo key
3. Enable Gmail App Password (2-min setup, instructions in README)
4. Run `python main.py` to test
5. Run `python main.py --schedule` to run every day at 8 AM automatically

---

## Build Order (What We're Making First)

- [x] PROJECT_OVERVIEW.md ← you are here
- [ ] config.py ← next (your settings + Harsh's info)
- [ ] requirements.txt ← next (all libraries)
- [ ] database.py
- [ ] scraper.py
- [ ] email_finder.py
- [ ] templates.py
- [ ] emailer.py
- [ ] main.py
- [ ] README.md (setup guide)
