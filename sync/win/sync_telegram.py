import argparse
import time
import json
import urllib.request
import urllib.error
import urllib.parse

class TelegramCRM:
    def __init__(self, api_url, token, bot_token):
        self.api_url = api_url.rstrip('/')
        self.token = token
        self.bot_token = bot_token
        self.tg_url = f"https://api.telegram.org/bot{self.bot_token}"
        self.offset = 0

    def crm_request(self, method, endpoint, data=None):
        url = f"{self.api_url}{endpoint}"
        headers = {"Authorization": f"Bearer {self.token}"}
        if data:
            data = json.dumps(data).encode('utf-8')
            headers["Content-Type"] = "application/json"
        
        req = urllib.request.Request(url, data=data, method=method, headers=headers)
        try:
            with urllib.request.urlopen(req) as response:
                return json.loads(response.read().decode())
        except Exception as e:
            print(f"CRM API Error ({endpoint}):", e)
            return None

    def tg_request(self, method, **kwargs):
        url = f"{self.tg_url}/{method}"
        data = urllib.parse.urlencode(kwargs).encode('utf-8')
        try:
            req = urllib.request.Request(url, data=data)
            with urllib.request.urlopen(req) as response:
                return json.loads(response.read().decode())
        except Exception as e:
            print("Telegram API Error:", e)
            return None

    def send_message(self, chat_id, text):
        self.tg_request("sendMessage", chat_id=chat_id, text=text, parse_mode="HTML")

    def handle_update(self, update):
        message = update.get("message")
        if not message:
            return
        
        chat_id = message["chat"]["id"]
        text = message.get("text", "").strip()
        
        if not text.startswith("/"):
            return
            
        parts = text.split(" ", 1)
        cmd = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""

        if cmd == "/leads":
            res = self.crm_request("GET", "/api/leads?limit=5")
            if res and res.get("success"):
                items = res["data"].get("items", [])
                if not items:
                    self.send_message(chat_id, "No leads found.")
                else:
                    msg = "<b>Recent Leads:</b>\n"
                    for item in items:
                        msg += f"ID: {item['id']} | {item['name']} | {item.get('phone', '')} | {item.get('status', '')}\n"
                    self.send_message(chat_id, msg)
            else:
                self.send_message(chat_id, "Failed to fetch leads.")

        elif cmd == "/add":
            # Format: Name, Phone, Industry
            splits = [x.strip() for x in args.split(",")]
            if len(splits) >= 2:
                data = {
                    "name": splits[0],
                    "phone": splits[1],
                    "industry": splits[2] if len(splits) > 2 else ""
                }
                res = self.crm_request("POST", "/api/leads", data)
                if res and res.get("success"):
                    self.send_message(chat_id, f"Lead added successfully! ID: {res['data']['id']}")
                else:
                    self.send_message(chat_id, "Failed to add lead.")
            else:
                self.send_message(chat_id, "Usage: /add Name, Phone, Industry")

        elif cmd == "/note":
            # Format: [lead_id] Content
            splits = args.split(" ", 1)
            if len(splits) == 2 and splits[0].isdigit():
                data = {
                    "lead_id": int(splits[0]),
                    "type": "note",
                    "content": splits[1]
                }
                res = self.crm_request("POST", "/api/interactions", data)
                if res and res.get("success"):
                    self.send_message(chat_id, "Note added successfully!")
                else:
                    self.send_message(chat_id, "Failed to add note.")
            else:
                self.send_message(chat_id, "Usage: /note [lead_id] Content")

        elif cmd == "/search":
            res = self.crm_request("GET", f"/api/leads?search={urllib.parse.quote(args)}")
            if res and res.get("success"):
                items = res["data"].get("items", [])
                if not items:
                    self.send_message(chat_id, "No leads matched.")
                else:
                    msg = f"<b>Search Results for '{args}':</b>\n"
                    for item in items[:5]:
                        msg += f"ID: {item['id']} | {item['name']} | {item.get('phone', '')} | {item.get('status', '')}\n"
                    self.send_message(chat_id, msg)
            else:
                self.send_message(chat_id, "Search failed.")

        elif cmd == "/status":
            splits = args.split(" ", 1)
            if len(splits) == 2 and splits[0].isdigit():
                data = {"status": splits[1]}
                res = self.crm_request("PUT", f"/api/leads/{splits[0]}", data)
                if res and res.get("success"):
                    self.send_message(chat_id, "Status updated successfully!")
                else:
                    self.send_message(chat_id, "Failed to update status.")
            else:
                self.send_message(chat_id, "Usage: /status [lead_id] [new_status]")
        else:
            self.send_message(chat_id, "Unknown command. Available: /leads, /add, /note, /search, /status")

    def run(self):
        print("Telegram bot listening...")
        while True:
            updates = self.tg_request("getUpdates", offset=self.offset, timeout=30)
            if updates and updates.get("ok"):
                for update in updates["result"]:
                    self.offset = update["update_id"] + 1
                    try:
                        self.handle_update(update)
                    except Exception as e:
                        print("Error handling update:", e)
            time.sleep(1)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-url", default="http://localhost:8788")
    parser.add_argument("--token", required=True)
    parser.add_argument("--bot-token", required=True)
    args = parser.parse_args()

    bot = TelegramCRM(args.api_url, args.token, args.bot_token)
    bot.run()

if __name__ == "__main__":
    main()
