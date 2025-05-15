from flask import Flask, request, jsonify
import pandas as pd
import datetime
import requests
import os

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

@app.route("/")
def index():
    return "Webhook server is running!"

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()
    try:
        open_price = float(data.get("open"))
        close_price = float(data.get("close"))
        candle_time = datetime.datetime.fromtimestamp(int(data.get("time")) / 1000)
    except Exception as e:
        return jsonify({"error": "Invalid payload", "detail": str(e)}), 400

    if close_price <= open_price:
        return jsonify({"status": "ignored", "reason": "not bullish"})

    body_size = abs(close_price - open_price)
    triggered_levels = []

    for level in LEVELS:
        if open_price > level and (open_price - level) >= 0.5 * body_size:
            triggered_levels.append(level)

    if triggered_levels:
        msg = f"🔔 {candle_time} — Bullish candle triggered above: {triggered_levels}"
        print(msg)
        send_telegram_alert(msg)
        return jsonify({"status": "alert", "levels": triggered_levels})
    else:
        return jsonify({"status": "no match"})