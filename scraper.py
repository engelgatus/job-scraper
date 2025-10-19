"""
Job Scraper for Discord Notifications
Scrapes RemoteOK for entry/associate automation & operations roles
Sends individual notifications to Discord via webhook
Runs automatically via GitHub Actions every 2 hours
"""

import requests
import json
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# ============================================================================
# CONFIGURATION - Job Search Criteria
# ============================================================================

# Discord webhook URL (loaded from environment variable)
WEBHOOK_URL = os.getenv('JOB_WEBHOOK_URL')

# Time window for new jobs (in hours)
JOB_FRESHNESS_HOURS = 3  # Only process jobs from last 3 hours

# Keywords to INCLUDE (job must have at least one of these)
INCLUDE_KEYWORDS = [
    'automation', 'n8n', 'python', 'operations', 'administration',
    'coordinator', 'associate', 'entry level'
]

# Keywords to EXCLUDE (job must NOT have any of these)
EXCLUDE_KEYWORDS = [
    'customer service', 'sales',
    'senior', 'lead', 'director', 'manager', 'principal'
]

# Requirements (RemoteOK is remote-only by default)
MUST_BE_REMOTE = False

# File to track jobs already sent (prevents duplicates)
SENT_JOBS_FILE = 'sent_jobs.json'

# ============================================================================
# TIME-BASED FILTERING
# ============================================================================

def is_job_fresh(job, hours=JOB_FRESHNESS_HOURS):
    """
    Check if a job was posted within the specified time window
    This prevents sending old jobs as "new" notifications
    """
    try:
        # RemoteOK uses epoch timestamp
        job_epoch = job.get('epoch', 0)
        if job_epoch == 0:
            print(f"⚠️ Job {job.get('id', 'unknown')} has no timestamp, skipping")
            return False
            
        job_time = datetime.fromtimestamp(job_epoch)
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        is_fresh = job_time >= cutoff_time
        
        if not is_fresh:
            hours_old = (datetime.now() - job_time).total_seconds() / 3600
            print(f"⏰ Skipping old job: {job.get('position', 'Unknown')} ({hours_old:.1f}h old)")
            
        return is_fresh
        
    except Exception as e:
        print(f"❌ Error checking job timestamp: {e}")
        # If we can't determine age, assume it's fresh to avoid missing jobs
        return True

# ============================================================================
# DUPLICATE TRACKING WITH CLEANUP
# ============================================================================

def load_sent_jobs():
    """Load the list of job IDs we've already sent to Discord"""
    if os.path.exists(SENT_JOBS_FILE):
        try:
            with open(SENT_JOBS_FILE, 'r') as f:
                data = json.load(f)
                # Handle both old format (list) and new format (dict with timestamps)
                if isinstance(data, list):
                    return {'jobs': data, 'last_cleanup': 0}
                return data
        except Exception as e:
            print(f"⚠️ Error loading sent jobs file: {e}")
            return {'jobs': [], 'last_cleanup': 0}
    return {'jobs': [], 'last_cleanup': 0}

def save_sent_job(job_id):
    """Add a job ID to the sent list with timestamp tracking"""
    data = load_sent_jobs()
    if job_id not in data['jobs']:
        data['jobs'].append(job_id)
        
        # Clean up old entries weekly
        current_time = datetime.now().timestamp()
        if current_time - data.get('last_cleanup', 0) > 604800:  # 7 days
            # Keep only last 1000 job IDs
            data['jobs'] = data['jobs'][-1000:]
            data['last_cleanup'] = current_time
            print("🧹 Cleaned up old job tracking data")
        
        try:
            with open(SENT_JOBS_FILE, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"❌ Error saving sent jobs: {e}")

def is_already_sent(job_id):
    """Check if we've already sent this job"""
    data = load_sent_jobs()
    return job_id in data['jobs']

# ============================================================================
# JOB SCRAPING
# ============================================================================

def fetch_remoteok_jobs():
    """Fetch recent jobs from RemoteOK API with improved error handling"""
    url = "https://remoteok.com/api"
    
    try:
        # RemoteOK requires a user agent
        headers = {
            'User-Agent': 'Mozilla/5.0 (compatible; JobScraperBot/1.0)',
            'Accept': 'application/json'
        }
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        
        # First item is metadata, skip it
        data = response.json()
        if not isinstance(data, list) or len(data) == 0:
            print("❌ Invalid response format from RemoteOK")
            return []
            
        jobs = data[1:]  # Skip metadata
        
        print(f"✅ Fetched {len(jobs)} total jobs from RemoteOK")
        return jobs
        
    except requests.exceptions.Timeout:
        print("❌ Timeout fetching jobs from RemoteOK")
        return []
    except requests.exceptions.RequestException as e:
        print(f"❌ Network error fetching jobs: {e}")
        return []
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON response: {e}")
        return []
    except Exception as e:
        print(f"❌ Unexpected error fetching jobs: {e}")
        return []

# ============================================================================
# FILTERING LOGIC
# ============================================================================

def matches_criteria(job):
    """Check if a job matches your search criteria with improved matching"""
    
    # Get job details (case-insensitive search)
    title = job.get('position', '').lower()
    description = job.get('description', '').lower()
    tags = [tag.lower() for tag in job.get('tags', [])]
    company = job.get('company', '').lower()
    
    # Combine all text for keyword searching
    all_text = f"{title} {description} {' '.join(tags)} {company}"
    
    # Check: Must be remote (disabled since RemoteOK is remote-only)
    if MUST_BE_REMOTE and not job.get('remote', True):
        return False
    
    # Check: Must have at least one INCLUDE keyword
    has_include = any(keyword.lower() in all_text for keyword in INCLUDE_KEYWORDS)
    if not has_include:
        return False
    
    # Check: Must NOT have any EXCLUDE keywords
    has_exclude = any(keyword.lower() in all_text for keyword in EXCLUDE_KEYWORDS)
    if has_exclude:
        return False
    
    return True

# ============================================================================
# DISCORD NOTIFICATION
# ============================================================================

def send_to_discord(job):
    """Send a job posting to Discord as a rich embed with better formatting"""
    
    if not WEBHOOK_URL:
        print("❌ No Discord webhook URL configured")
        return False
    
    # Extract job details with better defaults
    title = job.get('position', 'Unknown Position')
    company = job.get('company', 'Unknown Company')
    location = job.get('location', 'Remote')
    job_id = job.get('id', '')
    url = f"https://remoteok.com/remote-jobs/{job_id}" if job_id else "https://remoteok.com"
    tags = job.get('tags', [])[:6]  # First 6 tags only
    salary = job.get('salary_range') or job.get('salary_min') or 'Not specified'
    
    # Format job age
    try:
        job_time = datetime.fromtimestamp(job.get('epoch', 0))
        time_ago = datetime.now() - job_time
        if time_ago.total_seconds() < 3600:
            age_text = f"{int(time_ago.total_seconds() / 60)}m ago"
        else:
            age_text = f"{int(time_ago.total_seconds() / 3600)}h ago"
    except:
        age_text = "Recently posted"
    
    # Create Discord embed with enhanced formatting
    embed = {
        "title": f"💼 {title}",
        "url": url,
        "color": 0x00FF9F,  # Cyan/green
        "description": f"🕒 {age_text}",
        "fields": [
            {
                "name": "🏢 Company",
                "value": company,
                "inline": True
            },
            {
                "name": "📍 Location", 
                "value": location,
                "inline": True
            },
            {
                "name": "💰 Salary",
                "value": str(salary),
                "inline": True
            }
        ],
        "footer": {
            "text": f"RemoteOK • Job ID: {job_id}"
        },
        "timestamp": datetime.now().isoformat()
    }
    
    # Add tags field if we have tags
    if tags:
        embed["fields"].append({
            "name": "🏷️ Tags",
            "value": ", ".join(tags),
            "inline": False
        })
    
    payload = {
        "embeds": [embed]
    }
    
    try:
        response = requests.post(WEBHOOK_URL, json=payload, timeout=10)
        response.raise_for_status()
        print(f"✅ Sent to Discord: {title} at {company} ({age_text})")
        return True
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Error sending to Discord: {e}")
        return False

# ============================================================================
# MAIN SCRIPT
# ============================================================================

def main():
    """Main function - scrape, filter, and send jobs with improved logic"""
    
    print("\n" + "="*60)
    print("🔍 Job Scraper Starting...")
    print(f"⏰ Looking for jobs posted in the last {JOB_FRESHNESS_HOURS} hours")
    print("="*60 + "\n")
    
    # Validate configuration
    if not WEBHOOK_URL:
        print("❌ JOB_WEBHOOK_URL environment variable not set!")
        return
    
    # Fetch jobs from RemoteOK
    jobs = fetch_remoteok_jobs()
    
    if not jobs:
        print("❌ No jobs fetched. Exiting.")
        return
    
    # Statistics tracking
    stats = {
        'total_fetched': len(jobs),
        'fresh_jobs': 0,
        'already_sent': 0,
        'criteria_matched': 0,
        'successfully_sent': 0,
        'send_failed': 0
    }
    
    # Filter and send matching jobs
    for job in jobs:
        job_id = job.get('id')
        job_title = job.get('position', 'Unknown')
        
        # FIRST: Check if job is fresh (within time window)
        if not is_job_fresh(job, JOB_FRESHNESS_HOURS):
            continue
        stats['fresh_jobs'] += 1
        
        # SECOND: Skip if we've already sent this job
        if is_already_sent(job_id):
            stats['already_sent'] += 1
            continue
        
        # THIRD: Check if job matches your criteria
        if not matches_criteria(job):
            continue
        stats['criteria_matched'] += 1
        
        # FOURTH: Send to Discord
        print(f"📤 Processing: {job_title}")
        if send_to_discord(job):
            save_sent_job(job_id)
            stats['successfully_sent'] += 1
        else:
            stats['send_failed'] += 1
        
        # Rate limiting - stop after sending 5 jobs per run
        if stats['successfully_sent'] >= 5:
            print(f"\n⚠️ Reached {stats['successfully_sent']} jobs limit for this run")
            break
    
    # Print comprehensive statistics
    print(f"\n📊 Run Statistics:")
    print(f"   • Total jobs fetched: {stats['total_fetched']}")
    print(f"   • Fresh jobs (last {JOB_FRESHNESS_HOURS}h): {stats['fresh_jobs']}")
    print(f"   • Already sent (skipped): {stats['already_sent']}")
    print(f"   • Matched criteria: {stats['criteria_matched']}")
    print(f"   • Successfully sent: {stats['successfully_sent']}")
    if stats['send_failed'] > 0:
        print(f"   • Failed to send: {stats['send_failed']}")
    
    print(f"\n✅ Complete! Sent {stats['successfully_sent']} new job(s) to Discord")
    print("="*60 + "\n")

if __name__ == '__main__':
    main()
