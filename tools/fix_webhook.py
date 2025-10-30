
import os, requests, json

BOT = os.environ["TELEGRAM_BOT_TOKEN"]
BASE = f"https://api.telegram.org/bot{BOT}"
REPL = "https://content-maestro-connorrohan01.replit.app"  # 🔧 change if your Repl URL is different

print("🔍 Checking current webhook...")
info = requests.get(f"{BASE}/getWebhookInfo").json()
print(json.dumps(info, indent=2))

expected = f"{REPL}/api/v1/telegram/{BOT}"
print(f"\n✅ Expected webhook URL:\n{expected}")

if info.get("result", {}).get("url") != expected:
    print("\n⚙️ Resetting webhook to correct URL...")
    requests.get(f"{BASE}/deleteWebhook")
    res = requests.get(f"{BASE}/setWebhook", params={"url": expected})
    print("SetWebhook →", res.json())

print("\n🌐 Verifying webhook status...")
verify = requests.get(f"{BASE}/getWebhookInfo").json()
print(json.dumps(verify, indent=2))

print("\n🩺 Testing endpoint directly...")
r = requests.get(expected)
print("GET status:", r.status_code, "(405 ✅ good, 404 ❌ bad)")

payload = {
    "update_id": 1,
    "message": {
        "message_id": 1,
        "chat": {"id": int(os.environ.get("TELEGRAM_CHAT_ID", "7484907544"))},
        "text": "/ping"
    }
}
r = requests.post(expected, json=payload)
print("POST test →", r.status_code, r.text)

print("\n🎯 Done. Now send /ping in Telegram.")

