import asyncio
import requests
import re
import os
import pycountry
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# --- FIXED CREDENTIALS SECTION ---
# Heroku Config Vars se uthayega, warna default values use karengi
BOT_TOKEN = os.getenv("BOT_TOKEN", "8699579904:AAHDf2JMuWomgwpVyvx5ulkaus3qSVwZw9A")

# Group ID ko integer mein convert karna zaroori hai
raw_id = os.getenv("GROUP_ID", "-1003975483115")
try:
    GROUP_ID = int(raw_id)
except (ValueError, TypeError):
    GROUP_ID = -1003975483115

# Internal API URL
API_URL = "http://51.75.118.75:20267/api/np2?type=sms"

# Initialize Bot
bot = Bot(token=BOT_TOKEN)
last_timestamp = None

def fetch_new_otps(since_timestamp=None):
    """Fetch all OTP records newer than since_timestamp."""
    try:
        response = requests.get(API_URL, timeout=10)
        data = response.json()
        records = data.get("aaData", [])
        valid = [r for r in records if isinstance(r[0], str) and ":" in r[0]]
        
        if not valid:
            return []

        if since_timestamp is None:
            latest = valid[0]
            return [{
                "time": latest[0],
                "country": latest[1],
                "number": latest[2],
                "service": latest[3],
                "message": latest[4],
            }]

        new_records = []
        for r in valid:
            try:
                rec_time = datetime.strptime(r[0], "%Y-%m-%d %H:%M:%S")
                if rec_time > since_timestamp:
                    new_records.append({
                        "time": r[0],
                        "country": r[1],
                        "number": r[2],
                        "service": r[3],
                        "message": r[4],
                    })
            except ValueError:
                continue

        new_records.reverse()
        return new_records
    except Exception as e:
        print(f"Error fetching OTP: {e}")
        return []

def extract_otp(message):
    match = re.search(r'\d{3}-\d{3}', message)
    if match: return match.group(0)
    match = re.search(r'\d{6}', message)
    if match: return match.group(0)
    match = re.search(r'\d{4}', message)
    if match: return match.group(0)
    return "N/A"

def mask_number(number_str):
    try:
        number_str = f"+{number_str}"
        length = len(number_str)
        show_first = 5 if length >= 10 else 4
        show_last = 4 if length >= 10 else 2
        stars_count = length - show_first - show_last
        if stars_count <= 0: return number_str
        return f"{number_str[:show_first]}{'*' * stars_count}{number_str[-show_last:]}"
    except:
        return f"+{number_str}"

def get_country_info(country_string):
    try:
        country_name = country_string.split('-')[0].strip()
        country_data = pycountry.countries.search_fuzzy(country_name)
        if country_data:
            country_code = country_data[0].alpha_2
            regional_base = 0x1F1E6 - ord('A')
            flag = chr(regional_base + ord(country_code[0])) + chr(regional_base + ord(country_code[1]))
            return country_name, flag
    except:
        pass
    return country_string, "🌍"

def format_message(record):
    raw_message = record["message"]
    otp_code = extract_otp(raw_message)
    msg = raw_message.replace("<", "&lt;").replace(">", "&gt;")
    country_name, flag = get_country_info(record['country'])
    formatted_number = mask_number(record['number'])

    service_emoji = "📱"
    s_lower = record['service'].lower()
    if 'whatsapp' in s_lower: service_emoji = "🟢"
    elif 'telegram' in s_lower: service_emoji = "🔵"
    elif 'facebook' in s_lower: service_emoji = "📘"

    return f"""
<b>{flag} New {country_name} {record['service']} OTP!</b>

<blockquote>🕰 Time: {record['time']}</blockquote>
<blockquote>{flag} Country: {country_name}</blockquote>
<blockquote>{service_emoji} Service: {record['service']}</blockquote>
<blockquote>📞 Number: {formatted_number}</blockquote>
<blockquote>🔑 OTP: Code <code>{otp_code}</code></blockquote>

<blockquote>📩 Full-Message:</blockquote>
<pre>{msg}</pre>

Powered By LEADER SHAH 
"""

async def send_otp_message(record):
    try:
        message = format_message(record)
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton("📢 Channel", url="https://t.me/leaderotpgroup"),
             InlineKeyboardButton("🔢 Numbers", url="https://t.me/newbackupchanel")],
            [InlineKeyboardButton("👨‍💻 Developer", url="https://t.me/SHAHLEADER12"),
             InlineKeyboardButton("🟢 WhatsApp", url="https://whatsapp.com/channel/0029VbC0Gcs0G0XZqgIYFL01")]
        ])
        await bot.send_message(chat_id=GROUP_ID, text=message, parse_mode="HTML", reply_markup=keyboard)
        print(f"[{datetime.now()}] Sent OTP from {record['number']}")
    except Exception as e:
        print(f"Telegram send error: {e}")

async def main():
    global last_timestamp
    print("Bot started...")
    print(f"Using Group ID: {GROUP_ID}") # Ab yeh error nahi dega
    
    # First run
    otps = fetch_new_otps(since_timestamp=None)
    if otps:
        otp = otps[0]
        await send_otp_message(otp)
        last_timestamp = datetime.strptime(otp["time"], "%Y-%m-%d %H:%M:%S")

    while True:
        try:
            new_otps = fetch_new_otps(since_timestamp=last_timestamp)
            for otp in new_otps:
                await send_otp_message(otp)
                otp_time = datetime.strptime(otp["time"], "%Y-%m-%d %H:%M:%S")
                if last_timestamp is None or otp_time > last_timestamp:
                    last_timestamp = otp_time
        except Exception as e:
            print(f"Error in main loop: {e}")
        await asyncio.sleep(5)

if __name__ == "__main__":
    asyncio.run(main())
