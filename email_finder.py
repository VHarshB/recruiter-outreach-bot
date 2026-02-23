# email_finder.py
# ================================================================
#  FINDS RECRUITER EMAILS — 5 free methods, tried in order
#
#  Method 1: Apollo.io API        (50 free credits/month)
#  Method 2: Scrape careers page  (finds emails in HTML)
#  Method 3: Google dorking       (searches for @company.com publicly)
#  Method 4: Pattern + SMTP verify (guesses firstname@company.com etc.)
#  Method 5: ASU alumni search    (finds ASU grads working there)
#
#  For each company, tries methods in order until it finds emails.
#  Returns list of {email, first_name, last_name, title, method}
# ================================================================

import re
import time
import socket
import smtplib
import logging
import requests
from bs4 import BeautifulSoup
from config import EMAIL_FINDER, YOUR_INFO

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

APOLLO_KEY     = EMAIL_FINDER.get("apollo_api_key", "")
MAX_PER_COMPANY = EMAIL_FINDER.get("max_per_company", 3)

# Common email patterns to guess — tried in this order
EMAIL_PATTERNS = [
    "{first}@{domain}",
    "{first}.{last}@{domain}",
    "{first}{last}@{domain}",
    "{f}{last}@{domain}",
    "{first}_{last}@{domain}",
    "recruiting@{domain}",
    "recruiter@{domain}",
    "careers@{domain}",
    "talent@{domain}",
    "hr@{domain}",
    "jobs@{domain}",
    "hiring@{domain}",
]

# Recruiter-related title keywords — we prioritize these people
RECRUITER_TITLES = [
    "recruiter", "recruiting", "talent", "hr", "human resources",
    "people operations", "university recruiting", "campus recruiting",
    "technical recruiter", "engineering recruiter", "intern"
]


# ── HELPERS ───────────────────────────────────────────────────────

def is_recruiter_title(title):
    """Check if a job title suggests this person does recruiting."""
    title_lower = title.lower()
    return any(kw in title_lower for kw in RECRUITER_TITLES)


def extract_emails_from_text(text, domain=None):
    """Pull all email addresses from a block of text."""
    pattern = r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}"
    emails = re.findall(pattern, text)
    if domain:
        # Prefer emails matching the company domain
        company_emails = [e for e in emails if domain in e]
        return company_emails if company_emails else emails
    return list(set(emails))


def smtp_verify_email(email):
    """
    Verify an email address exists WITHOUT sending any email.
    Uses SMTP handshake — connects to mail server and asks if mailbox exists.
    Returns True if verified, False if not, None if inconclusive.

    Requires dnspython: pip install dnspython
    If not installed, skips verification and returns None (email still kept).
    """
    if not EMAIL_FINDER.get("smtp_verify", True):
        return None  # skip verification if disabled in config

    # Check dnspython is available — give a clear warning if not
    try:
        import dns.resolver
    except ImportError:
        # Only warn once, not on every call
        if not getattr(smtp_verify_email, "_warned", False):
            logging.warning(
                "⚠️  dnspython not installed — SMTP email verification is disabled.\n"
                "   Emails will still be found but not pre-verified.\n"
                "   To enable verification: pip install dnspython"
            )
            smtp_verify_email._warned = True
        return None  # inconclusive — keep the email, just unverified

    try:
        domain = email.split("@")[1]

        # Get MX records (which mail server handles this domain)
        mx_records = dns.resolver.resolve(domain, "MX")
        mx_host = str(sorted(mx_records, key=lambda r: r.preference)[0].exchange)

        # Connect to mail server and ask if mailbox exists
        # No email is sent — we just knock on the door
        server = smtplib.SMTP(timeout=10)
        server.connect(mx_host, 25)
        server.helo("verify.example.com")
        server.mail("verify@example.com")
        code, _ = server.rcpt(email)
        server.quit()

        return code == 250  # 250 = mailbox exists

    except dns.resolver.NXDOMAIN:
        return False   # domain doesn't exist at all
    except dns.resolver.NoAnswer:
        return None    # domain exists but no MX record — inconclusive
    except smtplib.SMTPConnectError:
        return None    # server blocked our connection — inconclusive
    except Exception:
        return None    # any other error — keep email, just unverified


# ── METHOD 1: APOLLO.IO API ───────────────────────────────────────

def find_via_apollo(company, domain):
    """
    Apollo.io has a free plan with 50 email credits/month.
    Sign up free at: https://apollo.io
    Returns list of recruiter contacts at the company.
    """
    if not APOLLO_KEY:
        logging.debug("  Apollo API key not set — skipping")
        return []

    logging.info(f"  🔍 Method 1: Apollo.io → {company}")
    contacts = []

    try:
        # Search for people at this company with recruiting titles
        url = "https://api.apollo.io/v1/mixed_people/search"
        payload = {
            "api_key": APOLLO_KEY,
            "q_organization_domains": [domain],
            "person_titles": ["recruiter", "talent acquisition", "university recruiting",
                              "campus recruiter", "hr", "technical recruiter"],
            "per_page": 5,
        }

        resp = requests.post(url, json=payload, headers=HEADERS, timeout=15)
        data = resp.json()

        people = data.get("people", [])
        for person in people:
            email = person.get("email", "")
            if not email or "gmail" in email or "yahoo" in email:
                continue

            contacts.append({
                "email":      email,
                "first_name": person.get("first_name", ""),
                "last_name":  person.get("last_name", ""),
                "title":      person.get("title", ""),
                "method":     "apollo",
                "verified":   True,   # Apollo pre-verifies emails
            })

        if contacts:
            logging.info(f"    ✅ Apollo found {len(contacts)} contacts")
        else:
            logging.info(f"    ⚠️ Apollo: no results for {domain}")

    except Exception as e:
        logging.error(f"    ❌ Apollo failed: {e}")

    return contacts[:MAX_PER_COMPANY]


# ── METHOD 2: SCRAPE COMPANY CAREERS / ABOUT PAGE ─────────────────

def find_via_careers_page(company, domain):
    """
    Visits the company's careers and about pages looking for
    email addresses sitting in the HTML — very common for
    mid-size companies that list a recruiting contact.
    """
    logging.info(f"  🔍 Method 2: Careers page scrape → {domain}")
    contacts = []
    found_emails = set()

    pages_to_check = [
        f"https://{domain}/careers",
        f"https://{domain}/jobs",
        f"https://{domain}/about",
        f"https://{domain}/contact",
        f"https://{domain}/team",
        f"https://www.{domain}/careers",
        f"https://www.{domain}/jobs",
    ]

    for url in pages_to_check:
        try:
            resp = requests.get(url, headers=HEADERS, timeout=10)
            if resp.status_code != 200:
                continue

            soup = BeautifulSoup(resp.text, "html.parser")
            text = soup.get_text(separator=" ")

            emails = extract_emails_from_text(text, domain)

            for email in emails:
                if email in found_emails:
                    continue
                if any(skip in email for skip in ["noreply", "no-reply", "support", "info@", "contact@"]):
                    continue
                found_emails.add(email)

                # Try to find person's name near this email in the HTML
                email_pattern = re.escape(email)
                surrounding = re.search(
                    rf"(.{{0,100}}){email_pattern}(.{{0,100}})",
                    text
                )
                context = surrounding.group(0) if surrounding else ""

                contacts.append({
                    "email":      email,
                    "first_name": "",   # hard to extract reliably from page text
                    "last_name":  "",
                    "title":      "Recruiter" if is_recruiter_title(context) else "HR/Recruiting",
                    "method":     "careers_page",
                    "verified":   False,
                })

            if contacts:
                break  # found emails on this page, stop checking others

            time.sleep(1)

        except Exception:
            continue

    if contacts:
        logging.info(f"    ✅ Careers page found {len(contacts)} emails")
    else:
        logging.info(f"    ⚠️ No emails found on careers page")

    return contacts[:MAX_PER_COMPANY]


# ── METHOD 3: GOOGLE DORKING ──────────────────────────────────────

def find_via_google_dork(company, domain):
    """
    Uses Google search to find publicly listed recruiter emails.
    Search query: "@company.com" "recruiter" OR "hiring" site:linkedin.com OR site:company.com
    This only finds emails that people have posted publicly themselves.
    """
    logging.info(f"  🔍 Method 3: Google dorking → {domain}")
    contacts = []

    queries = [
        f'"{domain}" recruiter email',
        f'site:{domain} "recruiter" OR "talent" email',
        f'"{company}" recruiter "@{domain}"',
    ]

    for query in queries:
        try:
            # Use Google's public search (basic, no API key)
            search_url = f"https://www.google.com/search?q={requests.utils.quote(query)}&num=10"
            resp = requests.get(search_url, headers=HEADERS, timeout=10)

            if resp.status_code == 429:
                logging.warning("    ⚠️ Google rate limited — waiting 30s")
                time.sleep(30)
                continue

            soup = BeautifulSoup(resp.text, "html.parser")
            text = soup.get_text(separator=" ")

            emails = extract_emails_from_text(text, domain)

            for email in emails:
                if any(skip in email for skip in ["noreply", "no-reply", "support"]):
                    continue
                contacts.append({
                    "email":      email,
                    "first_name": email.split("@")[0].split(".")[0].capitalize(),
                    "last_name":  "",
                    "title":      "Recruiter",
                    "method":     "google_dork",
                    "verified":   False,
                })

            if contacts:
                break

            time.sleep(3)  # be polite — avoid Google rate limits

        except Exception as e:
            logging.debug(f"    Google dork failed: {e}")

    if contacts:
        logging.info(f"    ✅ Google dork found {len(contacts)} emails")
    else:
        logging.info(f"    ⚠️ Google dork: no results")

    return contacts[:MAX_PER_COMPANY]


# ── METHOD 4: EMAIL PATTERN GUESSING + SMTP VERIFY ────────────────

def find_via_pattern_guess(company, domain, known_names=None):
    """
    Guesses common email patterns and verifies them via SMTP ping.
    No email is ever sent — just checks if the mailbox exists.

    If we know a recruiter's name (e.g. from LinkedIn search), we try
    firstname@domain, firstname.lastname@domain, etc.

    If we don't know a name, we try generic ones:
    recruiting@domain, hr@domain, careers@domain, talent@domain
    """
    logging.info(f"  🔍 Method 4: Pattern guessing → {domain}")
    contacts = []

    # Always try these generic recruiting addresses first
    generic_guesses = [
        ("recruiting", "", "recruiting@" + domain, "Recruiting Team"),
        ("talent",     "", "talent@" + domain,     "Talent Team"),
        ("hr",         "", "hr@" + domain,          "HR Team"),
        ("careers",    "", "careers@" + domain,     "Careers Team"),
        ("hiring",     "", "hiring@" + domain,      "Hiring Team"),
        ("jobs",       "", "jobs@" + domain,        "Jobs Team"),
    ]

    for first, last, email, title in generic_guesses:
        verified = smtp_verify_email(email)
        if verified:
            contacts.append({
                "email":      email,
                "first_name": first.capitalize(),
                "last_name":  last,
                "title":      title,
                "method":     "pattern_generic",
                "verified":   True,
            })

        if len(contacts) >= MAX_PER_COMPANY:
            break

    # If we have known names, also try personal patterns
    if known_names and len(contacts) < MAX_PER_COMPANY:
        for name_dict in known_names:
            first = name_dict.get("first", "").lower()
            last  = name_dict.get("last", "").lower()

            if not first:
                continue

            for pattern in EMAIL_PATTERNS[:6]:  # try top 6 patterns
                try:
                    email = pattern.format(
                        first=first,
                        last=last,
                        f=first[0] if first else "",
                        domain=domain
                    )
                    verified = smtp_verify_email(email)
                    if verified:
                        contacts.append({
                            "email":      email,
                            "first_name": first.capitalize(),
                            "last_name":  last.capitalize(),
                            "title":      name_dict.get("title", "Recruiter"),
                            "method":     "pattern_personal",
                            "verified":   True,
                        })
                        break  # found working pattern for this person
                except Exception:
                    continue

            if len(contacts) >= MAX_PER_COMPANY:
                break

    if contacts:
        logging.info(f"    ✅ Pattern guess found {len(contacts)} verified emails")
    else:
        logging.info(f"    ⚠️ Pattern guess: no verified emails found")

    return contacts


# ── METHOD 5: ASU ALUMNI SEARCH ───────────────────────────────────

def find_via_asu_alumni(company, domain):
    """
    Searches for ASU alumni working at the target company.
    Strategy: Google search for ASU alums at company on LinkedIn.

    Why this works: Reply rate jumps from ~10% to ~30% when
    you mention a shared university connection.
    We extract their name, then use pattern guessing for their email.
    """
    if not EMAIL_FINDER.get("asu_alumni_search", True):
        return []

    logging.info(f"  🔍 Method 5: ASU alumni search → {company}")
    alumni_names = []

    try:
        query = (
            f'site:linkedin.com "{company}" '
            f'"Arizona State" OR "ASU" '
            f'recruiter OR "talent acquisition" OR "university recruiting"'
        )
        search_url = f"https://www.google.com/search?q={requests.utils.quote(query)}&num=10"
        resp = requests.get(search_url, headers=HEADERS, timeout=10)

        soup = BeautifulSoup(resp.text, "html.parser")

        # LinkedIn result titles often look like: "John Smith - Technical Recruiter - Company"
        result_titles = soup.find_all("h3")
        for title_el in result_titles:
            title_text = title_el.get_text(strip=True)

            # Extract name from LinkedIn-style title: "FirstName LastName - Title - Company"
            parts = title_text.split(" - ")
            if len(parts) >= 2:
                name_part = parts[0].strip()
                role_part = parts[1].strip() if len(parts) > 1 else ""
                name_words = name_part.split()

                if len(name_words) >= 2:
                    alumni_names.append({
                        "first": name_words[0],
                        "last":  name_words[-1],
                        "title": role_part,
                        "is_asu_alum": True,
                    })

        time.sleep(2)

    except Exception as e:
        logging.debug(f"    ASU alumni search failed: {e}")

    if alumni_names:
        logging.info(f"    🎓 Found {len(alumni_names)} potential ASU alumni at {company}")
        # Now try to find their email via pattern guessing
        return find_via_pattern_guess(company, domain, known_names=alumni_names)
    else:
        logging.info(f"    ⚠️ No ASU alumni found at {company}")
        return []


# ── MAIN FINDER FUNCTION ──────────────────────────────────────────

def find_recruiter_emails(company, domain):
    """
    Master function — tries all 5 methods in order.
    Stops as soon as it has enough contacts (max 3 per company).
    Returns list of contact dicts.

    Each dict has:
        email, first_name, last_name, title, method, verified
    """
    logging.info(f"\n📧 Finding emails for: {company} ({domain})")
    all_contacts = []
    seen_emails  = set()

    def add_contacts(new_contacts):
        for c in new_contacts:
            if c["email"] not in seen_emails:
                seen_emails.add(c["email"])
                all_contacts.append(c)

    # Method 1: Apollo (best quality, limited monthly credits)
    if APOLLO_KEY:
        add_contacts(find_via_apollo(company, domain))
        if len(all_contacts) >= MAX_PER_COMPANY:
            return all_contacts[:MAX_PER_COMPANY]

    # Method 2: Careers page scrape
    add_contacts(find_via_careers_page(company, domain))
    if len(all_contacts) >= MAX_PER_COMPANY:
        return all_contacts[:MAX_PER_COMPANY]

    # Method 3: Google dorking
    add_contacts(find_via_google_dork(company, domain))
    if len(all_contacts) >= MAX_PER_COMPANY:
        return all_contacts[:MAX_PER_COMPANY]

    # Method 4: Pattern guessing + SMTP verify
    add_contacts(find_via_pattern_guess(company, domain))
    if len(all_contacts) >= MAX_PER_COMPANY:
        return all_contacts[:MAX_PER_COMPANY]

    # Method 5: ASU alumni search (bonus — higher reply rate!)
    add_contacts(find_via_asu_alumni(company, domain))

    if not all_contacts:
        logging.info(f"  ❌ Could not find any emails for {company} — skipping")

    return all_contacts[:MAX_PER_COMPANY]


# ── QUICK TEST ────────────────────────────────────────────────────
if __name__ == "__main__":
    # Test with a real company:
    # python email_finder.py
    test_company = "Stripe"
    test_domain  = "stripe.com"
    results = find_recruiter_emails(test_company, test_domain)
    print(f"\n✅ Found {len(results)} contacts at {test_company}:")
    for r in results:
        print(f"  {r['first_name']} {r['last_name']} — {r['email']} ({r['method']})")
