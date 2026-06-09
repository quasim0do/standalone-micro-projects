import os
import json
import requests
from datetime import datetime
from dotenv import load_dotenv
from shared.logger import log

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
CACHE_FILE = os.path.join(BASE_DIR, "outlook_cache.json")

load_dotenv(os.path.join(BASE_DIR, ".env"))


def is_m365_configured():
    return all([
        os.getenv("M365_CLIENT_ID"),
        os.getenv("M365_TENANT_ID"),
        os.getenv("M365_CLIENT_SECRET"),
    ])


def _get_access_token():
    try:
        import msal
    except ImportError:
        raise RuntimeError("msal not installed. Run: pip install msal")

    app = msal.ConfidentialClientApplication(
        os.getenv("M365_CLIENT_ID"),
        authority=f"https://login.microsoftonline.com/{os.getenv('M365_TENANT_ID')}",
        client_credential=os.getenv("M365_CLIENT_SECRET"),
    )
    result = app.acquire_token_for_client(scopes=["https://graph.microsoft.com/.default"])
    if "access_token" not in result:
        raise RuntimeError(f"M365 auth failed: {result.get('error_description', 'unknown')}")
    return result["access_token"]


def _load_cache():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE) as f:
            return json.load(f)
    return {"emails": [], "last_sync": None}


def _save_cache(data):
    with open(CACHE_FILE, "w") as f:
        json.dump(data, f, indent=2)


def get_flagged_emails():
    """Fetch flagged Outlook emails. Falls back to cache on failure (Pattern 3)."""
    cache = _load_cache()
    try:
        token = _get_access_token()
        url = (
            "https://graph.microsoft.com/v1.0/me/messages"
            "?$filter=flag/flagStatus eq 'flagged'"
            "&$select=id,subject,importance,bodyPreview,from,receivedDateTime"
        )
        resp = requests.get(url, headers={"Authorization": f"Bearer {token}"}, timeout=10)
        resp.raise_for_status()
        emails = resp.json().get("value", [])

        cache["emails"] = emails
        cache["last_sync"] = datetime.now().isoformat()
        _save_cache(cache)
        log.info(f"Outlook sync: {len(emails)} flagged emails")
        return emails, True
    except Exception as e:
        log.warning(f"Outlook API failed ({e}) — using cache")
        return cache.get("emails", []), False


def emails_to_tasks(emails, existing_source_ids):
    """Convert emails to task dicts, skipping already-imported (Pattern 6: dedup by source_id)."""
    tasks = []
    for email in emails:
        if email["id"] in existing_source_ids:
            continue
        tasks.append({
            "title": email.get("subject", "(no subject)"),
            "description": (
                f"From: {email.get('from', {}).get('emailAddress', {}).get('address', '')} — "
                f"{email.get('bodyPreview', '')[:100]}"
            ),
            "urgency": "high" if email.get("importance") == "high" else "medium",
            "importance": "medium",
            "source": "outlook",
            "source_id": email["id"],
            "deadline": None,
        })
    return tasks
