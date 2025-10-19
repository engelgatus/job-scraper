# Job Scraper 🔍

Automated job scraper that monitors RemoteOK for entry-level automation, operations, and Python roles. Sends matching jobs to Discord via webhook notifications.

## ✨ Features

- **Smart Filtering**: Keywords-based job matching with include/exclude lists
- **Discord Integration**: Rich embed notifications with job details
- **Duplicate Prevention**: Tracks sent jobs to avoid spam
- **Rate Limiting**: Maximum 10 jobs per run to prevent Discord rate limits
- **Customizable Criteria**: Easy configuration for job preferences

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Discord webhook URL

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/engelgatus/job-scraper.git
   cd job-scraper
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env and add your Discord webhook URL
   ```

4. **Run the scraper**
   ```bash
   python scraper.py
   ```

## ⚙️ Configuration

### Discord Webhook Setup

1. Go to your Discord server settings
2. Navigate to **Integrations > Webhooks**
3. Create a new webhook for your jobs channel
4. Copy the webhook URL to your `.env` file

### Job Search Criteria

Edit the keywords in `scraper.py`:

```python
# Jobs must contain at least one of these keywords
INCLUDE_KEYWORDS = [
    'automation', 'n8n', 'python', 'operations', 'administration',
    'coordinator', 'associate', 'entry level'
]

# Jobs must NOT contain any of these keywords
EXCLUDE_KEYWORDS = [
    'customer service', 'sales',
    'senior', 'lead', 'director', 'manager', 'principal'
]
```

## 📄 Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `JOB_WEBHOOK_URL` | Discord webhook URL for notifications | Yes |

## 🔄 Automation

### GitHub Actions (Recommended)

Create `.github/workflows/scraper.yml`:

```yaml
name: Job Scraper

on:
  schedule:
    - cron: '0 */2 * * *'  # Every 2 hours
  workflow_dispatch:      # Manual trigger

jobs:
  scrape:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v4
        with:
          python-version: '3.9'
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run scraper
        env:
          JOB_WEBHOOK_URL: ${{ secrets.JOB_WEBHOOK_URL }}
        run: python scraper.py
```

### Local Scheduling

**Linux/Mac (cron):**
```bash
# Edit crontab
crontab -e

# Add line to run every 2 hours
0 */2 * * * cd /path/to/job-scraper && python scraper.py
```

**Windows (Task Scheduler):**
1. Open Task Scheduler
2. Create Basic Task
3. Set trigger to repeat every 2 hours
4. Set action to run `python scraper.py`

## 📋 Output Example

```
============================================================
🔍 Job Scraper Starting...
============================================================

✅ Fetched 250 jobs from RemoteOK
✅ Sent to Discord: Python Automation Engineer at TechCorp
✅ Sent to Discord: Operations Associate at StartupXYZ

✅ Complete! Sent 2 new job(s) to Discord
============================================================
```

## 🛠️ Customization

### Adding New Job Sources

To add support for other job boards:

1. Create a new function similar to `fetch_remoteok_jobs()`
2. Ensure it returns jobs in the same format
3. Update the `main()` function to use your new source

### Modifying Discord Notifications

Edit the `send_to_discord()` function to customize:
- Embed colors and styling
- Additional job fields
- Notification format

## 📊 Data Storage

- `sent_jobs.json`: Tracks job IDs to prevent duplicate notifications
- Automatically created and maintained by the scraper
- Can be deleted to reset duplicate tracking

## 🔒 Security

- Never commit `.env` files to version control
- Use GitHub secrets for webhook URLs in Actions
- Webhook URLs should be kept private and secure

## 🤝 Contributing

Feel free to:
- Fork and adapt for your job search needs
- Add support for new job boards
- Improve filtering logic
- Submit bug reports and feature requests

## 📄 License

MIT License - see LICENSE file for details

---

**Made with ⚡ by [engelgatus](https://github.com/engelgatus)**

*Companion project to [Discord Command Center Bot](https://github.com/engelgatus/discord-command-center)*