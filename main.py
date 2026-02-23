# main.py
# ================================================================
#  THE BRAIN — connects all modules and runs the full pipeline
#
#  USAGE:
#    python main.py               ← run once right now (test/manual)
#    python main.py --schedule    ← run every day at 8 AM automatically
#    python main.py --followups   ← only send follow-ups (no new emails)
#    python main.py --stats       ← print your all-time stats
#    python main.py --got-reply recruiter@company.com  ← mark a reply
#    python main.py --test        ← dry run (finds jobs/emails, no sending)
#
#  PIPELINE ORDER:
#    1. Scrape fresh internship postings (4 sources)
#    2. For each company: find recruiter emails (5 free methods)
#    3. Skip if already contacted or company maxed out
#    4. Build personalized email using job keywords + Harsh's resume
#    5. Send 30-40 emails with random delays
#    6. Send follow-ups to 5-day-old unanswered emails
#    7. Send Harsh a daily summary
# ================================================================

import sys
import logging
import argparse
import time
from datetime import datetime

from config import EMAIL_SETTINGS, EMAIL_FINDER
from database import (
    init_db, save_job, save_recruiter,
    already_contacted, is_company_maxed,
    get_followup_candidates, get_all_time_stats,
    save_daily_summary, mark_got_reply
)
from scraper import get_fresh_jobs
from email_finder import find_recruiter_emails
from templates import main_email
from emailer import send_cold_emails, send_followups, send_daily_summary

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("internship_mailer.log"),
    ]
)

MAX_PER_COMPANY = EMAIL_FINDER.get("max_per_company", 3)
DAILY_LIMIT     = EMAIL_SETTINGS["daily_limit"]


# ── CORE PIPELINE ─────────────────────────────────────────────────

def run_pipeline(dry_run=False):
    start_time = datetime.now()
    date_str   = start_time.strftime("%Y-%m-%d")

    logging.info("\n" + "="*60)
    logging.info(f"🚀 INTERNSHIP MAILER STARTED — {date_str}")
    logging.info(f"   Mode: {'DRY RUN (no emails sent)' if dry_run else 'LIVE'}")
    logging.info("="*60 + "\n")

    stats = {
        "jobs_found": 0, "emails_found": 0, "emails_sent": 0,
        "followups_sent": 0, "companies_skipped": 0, "errors": "",
    }

    candidates    = []
    contacts_sent = []

    # ── STEP 1: Scrape fresh jobs ─────────────────────────────────
    logging.info("STEP 1: Scraping fresh internship postings...\n")
    try:
        jobs = get_fresh_jobs()
        stats["jobs_found"] = len(jobs)
        logging.info(f"✅ Step 1 complete — {len(jobs)} jobs found\n")
    except Exception as e:
        logging.error(f"❌ Scraper failed: {e}")
        stats["errors"] += f"Scraper failed: {e}\n"
        jobs = []

    # ── STEP 2 & 3: Find emails, check limits, build candidates ───
    logging.info("STEP 2: Finding recruiter emails & building send list...\n")

    for job in jobs:
        if len(candidates) >= DAILY_LIMIT:
            break

        company  = job["company"]
        domain   = job["domain"]
        role     = job["role"]
        job_url  = job["job_url"]
        location = job["location"]
        source   = job["source"]

        if is_company_maxed(company, MAX_PER_COMPANY):
            logging.info(f"  ⏭️  {company} — already at max contacts, skipping")
            stats["companies_skipped"] += 1
            continue

        job_id = save_job(company, domain, role, job_url, location, source)

        try:
            recruiter_contacts = find_recruiter_emails(company, domain)
        except Exception as e:
            logging.error(f"  ❌ Email finder failed for {company}: {e}")
            stats["errors"] += f"Email finder failed for {company}: {e}\n"
            continue

        if not recruiter_contacts:
            continue

        stats["emails_found"] += len(recruiter_contacts)

        for contact in recruiter_contacts:
            email       = contact["email"]
            first_name  = contact.get("first_name", "")
            last_name   = contact.get("last_name", "")
            title       = contact.get("title", "")
            find_method = contact.get("method", "")
            verified    = contact.get("verified", False)

            if already_contacted(email):
                logging.info(f"    ⏭️  {email} — already contacted")
                continue

            current_in_run = sum(
                1 for c in candidates if c["company"].lower() == company.lower()
            )
            if current_in_run >= MAX_PER_COMPANY:
                break

            recruiter_id = save_recruiter(
                job_id=job_id, company=company, email=email,
                first_name=first_name, last_name=last_name,
                title=title, find_method=find_method, verified=verified,
            )

            if recruiter_id is None:
                continue

            subject, body, hook_key = main_email(
                recruiter_first_name=first_name,
                company=company,
                role=role,
                job_url=job_url,
                job_description=role,
                find_method=find_method,
            )

            candidates.append({
                "recruiter_id": recruiter_id,
                "company":      company,
                "role":         role,
                "email":        email,
                "first_name":   first_name,
                "subject":      subject,
                "body":         body,
                "hook_key":     hook_key,
                "find_method":  find_method,
            })

            if len(candidates) >= DAILY_LIMIT:
                break

    logging.info(f"\n✅ Step 2 complete — {len(candidates)} candidates ready\n")

    # ── STEP 4 & 5: Send (or dry-run) ────────────────────────────
    if dry_run:
        logging.info("🧪 DRY RUN — no emails sent. Candidates:\n")
        for i, c in enumerate(candidates, 1):
            logging.info(f"  {i:>2}. {c['company']:<30} → {c['email']}  [{c['hook_key']}]")
        logging.info(f"\n  Total: {len(candidates)} candidates")
    else:
        logging.info("STEP 3: Sending cold emails...\n")
        try:
            sent, contacts_sent, errors = send_cold_emails(candidates)
            stats["emails_sent"] = sent
            if errors:
                stats["errors"] += errors + "\n"
        except Exception as e:
            logging.error(f"❌ Email sending failed: {e}")
            stats["errors"] += f"Send failed: {e}\n"

        # ── STEP 6: Follow-ups ────────────────────────────────────
        logging.info("STEP 4: Checking follow-ups...\n")
        try:
            followup_candidates = get_followup_candidates(
                followup_after_days=EMAIL_SETTINGS["followup_after_days"]
            )
            if followup_candidates:
                stats["followups_sent"] = send_followups(followup_candidates)
            else:
                logging.info("  📭 No follow-ups needed today")
        except Exception as e:
            logging.error(f"❌ Follow-up failed: {e}")
            stats["errors"] += f"Follow-up failed: {e}\n"

        # ── STEP 7: Save stats & send summary ────────────────────
        save_daily_summary(**{k: stats[k] for k in
            ["jobs_found","emails_found","emails_sent","followups_sent","companies_skipped","errors"]})

        logging.info("\nSTEP 5: Sending daily summary...\n")
        send_daily_summary(
            date=date_str,
            jobs_found=stats["jobs_found"],
            emails_found=stats["emails_found"],
            emails_sent=stats["emails_sent"],
            followups_sent=stats["followups_sent"],
            companies_skipped=stats["companies_skipped"],
            contacts_sent_to=contacts_sent,
            errors=stats["errors"],
        )

    elapsed = (datetime.now() - start_time).seconds
    logging.info(f"\n{'='*60}")
    logging.info(f"🏁 DONE in {elapsed}s | Sent: {stats['emails_sent']} | "
                 f"Follow-ups: {stats['followups_sent']}")
    logging.info(f"{'='*60}\n")


# ── SCHEDULER ─────────────────────────────────────────────────────

def run_scheduled():
    try:
        import schedule
    except ImportError:
        logging.error(
            "❌ Missing dependency: schedule\n"
            "   Install it with: pip install schedule\n"
            "   Or run: pip install -r requirements.txt"
        )
        return

    hour     = EMAIL_SETTINGS.get("send_hour", 8)
    run_time = f"{hour:02d}:00"
    logging.info(f"⏰ Scheduler active — running daily at {run_time}. Ctrl+C to stop.\n")
    schedule.every().day.at(run_time).do(run_pipeline)
    while True:
        schedule.run_pending()
        time.sleep(60)


# ── CLI ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    init_db()

    parser = argparse.ArgumentParser(description="Harsh's Internship Mailer")
    parser.add_argument("--schedule",  action="store_true", help="Run daily at 8 AM")
    parser.add_argument("--followups", action="store_true", help="Only send follow-ups")
    parser.add_argument("--test",      action="store_true", help="Dry run — no emails sent")
    parser.add_argument("--stats",     action="store_true", help="Show all-time stats")
    parser.add_argument("--got-reply", metavar="EMAIL",     help="Mark email as replied")
    args = parser.parse_args()

    if args.stats:
        s = get_all_time_stats()
        print("\n📊 ALL-TIME STATS\n" + "="*35)
        for k, v in s.items():
            print(f"  {k.replace('_',' ').title():<28}: {v}")
        print()

    elif args.got_reply:
        mark_got_reply(args.got_reply)

    elif args.followups:
        candidates = get_followup_candidates(EMAIL_SETTINGS["followup_after_days"])
        send_followups(candidates)

    elif args.test:
        run_pipeline(dry_run=True)

    elif args.schedule:
        run_scheduled()

    else:
        run_pipeline(dry_run=False)
