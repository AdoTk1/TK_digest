# TK Job Digest – Daily Job Fetcher

This GitHub-based automation fetches **Data Analyst, Intern, and Graduate Trainee** roles targeting Nigeria, formats a mini **HTML newsletter**, and **sends it every day at 7:00 AM WAT** to:
- Email (via **SendGrid**)
- WhatsApp (via **Twilio**)
- Telegram (via **Bot API**)

## Filters
- **Data Analyst** & **Intern** → **Remote** (Nigeria/Africa/Global that accepts Nigeria)
- **Graduate Trainee** → **Onsite** (Nigeria)
- Only jobs from the **last 7 days**
- Returns up to **15** postings daily

> Note: Public job sites frequently change HTML. The parser includes fallback selectors. If a site changes, update the scraper section in `fetch_jobs.py`.

---

## Quick Start

1. **Create a new GitHub repo** and upload the files from this folder.
2. Add **Repository Secrets**: *Settings → Secrets and variables → Actions → New repository secret*

| Secret Name | Description |
|---|---|
| `SENDGRID_API_KEY` | SendGrid API key |
| `EMAIL_TO` | Destination email address |
| `TWILIO_ACCOUNT_SID` | Twilio Account SID |
| `TWILIO_AUTH_TOKEN` | Twilio Auth Token |
| `TWILIO_WHATSAPP_FROM` | e.g., `whatsapp:+14155238886` |
| `WHATSAPP_TO` | e.g., `whatsapp:+234XXXXXXXXXX` |
| `TELEGRAM_BOT_TOKEN` | Telegram Bot token from @BotFather |
| `TELEGRAM_CHAT_ID` | Your Telegram chat ID |

3. The workflow is scheduled with cron **`0 6 * * *`** (GitHub Actions uses UTC): that’s **7:00 AM WAT**.

4. To **run manually**: go to **Actions → Daily Job Digest → Run workflow**.

---

## Local Test (optional)
```bash
python -m venv .venv && source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env  # fill in your values
python fetch_jobs.py --once
```

---

## Output
- **Email:** rich HTML newsletter with logo banner and job table/cards
- **Telegram:** compact text summary with links (HTML parse mode)
- **WhatsApp:** concise text with links (Twilio)

---

## Credits
- Built for TK’s **Job Digest** 🇳🇬
- Schedule: **7:00 AM WAT** (06:00 UTC)
