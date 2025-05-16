from flask import Flask, request, jsonify
import pandas as pd
import datetime
import requests
import os
import json
from dateutil import parser
import pytz

app = Flask(__name__)

# Telegram setup
TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]

def send_telegram_alert(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": message}
    try:
        requests.post(url, data=data)
    except Exception as e:
        print(f"Telegram Error: {e}")

# Load levels
LEVELS = pd.read_csv("levels.csv")["price"].tolist()

@app.route("/", methods=["GET"])
def index():
    return "Webhook server is running!"

@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        # Read raw body
        raw_data = request.data.decode("utf-8")
#        print("🔍 Headers:", dict(request.headers))
#        print("📦 Raw webhook data:", raw_data)
        
        # Parse manually
        data = json.loads(raw_data)
#        print("📩 Parsed JSON:", data)

        open_price = float(data.get("open"))
        close_price = float(data.get("close"))
        candle_time = parser.isoparse(data["time"])
        
        # Convert to Romania time
        bucharest_tz = pytz.timezone("Europe/Bucharest")
        candle_time_bucharest = candle_time.astimezone(bucharest_tz)
        
        # Only allow Mon–Fri, 07:00–19:00
        if not (0 <= candle_time_bucharest.weekday() <= 4 and 7 <= candle_time_bucharest.hour < 19):
            print("⏳ Ignored — Outside allowed time window.")
            return jsonify({"status": "ignored", "reason": "outside active hours"})
        
        if close_price <= open_price:
            return jsonify({"status": "ignored", "reason": "not bullish"})

        body_size = abs(close_price - open_price)
        triggered_levels = []

        for level in LEVELS:
            if open_price <= level < close_price:
                portion_above = close_price - level
                if portion_above >= 0.5 * body_size:
                    triggered_levels.append(level)

        if triggered_levels:
            msg = f"🔔 {candle_time_bucharest} — Bullish candle triggered above: {triggered_levels}"
            print(msg)
            send_telegram_alert(msg)
            return jsonify({"status": "alert", "level": triggered_levels[0]})
        else:
            return jsonify({"status": "no match"})

    except Exception as e:
        print(f"❌ Failed to process webhook: {e}")
        return jsonify({"error": "bad request", "detail": str(e)}), 400

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))  # default to 5000 locally
    app.run(host="0.0.0.0", port=port)

#just to run locally    
#if __name__ == "__main__":
#    app.run(host="0.0.0.0", port=10000, debug=True)