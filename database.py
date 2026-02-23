# database.py
# ================================================================
#  TRACKS EVERYTHING — who was contacted, when, follow-up status
#  Uses SQLite (built into Python, no install needed)
#  Database file is auto-created on first run
# ================================================================

import sqlite3
import logging
from datetime import datetime, timedelta
from config import DATABASE

DB_PATH = DATABASE["path"]

def get_connection():
    """Get a connection to the SQLite database."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # lets us access columns by name like a dict
    return conn


def init_db():
    """
    Create all tables on first run.
    Safe to call multiple times — won't overwrite existing data.
    """
    conn = get_connection()
    c = conn.cursor()

    # Table 1: Every job posting we found
    c.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            company         TEXT NOT NULL,
            domain          TEXT,
            role            TEXT,
            job_url         TEXT,
            location        TEXT,
            source          TEXT,       -- which scraper found it (github, indeed, etc.)
            date_found      TEXT,       -- ISO timestamp
            keywords_matched TEXT       -- which of Harsh's skills matched the job
        )
    """)

    c.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_jobs_unique
        ON jobs(company, role, job_url)
    """)

    # Table 2: Every recruiter email we found
    c.execute("""
        CREATE TABLE IF NOT EXISTS recruiters (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id          INTEGER,    -- links back to jobs table
            company         TEXT NOT NULL,
            first_name      TEXT,
            last_name       TEXT,
            email           TEXT UNIQUE NOT NULL,
            title           TEXT,       -- e.g. "Technical Recruiter"
            find_method     TEXT,       -- how we found the email (apollo, scrape, etc.)
            verified        INTEGER DEFAULT 0,  -- 1 if SMTP verified, 0 if not
            date_found      TEXT,
            FOREIGN KEY (job_id) REFERENCES jobs(id)
        )
    """)

    # Table 3: Every email we sent
    c.execute("""
        CREATE TABLE IF NOT EXISTS emails_sent (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            recruiter_id    INTEGER,
            company         TEXT,
            recruiter_email TEXT,
            subject         TEXT,
            personalization TEXT,       -- which hook was used (ml_ai, cloud, etc.)
            date_sent       TEXT,
            followup_sent   INTEGER DEFAULT 0,   -- 1 if follow-up already sent
            followup_date   TEXT,                -- when follow-up was sent
            got_reply       INTEGER DEFAULT 0,   -- 1 if they replied (manual update)
            FOREIGN KEY (recruiter_id) REFERENCES recruiters(id)
        )
    """)

    # Table 4: Daily run summaries
    c.execute("""
        CREATE TABLE IF NOT EXISTS daily_summary (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            date            TEXT,
            jobs_found      INTEGER DEFAULT 0,
            emails_found    INTEGER DEFAULT 0,
            emails_sent     INTEGER DEFAULT 0,
            followups_sent  INTEGER DEFAULT 0,
            companies_skipped INTEGER DEFAULT 0,
            errors          TEXT
        )
    """)

    conn.commit()
    conn.close()
    logging.info("✅ Database initialized.")


# ── JOB FUNCTIONS ─────────────────────────────────────────────────

def save_job(company, domain, role, job_url, location, source, keywords_matched=""):
    """Save a job posting. Returns the job ID."""
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        INSERT OR IGNORE INTO jobs
        (company, domain, role, job_url, location, source, date_found, keywords_matched)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (company, domain, role, job_url, location, source,
          datetime.now().isoformat(), keywords_matched))
    conn.commit()
    job_id = c.lastrowid

    if not job_id:
        c.execute(
            """
            SELECT id FROM jobs
            WHERE company = ? AND role = ? AND job_url = ?
            ORDER BY id DESC
            LIMIT 1
            """,
            (company, role, job_url)
        )
        row = c.fetchone()
        job_id = row[0] if row else None

    conn.close()
    return job_id


# ── RECRUITER FUNCTIONS ───────────────────────────────────────────

def save_recruiter(job_id, company, email, first_name="", last_name="",
                   title="", find_method="", verified=False):
    """Save a recruiter. Returns recruiter ID or None if email already exists."""
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute("""
            INSERT INTO recruiters
            (job_id, company, first_name, last_name, email, title, find_method, verified, date_found)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (job_id, company, first_name, last_name, email, title,
              find_method, int(verified), datetime.now().isoformat()))
        conn.commit()
        recruiter_id = c.lastrowid
        conn.close()
        return recruiter_id
    except sqlite3.IntegrityError:
        # Email already in database — skip
        conn.close()
        return None


def already_contacted(email):
    """Returns True if we have EVER emailed this address before."""
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT id FROM emails_sent WHERE recruiter_email = ?", (email,))
    result = c.fetchone()
    conn.close()
    return result is not None


def company_contact_count(company):
    """
    How many different people have we emailed at this company?
    Used to enforce the max 3 per company rule.
    """
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        SELECT COUNT(DISTINCT recruiter_email)
        FROM emails_sent
        WHERE LOWER(company) = LOWER(?)
    """, (company,))
    count = c.fetchone()[0]
    conn.close()
    return count


def is_company_maxed(company, max_per_company=3):
    """Returns True if we've already contacted max_per_company people at this company."""
    return company_contact_count(company) >= max_per_company


# ── EMAIL TRACKING FUNCTIONS ──────────────────────────────────────

def log_email_sent(recruiter_id, company, recruiter_email, subject, personalization):
    """Log that we sent an email."""
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        INSERT INTO emails_sent
        (recruiter_id, company, recruiter_email, subject, personalization, date_sent)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (recruiter_id, company, recruiter_email, subject,
          personalization, datetime.now().isoformat()))
    conn.commit()
    conn.close()
    logging.info(f"📧 Logged email → {recruiter_email} at {company}")


def get_followup_candidates(followup_after_days=5):
    """
    Returns list of emails that:
    - Were sent more than followup_after_days ago
    - Have NOT received a follow-up yet
    - Have NOT gotten a reply (got_reply = 0)
    """
    cutoff = (datetime.now() - timedelta(days=followup_after_days)).isoformat()
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        SELECT * FROM emails_sent
        WHERE date_sent < ?
          AND followup_sent = 0
          AND got_reply = 0
    """, (cutoff,))
    rows = c.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def mark_followup_sent(email_id):
    """Mark that a follow-up was sent for this email."""
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        UPDATE emails_sent
        SET followup_sent = 1, followup_date = ?
        WHERE id = ?
    """, (datetime.now().isoformat(), email_id))
    conn.commit()
    conn.close()


def mark_got_reply(recruiter_email):
    """
    Call this manually if a recruiter replies.
    Prevents a follow-up from being sent to someone who already responded.
    Usage: python main.py --got-reply recruiter@company.com
    """
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        UPDATE emails_sent SET got_reply = 1
        WHERE recruiter_email = ?
    """, (recruiter_email,))
    conn.commit()
    conn.close()
    print(f"✅ Marked {recruiter_email} as replied. No follow-up will be sent.")


# ── DAILY SUMMARY FUNCTIONS ───────────────────────────────────────

def save_daily_summary(jobs_found, emails_found, emails_sent,
                       followups_sent, companies_skipped, errors=""):
    """Save today's run stats."""
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        INSERT INTO daily_summary
        (date, jobs_found, emails_found, emails_sent, followups_sent, companies_skipped, errors)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (datetime.now().strftime("%Y-%m-%d"), jobs_found, emails_found,
          emails_sent, followups_sent, companies_skipped, errors))
    conn.commit()
    conn.close()


def get_all_time_stats():
    """Returns overall stats — useful for checking progress."""
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM emails_sent")
    total_sent = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM emails_sent WHERE got_reply = 1")
    total_replies = c.fetchone()[0]
    c.execute("SELECT COUNT(DISTINCT company) FROM emails_sent")
    total_companies = c.fetchone()[0]
    conn.close()
    return {
        "total_emails_sent": total_sent,
        "total_replies": total_replies,
        "reply_rate": f"{(total_replies/total_sent*100):.1f}%" if total_sent > 0 else "0%",
        "companies_contacted": total_companies,
    }
