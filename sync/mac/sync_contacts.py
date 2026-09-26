import argparse
import json
import os
import hashlib
import urllib.request
import urllib.error
import subprocess

STATE_FILE = os.path.expanduser("~/.crm_sync_state.json")

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
                print("Error from API:", data.get("error"))
                return []
    except Exception as e:
        print("Failed to fetch leads:", e)
        return []

def hash_contact(lead):
    # Hash name, phone, company, industry, status
    data = f"{lead.get('name')}|{lead.get('phone')}|{lead.get('company')}|{lead.get('industry')}|{lead.get('status')}"
    return hashlib.md5(data.encode('utf-8')).hexdigest()

def update_mac_contact(lead):
    name = f"CRM - {lead.get('name', 'Unknown')}"
    phone = lead.get('phone', '')
    if not phone: return False
    company = lead.get('company', '') or ''
    note = f"Industry: {lead.get('industry', 'N/A')} | Status: {lead.get('status', 'N/A')}"
    
    script = f'''
    tell application "Contacts"
        set existing_persons to every person whose name is "{name}"
        if (count of existing_persons) > 0 then
            set thePerson to item 1 of existing_persons
            set organization of thePerson to "{company}"
            set note of thePerson to "{note}"
            delete phones of thePerson
            make new phone at end of phones of thePerson with properties {{label:"work", value:"{phone}"}}
            save
        else
            set thePerson to make new person with properties {{first name:"{name}", organization:"{company}", note:"{note}"}}
            make new phone at end of phones of thePerson with properties {{label:"work", value:"{phone}"}}
            save
        end if
    end tell
    '''
    try:
        subprocess.run(['osascript', '-e', script], check=True, capture_output=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error syncing {name}:", e.stderr.decode())
        return False

def main():
    parser = argparse.ArgumentParser(description="Sync CRM Contacts to Mac")
    parser.add_argument("--api-url", default="http://localhost:8788", help="CRM API URL")
    parser.add_argument("--token", required=True, help="Auth token")
    args = parser.parse_args()

    leads = get_leads(args.api_url, args.token)
    
    try:
        with open(STATE_FILE, "r") as f:
            state = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        state = {}

    new_count = 0
    updated_count = 0
    skipped_count = 0

    for lead in leads:
        lead_id = str(lead.get("id"))
        phone = lead.get("phone")
        if not phone:
            continue
            
        current_hash = hash_contact(lead)
        prev_hash = state.get(lead_id)

        if prev_hash == current_hash:
            skipped_count += 1
            continue

        success = update_mac_contact(lead)
        if success:
            if prev_hash:
                updated_count += 1
            else:
                new_count += 1
            state[lead_id] = current_hash

    with open(STATE_FILE, "w") as f:
        json.dump(state, f)

    print(f"Sync complete. New: {new_count}, Updated: {updated_count}, Skipped: {skipped_count}")

if __name__ == "__main__":
    main()
