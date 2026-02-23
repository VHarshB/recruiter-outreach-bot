# 🚀 Harsh's Internship Email Automation

Automatically finds fresh CS internship postings daily, locates recruiter emails
for free, and sends 30–40 personalized emails using your real resume highlights.

---

## 📁 File Overview

| File | What it does |
|------|-------------|
| `main.py` | Brain — runs the full pipeline |
| `config.py` | All your settings (pre-filled from your resume) |
| `scraper.py` | Finds fresh internship postings from 4 sources |
| `email_finder.py` | Finds recruiter emails using 5 free methods |
| `database.py` | Tracks everyone contacted (SQLite) |
| `templates.py` | Your personalized email templates |
| `emailer.py` | Sends emails via Gmail |

---

## ⚡ Setup (One Time, ~10 Minutes)

### Step 1 — Install Python libraries
```bash
pip install -r requirements.txt
```

### Step 2 — Add your resume PDF
Place your resume in the project folder named exactly:
```
Harsh_Vaishya_Resume.pdf
```

### Step 3 — Create your .env file
Copy the template and fill it in:
```bash
cp .env.template .env
```
Then open `.env` and fill in your Gmail App Password and Apollo key.

### Step 4 — Get Gmail App Password
1. Go to https://myaccount.google.com/security
2. Enable 2-Step Verification (if not already on)
3. Search "App passwords" → create one named "Internship Mailer"
4. Copy the 16-character password into `.env`

### Step 5 — Get free Apollo API key (optional)
1. Sign up free at https://app.apollo.io
2. Go to Settings → API → copy your key into `.env`

### Step 6 — Test with a dry run first!
```bash
python main.py --test
```
This finds jobs and emails but sends NOTHING.
Review the output to make sure everything looks right.

### Step 7 — Run for real
```bash
python main.py
```

### Step 8 — Schedule it to run every day automatically
```bash
python main.py --schedule
```
Keep this terminal open (or run it on a server / Raspberry Pi).

---

## 📋 Daily Commands

```bash
# Run once right now
python main.py

# Run every day at 8 AM automatically
python main.py --schedule

# Dry run — see what would happen, no emails sent
python main.py --test

# Only send follow-ups today
python main.py --followups

# View your all-time stats
python main.py --stats

# Mark a recruiter as replied (stops follow-up to them)
python main.py --got-reply sarah@stripe.com
```

---

## 📊 What Happens Each Day

1. **8:00 AM** — Script wakes up
2. Scrapes 4 job sources for CS internships posted in last 24 hours
3. For each company, tries 5 free methods to find recruiter email
4. Skips anyone already contacted, skips companies already at 3 contacts
5. Picks the best achievement from your resume based on job keywords
6. Sends 35 personalized emails with 45–90 second delays between each
7. Sends follow-ups to anyone who hasn't replied in 5 days
8. Sends YOU a summary email with everything that happened

---

## 🔧 Customization

All settings are in `config.py`:

- Change daily email limit → `EMAIL_SETTINGS["daily_limit"]`
- Change follow-up timing → `EMAIL_SETTINGS["followup_after_days"]`
- Add job title keywords → `SCRAPER["keywords"]`
- Edit achievement hooks → `ACHIEVEMENTS` dict
- Disable ASU alumni search → `EMAIL_FINDER["asu_alumni_search"] = False`

---

## ⚠️ Important Notes

- **Gmail limit**: Gmail allows ~500 emails/day. Our 35/day is well within limits.
- **Spam safety**: Random delays between emails prevent spam detection.
- **Never share** your `.env` file — add it to `.gitignore` if using GitHub.
- **Resume**: Make sure `Harsh_Vaishya_Resume.pdf` is in the project folder.
- **Reply tracking**: When someone replies, run `--got-reply their@email.com` so the system doesn't follow up on them.

---

## 📈 Expected Results

Based on research and real student experiences:

| Week | Expected Outcome |
|------|-----------------|
| Week 1 | 245 emails sent, ~5–10 replies |
| Week 2 | 490 total sent, follow-ups bringing in more replies |
| Week 3 | First phone screens likely happening |
| Month 1 | 1,000+ emails sent, realistic 3–5 interview pipelines |

Reply rates are typically 3–8% for cold email. With your resume (4 hackathon wins, real user metrics, 3.6 GPA), expect to be at the higher end.

---

Good luck Harsh! 🚀 — Built with your resume details pre-loaded.
