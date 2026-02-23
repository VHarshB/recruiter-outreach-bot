# emailer.py
# ================================================================
#  SENDS ALL EMAILS — cold outreach, follow-ups, daily summary
#
#  Uses Gmail SMTP (free, no third-party service needed)
#  Built-in safety features:
#    - Random 45-90 second delay between emails (avoids spam flags)
#    - Hard cap of 35 emails per day
#    - Attaches Harsh's resume automatically
#    - Never sends to same address twice (double-checks DB)
#    - Graceful error handling — one failure won't stop the run
# ================================================================

import os
import time
import random
import logging
import smtplib
import re
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime

from config import EMAIL_SETTINGS, YOUR_INFO, NOTIFICATIONS
from database import already_contacted, log_email_sent, mark_followup_sent, get_all_time_stats
from templates import followup_email, daily_summary_email

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

# ── SETTINGS ──────────────────────────────────────────────────────
GMAIL_USER     = EMAIL_SETTINGS["gmail_user"]
GMAIL_PASSWORD = EMAIL_SETTINGS["gmail_app_password"]
DAILY_LIMIT    = EMAIL_SETTINGS["daily_limit"]
DELAY_MIN      = EMAIL_SETTINGS["delay_min_seconds"]
DELAY_MAX      = EMAIL_SETTINGS["delay_max_seconds"]

# Path to Harsh's resume PDF — place it in the project folder
RESUME_PATH = os.path.join(os.path.dirname(__file__), "Harsh_Vaishya_Resume.pdf")


# ── GMAIL CONNECTION ──────────────────────────────────────────────

def get_smtp_connection():
    """
    Opens a secure Gmail SMTP connection.
    Uses App Password (not your real Gmail password).
    See README.md for how to generate an App Password in 2 minutes.
    """
    try:
        server = smtplib.SMTP_SSL("smtp.gmail.com", 465)
        server.login(GMAIL_USER, GMAIL_PASSWORD)
        return server
    except smtplib.SMTPAuthenticationError:
        logging.error(
            "❌ Gmail authentication failed!\n"
            "   Make sure you're using a Gmail App Password, not your regular password.\n"
            "   See README.md → 'Gmail Setup' section for instructions."
        )
        raise
    except Exception as e:
        logging.error(f"❌ Could not connect to Gmail: {e}")
        raise


def build_message(to_email, subject, body, attach_resume=True):
    """
    Builds a MIME email message with optional resume attachment.

    Args:
        to_email       : recipient email address
        subject        : email subject line
        body           : plain text email body
        attach_resume  : whether to attach Harsh's resume PDF

    Returns:
        MIMEMultipart message object ready to send
    """
    msg = MIMEMultipart()
    msg["From"]    = f"{YOUR_INFO['name']} <{GMAIL_USER}>"
    msg["To"]      = to_email
    msg["Subject"] = subject

    # Plain text body
    msg.attach(MIMEText(body, "plain"))

    # Attach resume PDF if it exists
    if attach_resume and os.path.exists(RESUME_PATH):
        try:
            with open(RESUME_PATH, "rb") as f:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(f.read())
            encoders.encode_base64(part)
            part.add_header(
                "Content-Disposition",
                f'attachment; filename="Harsh_Vaishya_Resume.pdf"'
            )
            msg.attach(part)
        except Exception as e:
            logging.warning(f"  ⚠️ Could not attach resume: {e}")
    elif attach_resume and not os.path.exists(RESUME_PATH):
        logging.warning(
            f"  ⚠️ Resume not found at {RESUME_PATH}\n"
            f"     Place your resume PDF in the project folder named: Harsh_Vaishya_Resume.pdf"
        )

    return msg


# ── CORE SEND FUNCTION ────────────────────────────────────────────

def send_single_email(server, to_email, subject, body, attach_resume=True):
    """
    Sends one email using an existing SMTP connection.

    Args:
        server        : active smtplib SMTP connection
        to_email      : recipient email
        subject       : subject line
        body          : email body text
        attach_resume : attach PDF resume or not

    Returns:
        True if sent successfully, False if failed
    """
    try:
        msg = build_message(to_email, subject, body, attach_resume)
        server.sendmail(GMAIL_USER, to_email, msg.as_string())
        logging.info(f"  ✅ Sent → {to_email}")
        return True
    except smtplib.SMTPRecipientsRefused:
        logging.warning(f"  ❌ Recipient refused: {to_email} (email may not exist)")
        return False
    except smtplib.SMTPException as e:
        logging.error(f"  ❌ SMTP error sending to {to_email}: {e}")
        return False
    except Exception as e:
        logging.error(f"  ❌ Unexpected error sending to {to_email}: {e}")
        return False


def random_delay():
    """Wait a random amount of time between emails to avoid spam detection."""
    delay = random.uniform(DELAY_MIN, DELAY_MAX)
    logging.info(f"  ⏳ Waiting {delay:.0f}s before next email...")
    time.sleep(delay)


def extract_role_from_subject(original_subject):
    """Extract role from known cold-email subject format when possible."""
    if not original_subject:
        return "Software Engineer Intern"

    match = re.search(r"\|\s*(.*?)\s*@", original_subject)
    if match:
        role = match.group(1).strip()
        if role:
            return role

    return "Software Engineer Intern"


# ── MAIN SEND BATCH ───────────────────────────────────────────────

def send_cold_emails(candidates):
    """
    Sends cold emails to a list of recruiter candidates.
    Enforces daily limit, checks DB for duplicates, logs everything.

    Args:
        candidates: list of dicts with keys:
            recruiter_id, company, email, first_name, subject,
            body, hook_key, find_method

    Returns:
        (sent_count, contacts_sent_to, errors) tuple
    """
    if not candidates:
        logging.info("📭 No candidates to email today.")
        return 0, [], ""

    sent_count      = 0
    contacts_sent   = []
    errors          = []
    server          = None

    logging.info(f"\n{'='*55}")
    logging.info(f"📨 Starting email send — {len(candidates)} candidates, limit {DAILY_LIMIT}")
    logging.info(f"{'='*55}")

    try:
        server = get_smtp_connection()
        logging.info("✅ Gmail connected\n")

        for candidate in candidates:
            if sent_count >= DAILY_LIMIT:
                logging.info(f"🛑 Daily limit of {DAILY_LIMIT} reached. Stopping.")
                break

            email      = candidate["email"]
            company    = candidate["company"]
            role       = candidate.get("role", "Software Engineer Intern")
            subject    = candidate["subject"]
            body       = candidate["body"]
            hook_key   = candidate.get("hook_key", "default")
            rec_id     = candidate.get("recruiter_id")
            first_name = candidate.get("first_name", "")

            # Final duplicate check right before sending
            if already_contacted(email):
                logging.info(f"  ⏭️  Skipping {email} — already contacted")
                continue

            logging.info(f"\n📤 [{sent_count+1}/{DAILY_LIMIT}] {company} → {email}")
            logging.info(f"   Role: {role} | Hook: {hook_key}")

            success = send_single_email(server, email, subject, body, attach_resume=True)

            if success:
                # Log to database
                log_email_sent(
                    recruiter_id=rec_id,
                    company=company,
                    recruiter_email=email,
                    subject=subject,
                    personalization=hook_key,
                )

                sent_count += 1
                contacts_sent.append({
                    "company":   company,
                    "role":      role,
                    "email":     email,
                    "hook_key":  hook_key,
                    "first_name": first_name,
                })

                # Random delay between sends
                if sent_count < DAILY_LIMIT:
                    random_delay()

            else:
                errors.append(f"Failed to send to {email} at {company}")

    except Exception as e:
        error_msg = f"Critical emailer error: {e}"
        logging.error(f"❌ {error_msg}")
        errors.append(error_msg)

    finally:
        if server:
            try:
                server.quit()
            except:
                pass

    logging.info(f"\n{'='*55}")
    logging.info(f"✅ Send complete: {sent_count} emails sent")
    logging.info(f"{'='*55}\n")

    return sent_count, contacts_sent, "\n".join(errors)


# ── FOLLOW-UP SENDER ──────────────────────────────────────────────

def send_followups(followup_candidates):
    """
    Sends follow-up emails to recruiters who haven't replied in 5 days.

    Args:
        followup_candidates: list of email_sent rows from database
            (output of database.get_followup_candidates())

    Returns:
        Number of follow-ups sent
    """
    if not followup_candidates:
        logging.info("📭 No follow-ups needed today.")
        return 0

    sent_count = 0
    server     = None

    logging.info(f"\n{'='*55}")
    logging.info(f"🔁 Sending {len(followup_candidates)} follow-up(s)...")
    logging.info(f"{'='*55}")

    try:
        server = get_smtp_connection()

        for record in followup_candidates:
            email            = record["recruiter_email"]
            company          = record["company"]
            original_subject = record["subject"]

            role = extract_role_from_subject(original_subject)

            # Build follow-up using the same recruiter name from original
            # (we don't store first_name in emails_sent — use generic)
            subject, body = followup_email(
                recruiter_first_name="",
                company=company,
                role=role,
                original_subject=original_subject,
            )

            logging.info(f"\n🔁 Follow-up → {email} at {company}")

            success = send_single_email(
                server, email, subject, body, attach_resume=True
            )

            if success:
                mark_followup_sent(record["id"])
                sent_count += 1
                random_delay()

    except Exception as e:
        logging.error(f"❌ Follow-up sender error: {e}")

    finally:
        if server:
            try:
                server.quit()
            except:
                pass

    logging.info(f"✅ Follow-ups sent: {sent_count}")
    return sent_count


# ── DAILY SUMMARY SENDER ──────────────────────────────────────────

def send_daily_summary(
    date,
    jobs_found,
    emails_found,
    emails_sent,
    followups_sent,
    companies_skipped,
    contacts_sent_to,
    errors="",
):
    """
    Sends Harsh a summary email every morning after the script runs.
    Goes to YOUR_EMAIL (same as Gmail account).
    """
    if not NOTIFICATIONS.get("send_daily_summary", True):
        return

    recipient = NOTIFICATIONS.get("summary_recipient", GMAIL_USER)

    try:
        all_time = get_all_time_stats()
        subject, body = daily_summary_email(
            date=date,
            jobs_found=jobs_found,
            emails_found=emails_found,
            emails_sent=emails_sent,
            followups_sent=followups_sent,
            companies_skipped=companies_skipped,
            contacts_sent_to=contacts_sent_to,
            all_time_stats=all_time,
            errors=errors,
        )

        server = get_smtp_connection()
        send_single_email(server, recipient, subject, body, attach_resume=False)
        server.quit()
        logging.info(f"📊 Daily summary sent to {recipient}")

    except Exception as e:
        logging.error(f"❌ Could not send daily summary: {e}")
