#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TK Job Digest – Daily GitHub Action
- Scrapes Nigeria-focused Data Analyst / Intern / Graduate Trainee roles
- Applies filters (Remote vs Onsite by role type)
- Sends HTML email (SendGrid), Telegram message, and WhatsApp (Twilio)
"""

import os, re, datetime, pytz, requests
from bs4 import BeautifulSoup

APP_NAME = "TK Job Digest"
MAX_JOBS = 15
DAYS_WINDOW = 7
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
}
WAT = pytz.timezone("Africa/Lagos")

# ========== HELPERS ==========
def now_wat_iso():
    return datetime.datetime.now(WAT).strftime("%Y-%m-%d %H:%M")

def clean_space(s):
    return re.sub(r"\s+", " ", s or "").strip()

def infer_role_type(title):
    t = title.lower()
    if "graduate" in t and "trainee" in t:
        return "Graduate Trainee"
    if "intern" in t or "internship" in t:
        return "Intern"
    if "analyst" in t:
        return "Data Analyst"
    return "Other"

def infer_remote_or_onsite(title, location):
    text = (title + " " + (location or "")).lower()
    if "remote" in text or "hybrid" in text or "work from home" in text:
        return "Remote"
    return "Onsite"

def passes_policy(role, remote):
    if role in ["Data Analyst", "Intern"]:
        return remote == "Remote"
    if role == "Graduate Trainee":
        return remote == "Onsite"
    return False

def normalize_url(base, href):
    from urllib.parse import urljoin
    if not href: return ""
    if href.startswith("http"): return href
    return urljoin(base, href)

# ========== SCRAPERS ==========
def scrape_myjobmag():
    url = "https://www.myjobmag.com/search/jobs?q=Data+Analyst"
    jobs = []
    try:
        r = requests.get(url, headers=HEADERS, timeout=25)
        soup = BeautifulSoup(r.text, "html.parser")
        cards = soup.select("a[href*='/job/']")
        for c in cards:
            title = clean_space(c.text)
            link = normalize_url(url, c.get("href"))
            if "analyst" in title.lower():
                jobs.append({
                    "title": title, "company": "—", "location": "Nigeria",
                    "date": "", "source": "MyJobMag", "link": link
                })
    except Exception as e:
        print("MyJobMag error:", e)
    return jobs

def scrape_indeed():
    url = "https://ng.indeed.com/jobs?q=Data+Analyst&l=Nigeria"
    jobs = []
    try:
        r = requests.get(url, headers=HEADERS, timeout=25)
        soup = BeautifulSoup(r.text, "html.parser")
        cards = soup.select("a.tapItem")
        for c in cards:
            title = clean_space(c.select_one("h2 span").text if c.select_one("h2 span") else "")
            link = normalize_url("https://ng.indeed.com", c.get("href"))
            company = clean_space(c.select_one(".companyName").text if c.select_one(".companyName") else "")
            location = clean_space(c.select_one(".companyLocation").text if c.select_one(".companyLocation") else "")
            if "analyst" in title.lower():
                jobs.append({
                    "title": title, "company": company or "—",
                    "location": location or "Nigeria",
                    "date": "", "source": "Indeed", "link": link
                })
    except Exception as e:
        print("Indeed error:", e)
    return jobs

def scrape_jobberman():
    url = "https://www.jobberman.com/jobs?q=Data+Analyst"
    jobs = []
    try:
        r = requests.get(url, headers=HEADERS, timeout=25)
        soup = BeautifulSoup(r.text, "html.parser")
        cards = soup.select("a[href^='/job/']")
        for c in cards:
            title = clean_space(c.text)
            link = normalize_url("https://www.jobberman.com", c.get("href"))
            if "analyst" in title.lower():
                jobs.append({
                    "title": title, "company": "—", "location": "Nigeria",
                    "date": "", "source": "Jobberman", "link": link
                })
    except Exception as e:
        print("Jobberman error:", e)
    return jobs

# ========== FILTER + FORMAT ==========
def merge_and_filter(lists):
    seen, jobs = set(), []
    for lst in lists:
        for j in lst:
            key = (j["title"].lower(), j["link"])
            if key in seen: continue
            seen.add(key)
            role = infer_role_type(j["title"])
            remote = infer_remote_or_onsite(j["title"], j["location"])
            if not passes_policy(role, remote): continue
            jobs.append({**j, "role_type": role, "remote_onsite": remote})
    return jobs[:MAX_JOBS]

def to_html_email(jobs):
    logo_url = "https://raw.githubusercontent.com/AdoTk1/TK_digest/main/assets/tk_logo.png"
    if not jobs:
        return f"""
        <div style='font-family:Arial;padding:20px;'>
          <img src='{logo_url}' style='width:100%;max-width:600px;border-radius:8px;'>
          <h2>{APP_NAME}</h2>
          <p>No new jobs found today.</p>
          <p style='color:#888;'>Generated {now_wat_iso()} WAT</p>
        </div>
        """
    rows = ""
    for j in jobs:
        rows += f"""
        <tr>
          <td>{j['title']}</td>
          <td>{j['company']}</td>
          <td>{j['location']}</td>
          <td>{j['role_type']}</td>
          <td>{j['remote_onsite']}</td>
          <td><a href="{j['link']}">Apply</a></td>
          <td>{j['source']}</td>
        </tr>"""
    html = f"""
    <div style='font-family:Arial;background:#f9fafb;padding:0;margin:0;'>
      <div style='max-width:900px;margin:auto;background:white;border-radius:10px;overflow:hidden;'>
        <img src='{logo_url}' style='width:100%;display:block;'>
        <div style='padding:20px;'>
          <h2>🔥 {APP_NAME}</h2>
          <p>Top {len(jobs)} roles for Data Analysts in Nigeria — {now_wat_iso()} WAT</p>
          <table style='width:100%;border-collapse:collapse;'>
            <tr><th>Title</th><th>Company</th><th>Location</th><th>Role</th><th>Type</th><th>Apply</th><th>Source</th></tr>
            {rows}
          </table>
          <p style='color:#aaa;font-size:12px;'>Generated automatically at 7:00 AM WAT</p>
        </div>
      </div>
    </div>"""
    return html

def to_text_for_messaging(jobs):
    if not jobs:
        return f"{APP_NAME}: No jobs today ({now_wat_iso()} WAT)"
    lines = [f"🔥 {APP_NAME} — {now_wat_iso()} WAT"]
    for i, j in enumerate(jobs, 1):
        lines.append(f"{i}. {j['title']} • {j['company']} • {j['location']} • {j['role_type']} ({j['remote_onsite']})\n{j['link']}")
    return "\n\n".join(lines)

# ========== SENDERS ==========
def send_email_sendgrid(html_body):
    api_key = os.environ.get("SENDGRID_API_KEY")
    to_email = os.environ.get("EMAIL_TO")
    if not api_key or not to_email:
        print("SendGrid not configured, skipping email.")
        return

    from sendgrid import SendGridAPIClient
    from sendgrid.helpers.mail import Mail, Email, To

    html_body = html_body.replace("cid:tk_logo.png", "https://raw.githubusercontent.com/AdoTk1/TK_digest/main/assets/tk_logo.png")

    message = Mail(
        from_email=("no-reply@tk-jobdigest.local", "TK Job Digest"),
        to_emails=[To(to_email)],
        subject=f"💼 Daily Data Analyst Job Digest — {datetime.datetime.now(WAT).strftime('%b %d %Y')}",
        html_content=html_body
    )

    sg = SendGridAPIClient(api_key)
    response = sg.send(message)
    print("Email status:", response.status_code)

def send_telegram(text):
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        print("Telegram not configured, skipping.")
        return
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "disable_web_page_preview": True}
    r = requests.post(url, data=payload, timeout=20)
    print("Telegram:", r.status_code)

def send_whatsapp(text):
    from twilio.rest import Client
    sid = os.environ.get("TWILIO_ACCOUNT_SID")
    token = os.environ.get("TWILIO_AUTH_TOKEN")
    w_from = os.environ.get("TWILIO_WHATSAPP_FROM")
    w_to = os.environ.get("WHATSAPP_TO")
    if not all([sid, token, w_from, w_to]):
        print("Twilio WhatsApp not configured, skipping.")
        return
    client = Client(sid, token)
    msg = client.messages.create(from_=w_from, to=w_to, body=text)
    print("WhatsApp SID:", msg.sid)

# ========== MAIN ==========
def main():
    all_jobs = scrape_myjobmag() + scrape_indeed() + scrape_jobberman()
    jobs = merge_and_filter([all_jobs])
    html_body = to_html_email(jobs)
    text_body = to_text_for_messaging(jobs)

    send_email_sendgrid(html_body)
    send_telegram(text_body)
    send_whatsapp(text_body)
    print(f"✅ Done: {len(jobs)} jobs sent — {now_wat_iso()} WAT")

if __name__ == "__main__":
    main()
