import requests
import time
import json
import os
from datetime import datetime
from geopy.geocoders import Nominatim   


AFRO_API_KEY = ""
AFRO_SENDER_ID = ''



BOT_TOKEN = '7590641106:AAGhh9fzTDITL9M5z4PylzzRvPS9sVZGyhA'
API_URL = f'https://api.telegram.org/bot{BOT_TOKEN}'
JSON_FILE = 'messages.json'
STATE_FILE = 'user_states.json'

url = f"https://api.telegram.org/bot{BOT_TOKEN}/setMyCommands"


geolocator = Nominatim(user_agent="ssas-bot")


# Create files if not exist


for file in [JSON_FILE, STATE_FILE]:
    if not os.path.exists(file):
        with open(file, 'w') as f:
            json.dump({}, f) if file == STATE_FILE else json.dump([], f)

Commands = [
    {"command": "/start", "description": "Start the bot / ቦትን ጀምር"},
    {"command": "/about", "description": "About this bot / ስለምን ይህ ቦት"},
    {"command": "/contact", "description": "Contact us / እኛን ያግኙ"},
    {"command": "/cancel", "description": "Cancel current operation / አሁን ያቋርጡ"},
    {"command": "/feedback", "description": "Send feedback / እቅድ ያስተውሉ"},
]

# Fields expected in the delivery form
Data_Message = [
    {"field": "pickup", "label": "Enter pickup location: / መነሻ ቦታን ያስገቡ:"},
    {"field": "sender_phone", "label": "Enter sender's phone number: / የላኪውን ስልክ ቁጥር ያስገቡ:"},
    {"field": "dropoff", "label": "Enter drop-off location: / መድረሻ ቦታን ያስገቡ:"},
    {"field": "receiver_phone", "label": "Enter receiver's phone number: / የተቀባዩን ስልክ ቁጥር ያስገቡ:"},
    {"field": "location_marker", "label": "📍 Please share your location: / እባክዎ አካባቢዎን ያካፍሉ:"},
    {"field": "payment_from_sender_or_receiver", "label": "Who will pay for the delivery? / ክፍያው በማን ነው?"},
    {"field": "item_description", "label": "Enter item description: / የእቃውን መግለጫ ያስገቡ:"},
    {"field": "Quantity", "label": "Enter quantity: / ብዛትን ያስገቡ:"},
]



def get_updates(offset=None):
    return requests.get(f'{API_URL}/getUpdates', params={'timeout': 100, 'offset': offset}).json()


def send_message(chat_id, text, reply_markup=None):
    payload = {'chat_id': chat_id, 'text': text}
    if reply_markup:
        payload["reply_markup"] = json.dumps(reply_markup)
    requests.post(f'{API_URL}/sendMessage', data=payload)


def request_location(chat_id):
    keyboard = {
        "keyboard": [[{"text": "📍 Share Location", "request_location": True}]],
        "resize_keyboard": True,
        "one_time_keyboard": True
    }
    send_message(chat_id, "📍 Please share your location: / እባክዎ አካባቢዎን ያጋሩ: ", reply_markup=keyboard)

def request_payment_option(chat_id):
    keyboard = {
        "keyboard": [
            [{"text": "Sender / ላኪ"}],
            [{"text": "Receiver / ተቀባይ"}]
        ],
        "resize_keyboard": True,
        "one_time_keyboard": True
    }
    send_message(chat_id, "Who will pay for the delivery? / ከፋዩ ማን ነው?", reply_markup=keyboard)


def get_address_from_coordinates(lat, lon):
    try:
        url = "https://nominatim.openstreetmap.org/reverse"
        params = {'lat': lat, 'lon': lon, 'format': 'json', 'addressdetails': 1}
        headers = {'User-Agent': 'ToloDeliveryBot/1.0'}
        response = requests.get(url, params=params, headers=headers)
        data = response.json()
        address = data.get("address", {})
        return {
            "full_address": data.get("display_name", "Unknown location"),
            "city": address.get("city", address.get("town", "")),
            "postcode": address.get("postcode", ""),
            "country": address.get("country", "")
        }
    except Exception as e:
        print("Geocoding failed:", e)
        return {}
# Add this helper function to remove keyboards
def remove_keyboard(chat_id, text="Saved. / ተመዝግቧል."):
    keyboard = {"remove_keyboard": True}
    send_message(chat_id, text, reply_markup=keyboard)


def save_delivery(data):
    try:
        with open(JSON_FILE, 'r') as f:
            content = f.read().strip()
            deliveries = json.loads(content) if content else []
    except Exception:
        deliveries = []

    deliveries.append(data)
    with open(JSON_FILE, 'w') as f:
        json.dump(deliveries, f, indent=2)

def send_sms(phone_number, message_text):
    url = "https://api.afromessage.com/api/send"  
    headers = {
        "Authorization": f"Bearer {AFRO_API_KEY}",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    payload = {
        "from": AFRO_SENDER_ID,
        "to": phone_number,
        "text": message_text
    }

    try:
        response = requests.post(url, headers=headers, data=payload)
        response.raise_for_status()
        print("SMS sent successfully")
    except requests.exceptions.RequestException as e:
        print("SMS failed:", e)


def load_states():
    with open(STATE_FILE, 'r') as f:
        return json.load(f)


def save_states(states):
    with open(STATE_FILE, 'w') as f:
        json.dump(states, f)


def main():
    last_update_id = None
    print("🚀 Bot is running...")

    while True:
        updates = get_updates(offset=last_update_id)
        states = load_states()

        for result in updates.get("result", []):
            update_id = result["update_id"]
            message = result.get("message")
            if not message:
                continue

            chat_id = str(message["chat"]["id"])

            if "location" in message and chat_id in states:
                lat = message["location"]["latitude"]
                lon = message["location"]["longitude"]
                states[chat_id]["data"].update({"latitude": lat, "longitude": lon})
                states[chat_id]["data"].update(get_address_from_coordinates(lat, lon))
                states[chat_id]["step"] += 1
                save_states(states)
                remove_keyboard(chat_id)
                request_payment_option(chat_id)
                continue  # ✅ No update to last_update_id here

            if "text" not in message:
                continue

            text = message["text"].strip()

            if text.lower() == "/start":
                states[chat_id] = {"step": 0, "data": {}}
                save_states(states)
                send_message(chat_id, "👋 Selam! Welcome to Tolo Delivery.\nሰላም! ወደ ቶሎ ዴሊቨሪ እንኳን በደህና መጡ።\nLet's begin / እንጀምር።")
                send_message(chat_id, Data_Message[0]['label'])

            elif chat_id in states:
                state = states[chat_id]
                step = state["step"]
                field_info = Data_Message[step]
                field = field_info["field"]

                if field in ["sender_phone", "receiver_phone"]:
                    if not ((text.startswith("09") and len(text) == 10 and text.isdigit()) or
                            (text.startswith("+2519") and len(text) == 13 and text[1:].isdigit())):
                        send_message(chat_id, "⚠️ Invalid Ethiopian phone number. Example: 0912345678 or +251912345678 / እባክዎ ትክክል የኢትዮጵያ ስልክ ቁጥር ያስገቡ።")
                        continue

                if field == "Quantity":
                    if not text.isdigit() or int(text) <= 0:
                        send_message(chat_id, "⚠️ Please enter a valid quantity (positive number). / እባክዎ ትክክል ቁጥር ያስገቡ።")
                        continue

                valid_inputs = ["Sender / ላኪ", "Receiver / ተቀባይ"]
                if field == "payment_from_sender_or_receiver" and text not in valid_inputs:
                    request_payment_option(chat_id)
                    #send_message(chat_id, "⚠️ Please choose from the buttons below.")
                    continue
             
                
                state["data"][field] = text

                if step == 0:
                    user = message["from"]
                    full_name = f"{user.get('first_name', '')} {user.get('last_name', '')}".strip()
                    state["data"]["user_name"] = full_name

                if step + 1 < len(Data_Message):
                    next_field_info = Data_Message[step + 1]
                    state["step"] += 1
                    save_states(states)

                    if next_field_info["field"] == "location_marker":
                        request_location(chat_id)
                    elif next_field_info["field"] == "payment_from_sender_or_receiver":
                        request_payment_option(chat_id)
                    else:
                        remove_keyboard(chat_id)
                        send_message(chat_id, next_field_info["label"])
                else:
                    state["data"]["timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    save_delivery(state["data"])
                    del states[chat_id]
                    save_states(states)
                    send_message(chat_id, "✅ Delivery saved. Thank you! / እቅድዎ በስኬት ተመዝግቧል። ")

                    if "receiver_phone" in state["data"]:
                        sms_text = f"Tolo Delivery: From {state['data'].get('pickup')} to {state['data'].get('dropoff')}."
                        if send_sms(state["data"]["receiver_phone"], sms_text):
                            send_message(chat_id, "📲 SMS sent to receiver. / ማስረጃ ተላክ።")
                        else:
                            send_message(chat_id, "⚠️ SMS failed to send. / ማስረጃ አልተላከም።")
                    response = requests.post(url, json={"commands": Commands})
                    print(f"Commands set response: {response.status_code} - {response.text}")
            else:
                send_message(chat_id, "Type /start to begin. / እባክዎ /start ይጻፉ ለመጀመር።")
            
        # ✅ Update offset here ONLY ONCE after all processing
        if updates.get("result"):
            last_update_id = updates["result"][-1]["update_id"] + 1

        time.sleep(1)
        
if __name__ == '__main__':
    main()
