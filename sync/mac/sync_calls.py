import argparse
import sqlite3
import os
import json
import urllib.request
import urllib.error
from datetime import datetime, timedelta

# Call history DB path
CALL_DB = os.path.expanduser("~/Library/Application Support/CallHistoryDB/CallHistory.storedata")
STATE_FILE = os.path.expanduser("~/.crm_call_sync_state.json")

def get_leads(api_url, token):
    url = f"{api_url.rstrip('/')}/api/leads?limit=1000"
    req = urllib.request.Request(url)
    req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())
            if data.get("success"):
                return data.get("data", {}).get("items", [])
            else:
                return []
    except Exception:
        return []

def post_interaction(api_url, token, interaction):
    url = f"{api_url.rstrip('/')}/api/interactions"
    data = json.dumps(interaction).encode('utf-8')
    req = urllib.request.Request(url, data=data, method='POST')
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req) as response:
            return response.status in (200, 201)
    except Exception as e:
        print("Failed to post interaction:", e)
        return False

def format_phone(phone):
    return ''.join(filter(str.isdigit, str(phone)))

def main():
    parser = argparse.ArgumentParser(description="Sync Mac Calls to CRM")
    parser.add_argument("--api-url", default="http://localhost:8788", help="CRM API URL")
    parser.add_argument("--token", required=True, help="Auth token")
    args = parser.parse_args()

    # Load state
    try:
        with open(STATE_FILE, "r") as f:
            state = json.load(f)
            last_sync = state.get("last_sync", 0)
    except (FileNotFoundError, json.JSONDecodeError):
        last_sync = (datetime.now() - timedelta(hours=48)).timestamp()

    # Fetch leads and map phones
    leads = get_leads(args.api_url, args.token)
    phone_to_lead = {}
    for lead in leads:
        if lead.get("phone"):
            p = format_phone(lead["phone"])
            if p: phone_to_lead[p] = lead["id"]

    if not os.path.exists(CALL_DB):
        print("Call history DB not found at", CALL_DB)
        return

    # Read calls
    try:
        conn = sqlite3.connect(CALL_DB)
        cursor = conn.cursor()
        # Mac timestamp is CoreData timestamp (seconds since 2001-01-01)
        mac_epoch = datetime(2001, 1, 1).timestamp()
        target_time = last_sync - mac_epoch
        
        cursor.execute("""
            SELECT ZADDRESS, ZDATE, ZDURATION, ZORIGINATED
            FROM ZCALLRECORD
            WHERE ZDATE > ?
            ORDER BY ZDATE ASC
        """, (target_time,))
        
        calls = cursor.fetchall()
        conn.close()
    except Exception as e:
        print("Failed to read call history:", e)
        return

    synced_count = 0
    max_timestamp = last_sync

    for call in calls:
        address, zdate, duration, originated = call
        if not address: continue
        
        call_time = mac_epoch + zdate
        if call_time > max_timestamp:
            max_timestamp = call_time

        f_phone = format_phone(address)
        if f_phone in phone_to_lead:
            lead_id = phone_to_lead[f_phone]
            direction = "outbound" if originated == 1 else "inbound"
            dt = datetime.fromtimestamp(call_time).isoformat()
            
            interaction = {
                "lead_id": lead_id,
                "type": "call",
                "direction": direction,
                "duration": int(duration) if duration else 0,
                "content": f"Phone call on {dt}",
                "metadata": {"source": "mac_call_history"}
            }
            if post_interaction(args.api_url, args.token, interaction):
                synced_count += 1

    # Save state
    with open(STATE_FILE, "w") as f:
        json.dump({"last_sync": max_timestamp}, f)

    print(f"Call sync complete. Synced {synced_count} matched calls.")

if __name__ == "__main__":
    main()
