#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TK Job Digest — Pro Edition
Runs in GitHub Actions daily (07:00 WAT). Fetches Data Analyst / Data Science /
Intern / Graduate Trainee roles across Nigeria + global remote. Formats an HTML
newsletter (with skills) and delivers via SendGrid (email), Telegram, and WhatsApp.

Env (GitHub Secrets):
  SENDGRID_API_KEY, EMAIL_TO
  TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
  TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_WHATSAPP_FROM, WHATSAPP_TO
"""

import os
import re
import datetime
import requests
import pytz
from bs4 import BeautifulSoup

# -------------------- Settings --------------------
APP_NAME = "TK Job Digest"
SENDER_EMAIL = "adotanko01@gmail.com"          # verified sender
SENDER_NAME  = "TK Job Digest Team"            # professional display name
MAX_JOBS     = 25                              # aim for 15+, allow some buffer
DAYS_WINDOW  = 7                               # freshness window (best-effort)
WAT          = pytz.timezone("Africa/Lagos")

HEADERS = {
    "User-Agent":
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0 Safari/537.36"
}

TITLE_KEYWORDS = [
    # broader catch for titles
    r"\bdata\s*analyst\b",
    r"\bdata\s*science\b",
    r"\banalytics?\b",
    r"\bgraduate\s*trainee\b",
    r"\bintern(ship)?\b",
]

SKILL_KEYWORDS = [
    "SQL", "Excel", "Python", "Power BI", "Tableau", "R",
    "ETL", "Machine Learning", "ML", "Visualization", "Pandas",
    "NumPy", "DAX", "Looker", "DBT", "Airflow"
]

LOGO_URL = "https://raw.githubusercontent.com/AdoTk1/TK_digest/main/assets/tk_logo.png"

# -------------------- Utils --------------------
def now_wat() -> str:
    return datetime.datetime.now(WAT).strftime("%Y-%m-%d %H:%M")

def clean(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "")).strip()

def has_title_keyword(text: str) -> bool:
    t = (text or "").lower()
    for pat in TITLE_KEYWORDS:
        if re.search(pat, t, flags=re.I):
            return True
    return False

def find_skills(text: str) -> list:
    found = []
    low = (text or "")
    for sk in SKILL_KEYWORDS:
        # word-ish match but allow BI/ML etc.
        if re.search(rf"\b{re.escape(sk)}\b", low, flags=re.I):
            found.append(sk)
    return sorted(set(found), key=lambda x: SKILL_KEYWORDS.index(x))[:6]

def normalize_url(base: str, href: str) -> str:
    if not href:
        return ""
    if href.startswith("http"):
        return href
    return requests.compat.urljoin(base, href)

def recency_pass(date_text: str) -> bool:
    """
    Best-effort filter. If site shows 'X days ago' or 'today', keep recent.
    If unknown, keep (we rely on daily schedule + de-dupe).
    """
    s = (date_text or "").lower()
    if any(k in s for k in ["today", "just", "hour"]):
        return True
    m = re.search(r"(\d+)\s+day", s)
    if m:
        return int(m.group(1)) <= DAYS_WINDOW
    # simple ISO date try
    try:
        dt = datetime.datetime.fromisoformat(s[:10])
        return (datetime.datetime.utcnow() - dt).days <= DAYS_WINDOW
    except Exception:
        return True

def role_from_title(title: str) -> str:
    t = (title or "").lower()
    if "graduate" in t and "trainee" in t:
        return "Graduate Trainee"
    if "intern" in t:
        return "Intern"
    if "science" in t:
        return "Data Science"
    if "analyst" in t:
        return "Data Analyst"
    return "Other"

def worktype_from_text(title: str, location: str) -> str:
    t = (title + " " + (location or "")).lower()
    if any(k in t for k in ["remote", "hybrid", "work from home", "anywhere"]):
        return "Remote"
    return "Onsite"

# -------------------- Scrapers --------------------
def scrape_myjobmag():
    url = "https://www.myjobmag.com/search/jobs?q=Data+Analyst"
    out = []
    try:
        r = requests.get(url, headers=HEADERS, timeout=25)
        soup = BeautifulSoup(r.text, "html.parser")
        for a in soup.select("a[href*='/job/']"):
            title = clean(a.get_text())
            if not has_title_keyword(title):
                continue
            link = normalize_url(url, a.get("href"))
            out.append({
                "title": title,
                "company": "—",
                "location": "Nigeria",
                "date": "",
                "source": "MyJobMag",
                "link": link,
                "desc": ""
            })
    except Exception as e:
        print("MyJobMag error:", e)
    return out

def scrape_jobberman():
    url = "https://www.jobberman.com/jobs?q=Data+Analyst"
    out = []
    try:
        r = requests.get(url, headers=HEADERS, timeout=25)
        soup = BeautifulSoup(r.text, "html.parser")
        for a in soup.select("a[href^='/job/']"):
            title = clean(a.get_text())
            if not has_title_keyword(title):
                continue
            link = normalize_url("https://www.jobberman.com", a.get("href"))
            out.append({
                "title": title,
                "company": "—",
                "location": "Nigeria",
                "date": "",
                "source": "Jobberman",
                "link": link,
                "desc": ""
            })
    except Exception as e:
        print("Jobberman error:", e)
    return out

def scrape_jobzilla():
    url = "https://www.jobzilla.ng/jobs/data-analyst"
    out = []
    try:
        r = requests.get(url, headers=HEADERS, timeout=25)
        soup = BeautifulSoup(r.text, "html.parser")
        for card in soup.select("a.job-link, h2 a"):
            title = clean(card.get_text())
            if not has_title_keyword(title):
                continue
            link = normalize_url(url, card.get("href"))
            out.append({
                "title": title,
                "company": "—",
                "location": "Nigeria",
                "date": "",
                "source": "Jobzilla",
                "link": link,
                "desc": ""
            })
    except Exception as e:
        print("Jobzilla error:", e)
    return out

def scrape_hotnigerianjobs():
    url = "https://www.hotnigerianjobs.com/search?query=Data+Analyst"
    out = []
    try:
        r = requests.get(url, headers=HEADERS, timeout=25)
        soup = BeautifulSoup(r.text, "html.parser")
        for a in soup.select("a[href*='/post/'], a[href*='/p/']"):
            title = clean(a.get_text())
            if not has_title_keyword(title):
                continue
            link = normalize_url("https://www.hotnigerianjobs.com", a.get("href"))
            out.append({
                "title": title,
                "company": "—",
                "location": "Nigeria",
                "date": "",
                "source": "HotNigerianJobs",
                "link": link,
                "desc": ""
            })
    except Exception as e:
        print("HotNigerianJobs error:", e)
    return out

def scrape_indeed_nigeria():
    url = "https://ng.indeed.com/jobs?q=Data+Analyst+OR+Data+Science+OR+Graduate+Trainee+OR+Intern&l=Nigeria"
    out = []
    try:
        r = requests.get(url, headers=HEADERS, timeout=25)
        soup = BeautifulSoup(r.text, "html.parser")
        for c in soup.select("a.tapItem"):
            title = clean(c.select_one("h2 span").get_text() if c.select_one("h2 span") else "")
            if not has_title_keyword(title):
                continue
            link = normalize_url("https://ng.indeed.com", c.get("href"))
            comp = clean(c.select_one(".companyName").get_text() if c.select_one(".companyName") else "—")
            loc  = clean(c.select_one(".companyLocation").get_text() if c.select_one(".companyLocation") else "Nigeria")
            date = clean(c.select_one(".date").get_text() if c.select_one(".date") else "")
            out.append({
                "title": title, "company": comp, "location": loc,
                "date": date, "source": "Indeed (NG)", "link": link, "desc": ""
            })
    except Exception as e:
        print("Indeed NG error:", e)
    return out

def scrape_indeed_global_remote():
    # US + Europe remote – Indeed global remote search
    url = "https://www.indeed.com/jobs?q=Data+Analyst+OR+Data+Science+OR+Intern+OR+Graduate+Trainee&l=Remote"
    out = []
    try:
        r = requests.get(url, headers=HEADERS, timeout=25)
        soup = BeautifulSoup(r.text, "html.parser")
        for c in soup.select("a.tapItem"):
            title = clean(c.select_one("h2 span").get_text() if c.select_one("h2 span") else "")
            if not has_title_keyword(title):
                continue
            link = normalize_url("https://www.indeed.com", c.get("href"))
            comp = clean(c.select_one(".companyName").get_text() if c.select_one(".companyName") else "—")
            loc  = clean(c.select_one(".companyLocation").get_text() if c.select_one(".companyLocation") else "Remote")
            date = clean(c.select_one(".date").get_text() if c.select_one(".date") else "")
            out.append({
                "title": title, "company": comp, "location": loc,
                "date": date, "source": "Indeed (Remote)", "link": link, "desc": ""
            })
    except Exception as e:
        print("Indeed Remote error:", e)
    return out

# -------------------- Merge + Rank --------------------
def collect_jobs():
    all_lists = [
        scrape_myjobmag(),
        scrape_jobberman(),
        scrape_jobzilla(),
        scrape_hotnigerianjobs(),
        scrape_indeed_nigeria(),
        scrape_indeed_global_remote(),
    ]
    dup = set()
    merged = []
    for lst in all_lists:
        for j in lst:
            key = (j["title"].lower(), j["link"])
            if key in dup:
                continue
            dup.add(key)
            role = role_from_title(j["title"])
            wtype = worktype_from_text(j["title"], j.get("location", ""))
            skills = find_skills(" ".join([j["title"], j.get("desc","")]))
            if not recency_pass(j.get("date","")):
                continue
            j.update({"role_type": role, "worktype": wtype, "skills": skills})
            merged.append(j)

    # Sort: Remote first, then by source preference, then title
    source_priority = {
        "Indeed (Remote)": 0, "Indeed (NG)": 1,
        "MyJobMag": 2, "Jobberman": 3, "Jobzilla": 4, "HotNigerianJobs": 5
    }
    merged.sort(key=lambda x: (
        0 if x["worktype"] == "Remote" else 1,
        source_priority.get(x["source"], 9),
        x["title"].lower()
    ))
    return merged[:MAX_JOBS]

# -------------------- Formatters --------------------
def html_email(jobs):
    if not jobs:
        return f"""
        <div style='font-family:Arial;padding:20px'>
          <img src='{LOGO_URL}' style='width:100%;max-width:900px;border-radius:10px'>
          <h2 style='margin:16px 0'>💼 {APP_NAME}</h2>
          <p>No new matching roles found today. Check back tomorrow.</p>
          <p style='color:#8a8f98;font-size:12px'>Generated {now_wat()} WAT</p>
        </div>
        """
    rows = []
    for j in jobs:
        skills_badges = "".join(
            f"<span style='display:inline-block;background:#eef2ff;color:#273c75;"
            f"border-radius:999px;padding:2px 8px;margin:2px;font-size:12px'>{s}</span>"
            for s in (j.get("skills") or [])
        )
        rows.append(f"""
        <tr>
          <td style='padding:10px;border-bottom:1px solid #eee'>
            <strong>{j['title']}</strong><br>
            <span style='color:#556'>{j['company']}</span>
          </td>
          <td style='padding:10px;border-bottom:1px solid #eee'>{j['location']}</td>
          <td style='padding:10px;border-bottom:1px solid #eee'>{j['role_type']}</td>
          <td style='padding:10px;border-bottom:1px solid #eee'>{j['worktype']}</td>
          <td style='padding:10px;border-bottom:1px solid #eee'>{skills_badges}</td>
          <td style='padding:10px;border-bottom:1px solid #eee'><a href="{j['link']}">Apply</a></td>
          <td style='padding:10px;border-bottom:1px solid #eee;color:#6b7280'>{j['source']}</td>
        </tr>
        """)
    return f"""
    <div style='font-family:Arial;background:#f7f9fc'>
      <div style='max-width:940px;margin:auto;background:#fff;border-radius:12px;overflow:hidden;
                  box-shadow:0 8px 24px rgba(0,0,0,0.06)'>
        <img src='{LOGO_URL}' style='width:100%;display:block'>
        <div style='padding:20px 24px'>
          <h2 style='margin:0 0 8px;color:#1f2d5a'>💼 {APP_NAME}</h2>
          <p style='margin:0 0 16px;color:#475569'>Nigeria + Global Remote — {now_wat()} WAT</p>
          <table role='table' style='width:100%;border-collapse:collapse'>
            <thead>
              <tr>
                <th align='left' style='padding:8px;border-bottom:2px solid #e2e8f0'>Role</th>
                <th align='left' style='padding:8px;border-bottom:2px solid #e2e8f0'>Company</th>
                <th align='left' style='padding:8px;border-bottom:2px solid #e2e8f0'>Location</th>
                <th align='left' style='padding:8px;border-bottom:2px solid #e2e8f0'>Type</th>
                <th align='left' style='padding:8px;border-bottom:2px solid #e2e8f0'>Skills</th>
                <th align='left' style='padding:8px;border-bottom:2px solid #e2e8f0'>Apply</th>
                <th align='left' style='padding:8px;border-bottom:2px solid #e2e8f0'>Source</th>
              </tr>
            </thead>
            <tbody>
              {''.join(rows)}
            </tbody>
          </table>
          <p style='color:#94a3b8;font-size:12px;margin-top:16px'>
            Generated automatically at 7:00 AM WAT • {APP_NAME}
          </p>
        </div>
      </div>
    </div>
    """

def text_broadcast(jobs):
    if not jobs:
        return f"{APP_NAME}: No jobs today ({now_wat()} WAT)"
    lines = [f"💼 {APP_NAME} — {now_wat()} WAT (NG + Global Remote)"]
    for i, j in enumerate(jobs, 1):
        skills = ", ".join(j.get("skills") or [])
        skills_part = f" • Skills: {skills}" if skills else ""
        lines.append(f"{i}. {j['title']} • {j['company']} • {j['location']} • {j['worktype']}{skills_part}\n{j['link']}")
    return "\n\n".join(lines[:15])

# -------------------- Senders --------------------
def send_email_sendgrid(html_body):
    api_key = os.environ.get("SENDGRID_API_KEY")
    to_email = os.environ.get("EMAIL_TO")
    if not api_key or not to_email:
        print("⚠️ Missing SENDGRID_API_KEY or EMAIL_TO — skipping email.")
        return
    from sendgrid import SendGridAPIClient
    from sendgrid.helpers.mail import Mail, Email, To

    message = Mail(
        from_email=Email(SENDER_EMAIL, SENDER_NAME),
        to_emails=To(to_email),
        subject=f"📊 {APP_NAME} — {now_wat()} WAT",
        html_content=html_body
    )
    try:
        resp = SendGridAPIClient(api_key).send(message)
        print("✅ Email status:", resp.status_code)
    except Exception as e:
        print("❌ SendGrid error:", e)

def send_telegram(text):
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        print("⚠️ Telegram not configured.")
        return
    try:
        r = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            data={"chat_id": chat_id, "text": text, "disable_web_page_preview": True},
            timeout=20
        )
        print("📨 Telegram:", r.status_code)
    except Exception as e:
        print("❌ Telegram error:", e)

def send_whatsapp(text):
    sid  = os.environ.get("TWILIO_ACCOUNT_SID")
    tok  = os.environ.get("TWILIO_AUTH_TOKEN")
    wfrm = os.environ.get("TWILIO_WHATSAPP_FROM")
    wto  = os.environ.get("WHATSAPP_TO")
    if not all([sid, tok, wfrm, wto]):
        print("⚠️ WhatsApp not configured.")
        return
    try:
        from twilio.rest import Client
        msg = Client(sid, tok).messages.create(from_=wfrm, to=wto, body=text)
        print("✅ WhatsApp SID:", msg.sid)
    except Exception as e:
        print("❌ WhatsApp error:", e)

# -------------------- Main --------------------
def main():
    jobs = collect_jobs()
    html = html_email(jobs)
    text = text_broadcast(jobs)

    send_email_sendgrid(html)
    send_telegram(text)
    send_whatsapp(text)

    print(f"✅ Finished: {len(jobs)} jobs sent — {now_wat()} WAT")

if __name__ == "__main__":
    main()
