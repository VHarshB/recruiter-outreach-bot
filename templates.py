# templates.py
# ================================================================
#  EMAIL TEMPLATES — pre-filled with Harsh's real resume details
#
#  3 templates total:
#    1. main_email()     — personalized cold email (uses resume hooks)
#    2. followup_email() — polite 5-day follow-up
#    3. daily_summary()  — what Harsh gets every morning
#
#  Personalization logic:
#    Script reads job description keywords → picks the best
#    achievement hook from Harsh's resume to mention.
#    e.g. AWS job → mentions Lambda/Docker project
#         React job → mentions EnKoat portal
#         AI job → mentions Hack SoDA 1st place win
# ================================================================

from config import YOUR_INFO, ACHIEVEMENTS


# ── PERSONALIZATION HOOK SELECTOR ────────────────────────────────

def pick_achievement_hook(job_description="", role=""):
    """
    Reads the job description and role title, picks the most
    relevant achievement from Harsh's resume to mention.
    Returns (hook_text, hook_key) tuple.
    """
    combined = (job_description + " " + role).lower()

    # Check each achievement category's keywords
    for key, data in ACHIEVEMENTS.items():
        if key == "default":
            continue
        if any(kw in combined for kw in data["keywords"]):
            return data["hook"], key

    # Nothing matched — use the default (hackathon wins)
    return ACHIEVEMENTS["default"]["hook"], "default"


def get_recruiter_first_name(first_name):
    """Returns recruiter's first name, or 'there' if unknown."""
    return first_name.strip().capitalize() if first_name and first_name.strip() else "there"


def is_asu_alum_connection(method):
    """Check if this contact was found via ASU alumni search."""
    return method in ["asu_alumni", "pattern_personal"] # pattern_personal often comes from alumni


# ── TEMPLATE 1: MAIN COLD EMAIL ──────────────────────────────────

def main_email(
    recruiter_first_name,
    company,
    role,
    job_url="",
    job_description="",
    find_method="",
):
    """
    Builds the personalized cold email for Harsh.
    Automatically selects the best achievement hook based on job keywords.

    Args:
        recruiter_first_name : recruiter's first name (or empty string)
        company              : company name e.g. "Stripe"
        role                 : job title e.g. "Software Engineer Intern"
        job_url              : link to the posting (optional)
        job_description      : full job description text (used for keyword matching)
        find_method          : how we found this email (used for ASU alumni tweak)

    Returns:
        (subject, body, hook_key) tuple
    """

    name        = get_recruiter_first_name(recruiter_first_name)
    hook, hook_key = pick_achievement_hook(job_description, role)
    is_alum     = is_asu_alum_connection(find_method)

    # ── Subject Line ─────────────────────────────────────────────
    subject = (
        f"ASU CS Junior | 4x Hackathon Winner | {role} @ {company}"
    )

    # ── ASU Alumni connection line (only when relevant) ───────────
    alumni_line = ""
    if is_alum:
        alumni_line = (
            f"I came across your profile while looking for ASU alumni at {company} — "
            f"always excited to connect with fellow Sun Devils!\n\n"
        )

    # ── Body ─────────────────────────────────────────────────────
    body = f"""Hi {name},

{alumni_line}I'm Harsh Vaishya, a junior CS student at Arizona State University (GPA: 3.6) specializing in full-stack development, cloud-native backend systems, and scalable APIs.

I came across {company}'s {role} posting and wanted to reach out directly. {hook}

I believe my experience aligns well with what your team is building at {company}, and I'd love to contribute this summer.

I've attached my resume — you can also see my work at github.com/VHarshB and harshvaishya.tech.

Would you be the right person to connect with about the {role} position, or could you point me in the right direction?

Thank you for your time.

Best,
Harsh Vaishya
ASU Ira A. Fulton Schools of Engineering | CS '27
(480) 465-1376 | hvaishya@asu.edu
linkedin.com/in/harsh-asu/ | github.com/VHarshB | harshvaishya.tech"""

    return subject, body, hook_key


# ── TEMPLATE 2: FOLLOW-UP EMAIL ──────────────────────────────────

def followup_email(
    recruiter_first_name,
    company,
    role,
    original_subject,
    days_since=5,
):
    """
    Polite follow-up sent 5 days after original email with no reply.
    Kept very short — just a bump, not a second pitch.

    Args:
        recruiter_first_name : recruiter's first name
        company              : company name
        role                 : job title
        original_subject     : subject of the original email (for threading)
        days_since           : how many days have passed (for reference)

    Returns:
        (subject, body) tuple
    """
    name = get_recruiter_first_name(recruiter_first_name)

    # Reply to same thread by using "Re:" prefix
    subject = f"Re: {original_subject}"

    body = f"""Hi {name},

Just bumping this up in case it got buried — I know how full inboxes get!

I'm still very interested in the {role} position at {company} this summer. Happy to provide anything else you need — additional code samples, references, or a quick 15-minute call at your convenience.

Thanks again for your time.

Best,
Harsh Vaishya
(480) 465-1376 | hvaishya@asu.edu | github.com/VHarshB"""

    return subject, body


# ── TEMPLATE 3: DAILY SUMMARY EMAIL ──────────────────────────────

def daily_summary_email(
    date,
    jobs_found,
    emails_found,
    emails_sent,
    followups_sent,
    companies_skipped,
    contacts_sent_to,   # list of {company, role, email, hook_key}
    all_time_stats,     # dict from database.get_all_time_stats()
    errors=None,
):
    """
    Summary email sent to Harsh every morning after the script runs.
    Shows exactly what happened, who was emailed, and overall stats.

    Args:
        contacts_sent_to : list of dicts with today's recipients
        all_time_stats   : cumulative stats from the database
    """

    subject = f"📬 Internship Mailer — {date} | {emails_sent} emails sent"

    # Build the contacts table
    if contacts_sent_to:
        contacts_table = "\n".join([
            f"  • {c['company']} ({c['role']}) → {c['email']}  [{c.get('hook_key','default')} hook]"
            for c in contacts_sent_to
        ])
    else:
        contacts_table = "  (none today)"

    # Error section
    error_section = ""
    if errors:
        error_section = f"\n⚠️  ERRORS TODAY:\n{errors}\n"

    # Hook breakdown — what personalization was used most
    if contacts_sent_to:
        hook_counts = {}
        for c in contacts_sent_to:
            hk = c.get("hook_key", "default")
            hook_counts[hk] = hook_counts.get(hk, 0) + 1
        hook_summary = "  " + ", ".join([f"{k}: {v}" for k, v in hook_counts.items()])
    else:
        hook_summary = "  n/a"

    body = f"""Hey Harsh! Here's your daily internship mailer summary.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  TODAY — {date}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  🔍  Jobs found today       : {jobs_found}
  📧  Recruiter emails found  : {emails_found}
  ✉️   Emails sent today       : {emails_sent}
  🔁  Follow-ups sent         : {followups_sent}
  ⏭️   Companies skipped       : {companies_skipped} (already at 3 contacts or already emailed)

  Personalization hooks used:
{hook_summary}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  TODAY'S RECIPIENTS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{contacts_table}

{error_section}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  ALL-TIME STATS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  📨  Total emails sent       : {all_time_stats.get('total_emails_sent', 0)}
  💬  Total replies received  : {all_time_stats.get('total_replies', 0)}
  📈  Overall reply rate      : {all_time_stats.get('reply_rate', '0%')}
  🏢  Companies contacted     : {all_time_stats.get('companies_contacted', 0)}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💡 TIP: If a recruiter replied, run this command so we don't follow up on them:
   python main.py --got-reply recruiter@company.com

Good luck Harsh! 🚀
— Your Internship Mailer Bot
"""

    return subject, body


# ── QUICK TEST ────────────────────────────────────────────────────
if __name__ == "__main__":
    # Test all 3 templates — python templates.py

    print("\n" + "="*60)
    print("TEST 1: Main cold email (AWS job → cloud hook)")
    print("="*60)
    subj, body, hook = main_email(
        recruiter_first_name="Sarah",
        company="Stripe",
        role="Backend Engineer Intern",
        job_description="We use AWS, Docker, Kubernetes and microservices",
    )
    print(f"Subject: {subj}")
    print(f"Hook used: {hook}")
    print(f"\n{body}")

    print("\n" + "="*60)
    print("TEST 2: Main cold email (React job → frontend hook)")
    print("="*60)
    subj2, body2, hook2 = main_email(
        recruiter_first_name="",
        company="Figma",
        role="Frontend Engineer Intern",
        job_description="We work with React, TypeScript, and TailwindCSS",
    )
    print(f"Subject: {subj2}")
    print(f"Hook used: {hook2}")
    print(f"\n{body2}")

    print("\n" + "="*60)
    print("TEST 3: Follow-up email")
    print("="*60)
    subj3, body3 = followup_email(
        recruiter_first_name="Sarah",
        company="Stripe",
        role="Backend Engineer Intern",
        original_subject=subj,
    )
    print(f"Subject: {subj3}")
    print(f"\n{body3}")

    print("\n" + "="*60)
    print("TEST 4: Daily summary email")
    print("="*60)
    subj4, body4 = daily_summary_email(
        date="2026-02-22",
        jobs_found=47,
        emails_found=38,
        emails_sent=35,
        followups_sent=4,
        companies_skipped=6,
        contacts_sent_to=[
            {"company": "Stripe", "role": "Backend Intern", "email": "sarah@stripe.com", "hook_key": "cloud_devops"},
            {"company": "Figma", "role": "Frontend Intern", "email": "john@figma.com", "hook_key": "frontend"},
        ],
        all_time_stats={
            "total_emails_sent": 105,
            "total_replies": 7,
            "reply_rate": "6.7%",
            "companies_contacted": 62,
        }
    )
    print(f"Subject: {subj4}")
    print(f"\n{body4}")
