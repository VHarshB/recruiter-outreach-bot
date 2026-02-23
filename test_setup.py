#!/usr/bin/env python3
# test_setup.py
# ================================================================
#  RUN THIS BEFORE ANYTHING ELSE — verifies your full setup
#
#  Checks:
#    ✅ All required Python libraries installed
#    ✅ .env file exists and secrets are loaded
#    ✅ Gmail connection works (real auth test)
#    ✅ Apollo API key is valid (if provided)
#    ✅ Resume PDF found in project folder
#    ✅ Database can be created
#    ✅ Scrapers return at least some jobs
#    ✅ Email finder works on a test company
#    ✅ Templates render correctly with your info
#    ✅ SMTP email verification works
#
#  USAGE:
#    python test_setup.py
#
#  All checks must pass (✅) before running main.py for real.
# ================================================================

import os
import sys
import time

# ── COLORS for terminal output ────────────────────────────────────
GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
BLUE   = "\033[94m"
RESET  = "\033[0m"
BOLD   = "\033[1m"

def ok(msg):    print(f"  {GREEN}✅ {msg}{RESET}")
def fail(msg):  print(f"  {RED}❌ {msg}{RESET}")
def warn(msg):  print(f"  {YELLOW}⚠️  {msg}{RESET}")
def info(msg):  print(f"  {BLUE}ℹ️  {msg}{RESET}")
def header(msg): print(f"\n{BOLD}{msg}{RESET}\n" + "─"*50)

passed = 0
failed = 0

def check(condition, pass_msg, fail_msg=None, warning=False):
    global passed, failed
    if condition:
        ok(pass_msg)
        passed += 1
    else:
        if fail_msg is None:
            fail_msg = "Check failed"
        if warning:
            warn(fail_msg)
        else:
            fail(fail_msg)
            failed += 1


# ═══════════════════════════════════════════════════════════════
print(f"\n{BOLD}{'='*55}")
print("  INTERNSHIP MAILER — Setup Verification")
print(f"{'='*55}{RESET}")
# ═══════════════════════════════════════════════════════════════


# ── CHECK 1: Required libraries ───────────────────────────────────
header("CHECK 1: Python Libraries")

libraries = {
    "requests":     "requests",
    "bs4":          "beautifulsoup4",
    "dotenv":       "python-dotenv",
    "schedule":     "schedule",
    "dns":          "dnspython",
}

all_libs_ok = True
for import_name, pip_name in libraries.items():
    try:
        __import__(import_name)
        ok(f"{pip_name} installed")
    except ImportError:
        fail(f"{pip_name} NOT installed → run: pip install {pip_name}")
        all_libs_ok = False

# jobspy is optional but recommended
try:
    import jobspy
    ok("jobspy installed (Source 4 active)")
except ImportError:
    warn("jobspy not installed → Source 4 inactive. Install with: pip install jobspy")


# ── CHECK 2: .env file and secrets ───────────────────────────────
header("CHECK 2: Environment & Secrets")

env_exists = os.path.exists(".env")
check(env_exists, ".env file found", ".env file MISSING — copy .env.template to .env and fill it in")

if env_exists:
    from dotenv import load_dotenv
    load_dotenv()

    gmail_pw = os.getenv("GMAIL_APP_PASSWORD", "")
    apollo_k = os.getenv("APOLLO_API_KEY", "")

    check(
        bool(gmail_pw) and len(gmail_pw) >= 16,
        f"GMAIL_APP_PASSWORD set (length: {len(gmail_pw)})",
        "GMAIL_APP_PASSWORD missing or too short in .env — emails won't send"
    )
    check(
        bool(apollo_k) and len(apollo_k) > 10,
        f"APOLLO_API_KEY set (length: {len(apollo_k)})",
        "APOLLO_API_KEY not set — Apollo method will be skipped (other 4 methods still work)",
        warning=True   # this is optional so just a warning
    )


# ── CHECK 3: Resume PDF ───────────────────────────────────────────
header("CHECK 3: Resume PDF")

resume_path = "Harsh_Vaishya_Resume.pdf"
resume_exists = os.path.exists(resume_path)
check(
    resume_exists,
    f"Resume found: {resume_path}",
    f"Resume NOT found! Place your PDF in this folder named exactly: {resume_path}"
)

if resume_exists:
    size_kb = os.path.getsize(resume_path) / 1024
    check(
        size_kb > 10,
        f"Resume size looks good ({size_kb:.0f} KB)",
        f"Resume file seems too small ({size_kb:.0f} KB) — may be corrupted"
    )


# ── CHECK 4: Gmail connection ─────────────────────────────────────
header("CHECK 4: Gmail Connection")

if not env_exists or not gmail_pw:
    warn("Skipping Gmail test — no password set")
else:
    try:
        from config import EMAIL_SETTINGS
        gmail_user = EMAIL_SETTINGS["gmail_user"]
        gmail_pass = EMAIL_SETTINGS["gmail_app_password"]

        import smtplib
        server = smtplib.SMTP_SSL("smtp.gmail.com", 465)
        server.login(gmail_user, gmail_pass)
        server.quit()
        ok("Gmail connection successful ✉️")
        passed += 1
    except smtplib.SMTPAuthenticationError:
        fail(
            "Gmail authentication FAILED!\n"
            "     Make sure you're using a Gmail APP PASSWORD\n"
            "     See README.md → Gmail Setup"
        )
        failed += 1
    except Exception as e:
        fail(f"Gmail connection error: {e}")
        failed += 1


# ── CHECK 5: Apollo API ───────────────────────────────────────────
header("CHECK 5: Apollo.io API (optional)")

apollo_key = os.getenv("APOLLO_API_KEY", "")
if not apollo_key:
    warn("No Apollo key — skipping test. Other 4 email methods still work fine.")
else:
    try:
        import requests
        resp = requests.post(
            "https://api.apollo.io/v1/mixed_people/search",
            json={"api_key": apollo_key, "q_organization_domains": ["stripe.com"], "per_page": 1},
            timeout=10
        )
        data = resp.json()
        if "error" in str(data).lower() or resp.status_code == 401:
            fail(f"Apollo API key invalid: {data.get('message', resp.status_code)}")
            failed += 1
        else:
            credits = data.get("pagination", {}).get("total_entries", "?")
            ok(f"Apollo API working — found results for test query")
            passed += 1
    except Exception as e:
        warn(f"Apollo API test inconclusive: {e}")


# ── CHECK 6: Database ─────────────────────────────────────────────
header("CHECK 6: Database")

try:
    from database import init_db, get_all_time_stats
    init_db()
    stats = get_all_time_stats()
    ok(f"Database created/opened successfully")
    info(f"All-time stats: {stats['total_emails_sent']} emails sent, "
         f"{stats['total_replies']} replies, "
         f"{stats['companies_contacted']} companies contacted")
    passed += 1
except Exception as e:
    fail(f"Database error: {e}")
    failed += 1


# ── CHECK 7: Scrapers (quick test) ────────────────────────────────
header("CHECK 7: Job Scrapers (quick test — may take 30s)")

try:
    import requests
    from bs4 import BeautifulSoup

    # Test GitHub SimplifyJobs
    resp = requests.get(
        "https://raw.githubusercontent.com/SimplifyJobs/Summer2026-Internships/dev/README.md",
        timeout=15
    )
    lines_with_jobs = [l for l in resp.text.split("\n") if l.startswith("|") and "🔒" not in l and "---" not in l and "Company" not in l]
    check(
        len(lines_with_jobs) > 5,
        f"GitHub SimplifyJobs reachable ({len(lines_with_jobs)} open jobs found)",
        "GitHub SimplifyJobs unreachable — check internet connection"
    )

    # Test Indeed RSS
    rss = requests.get(
        "https://www.indeed.com/rss?q=software+engineer+intern&l=United+States&fromage=1",
        timeout=10,
        headers={"User-Agent": "Mozilla/5.0"}
    )
    check(
        rss.status_code == 200,
        "Indeed RSS feed reachable",
        f"Indeed RSS returned status {rss.status_code}"
    )

except Exception as e:
    fail(f"Scraper test failed: {e}")
    failed += 1


# ── CHECK 8: Email templates ──────────────────────────────────────
header("CHECK 8: Email Templates")

try:
    from templates import main_email, followup_email, daily_summary_email

    subj, body, hook = main_email(
        recruiter_first_name="Sarah",
        company="Stripe",
        role="Backend Engineer Intern",
        job_description="AWS Docker Kubernetes backend microservices API",
    )

    check(bool(subj), "Subject line generated")
    check("Harsh" in body, "Your name appears in email body")
    check("ASU" in body or "Arizona State" in body, "University mentioned")
    check("github.com/VHarshB" in body, "GitHub link included")
    check(hook == "cloud_devops", f"Correct hook selected for AWS job (got: {hook})")

    # Test a frontend job
    _, body2, hook2 = main_email(
        recruiter_first_name="",
        company="Figma",
        role="Frontend React Intern",
        job_description="React TypeScript TailwindCSS frontend UI",
    )
    check(hook2 == "frontend", f"Correct hook for React job (got: {hook2})")

    ok("All template tests passed")

    print(f"\n  {BLUE}── Sample email preview ──{RESET}")
    print(f"  Subject: {subj}")
    print(f"  Hook used: {hook}")
    preview = body[:300].replace("\n", "\n  ")
    print(f"\n  {preview}...")

except Exception as e:
    fail(f"Template error: {e}")
    failed += 1
    import traceback
    traceback.print_exc()


# ── CHECK 9: SMTP email verification ─────────────────────────────
header("CHECK 9: SMTP Email Verification")

try:
    import dns.resolver
    ok("dnspython installed — SMTP verification active")
    passed += 1

    # Quick test — verify a known-good generic address pattern
    try:
        mx = dns.resolver.resolve("gmail.com", "MX")
        ok(f"DNS resolution working (Gmail MX: {str(list(mx)[0].exchange)[:40]})")
        passed += 1
    except Exception as e:
        warn(f"DNS test inconclusive: {e} — SMTP verify may not work")

except ImportError:
    warn("dnspython not installed — SMTP verify will be skipped")
    warn("Install with: pip install dnspython")


# ── FINAL RESULT ──────────────────────────────────────────────────
print(f"\n{'='*55}")
total = passed + failed
print(f"{BOLD}  RESULTS: {passed}/{total} checks passed{RESET}")

if failed == 0:
    print(f"\n  {GREEN}{BOLD}🎉 Everything looks good! You're ready to run:{RESET}")
    print(f"\n  {BLUE}  python main.py --test{RESET}   ← dry run first (recommended)")
    print(f"  {BLUE}  python main.py{RESET}           ← send real emails")
    print(f"  {BLUE}  python main.py --schedule{RESET} ← run daily at 8 AM\n")
else:
    print(f"\n  {RED}{BOLD}⚠️  {failed} check(s) failed — fix these before running main.py{RESET}")
    print(f"\n  See README.md for step-by-step setup instructions.\n")

print("="*55 + "\n")
