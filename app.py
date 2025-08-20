import requests
import folium
import time
from flask import Flask, render_template, jsonify
import threading
from datetime import datetime
import pytz
import os

# Supabase URL
BASE_URL = "https://erspvsdfwaqjtuhymubj.supabase.co"
REFRESH_URL = f"{BASE_URL}/auth/v1/token?grant_type=refresh_token"

# Store both access and refresh tokens
access_token = ""
refresh_token = ""

# Read tokens from file
try:
    with open("token.txt", "r") as file:
        tokens = file.read().strip().splitlines()
        access_token = tokens[0]
        # Check if refresh token exists in the file
        if len(tokens) > 1:
            refresh_token = tokens[1]
except Exception as e:
    print(f"Error reading tokens: {e}")

app = Flask(__name__)

# Create templates and static directories if they don't exist
os.makedirs('templates', exist_ok=True)
os.makedirs('static/css', exist_ok=True)
os.makedirs('static/js', exist_ok=True)

# Store latest data for each tracked ID
tracked_users = {
    "d095ceae-d20d-4c79-8910-72faad1a43b0": {"data": {}, "color": "blue"},
    "45b27735-2e40-4449-9759-99c8a857da4d": {"data": {}, "color": "purple"},
    "d29ee857-ac7a-4848-858d-cc55f7537edc": {"data": {}, "color": "green"},
    "193f651e-8ee6-47c6-a8ef-7d2afe4ad66b": {"data": {}, "color": "orange"},
    "96f9e5ab-646a-43eb-818d-903b9c4d3e2c": {"data": {}, "color": "pink"}
}

# Your location (default, will be updated by user's GPS)
my_location = {"coords": [33.8864, -84.4111], "color": "red", "label": "Me"}

# API key (constant)
API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVyc3B2c2Rmd2FxanR1aHltdWJqIiwicm9sZSI6ImFub24iLCJpYXQiOjE2ODM1ODY0MjcsImV4cCI6MTk5OTE2MjQyN30.2AItrHcB7A5bSZ_dfd455kvLL8fXLL7IrfMBoFmkGww"

# Create a session for persistent headers
session = requests.Session()
session.headers.update({
    "content-type": "application/json",
    "accept": "*/*",
    "authorization": f"Bearer {access_token}",
    "apikey": API_KEY,
    "user-agent": "Splashin/5 CFNetwork/3826.600.41 Darwin/24.6.0",
    "x-client-info": "supabase-js-react-native/2.52.1",
    "content-profile": "public",
})
session.verify = False  # Note: In production, you should use proper SSL verification


def refresh_tokens():
    """Get a new access token using the refresh token."""
    global access_token, refresh_token

    print("🔄 Attempting to refresh token...")
    if not refresh_token:
        print("⚠️ No refresh token available")
        return False

    try:
        payload = {"refresh_token": refresh_token}
        resp = requests.post(
            REFRESH_URL,
            headers={
                "Content-Type": "application/json",
                "apikey": API_KEY,
            },
            json=payload,
            verify=False
        )
        resp.raise_for_status()
        data = resp.json()

        # Update tokens
        access_token = data["access_token"]
        refresh_token = data["refresh_token"]

        # Update session header
        session.headers["authorization"] = f"Bearer {access_token}"

        # Save to token.txt for persistence
        with open("token.txt", "w") as f:
            f.write(access_token + "\n" + refresh_token)

        print("🔄 Token refreshed successfully")
        return True
    except requests.RequestException as e:
        print("⚠️ Failed to refresh token:", e)
        return False

def test_get_name(uid):
    """Test function to fetch just the name of a user"""
    data = get_location(uid)
    if not data:
        print(f"❌ No data returned for {uid}")
        return None
    
    print(data)
    name = data.get("fn", "Unknown")
    print(f"✅ Name for {uid}: {name}")
    return name


def make_request(target_id):
    URL = f"{BASE_URL}/rest/v1/rpc/location-request"

    payload = {
        "queue_name": "location-request",
        "uid": target_id
    }

    max_retries = 2
    for attempt in range(max_retries):
        try:
            response = session.post(URL, json=payload)

            # Handle authentication errors
            if response.status_code == 401:  # Unauthorized, token likely expired
                print("⚠️ Token expired, refreshing...")
                if refresh_tokens():
                    continue  # retry with new token
                else:
                    print("❌ Token refresh failed, aborting request")
                    return

            response.raise_for_status()

            print("Status:", response.status_code)
            if "application/json" in response.headers.get("content-type", ""):
                print(response.json())
            else:
                print("Response:", response.text)

            # Request successful, break the retry loop
            break

        except requests.exceptions.RequestException as e:
            print(f"Request failed (attempt {attempt + 1}/{max_retries}): {e}")
            if attempt + 1 < max_retries:
                time.sleep(1)  # Wait before retry
            else:
                print("❌ All request attempts failed")


def get_location(target_id):
    """Query Supabase for a user's location and extra info"""
    URL = f"{BASE_URL}/rest/v1/rpc/get_map_user_full_v2"

    payload = {"gid": "73b5a586-8093-4d49-8fed-41124615b3c4", "uid": target_id}

    max_retries = 2
    for attempt in range(max_retries):
        try:
            response = session.post(URL, json=payload)

            # Handle authentication errors
            if response.status_code == 401:  # Unauthorized, token likely expired
                print("⚠️ Token expired, refreshing...")
                if refresh_tokens():
                    continue  # retry with new token
                else:
                    print("❌ Token refresh failed, aborting request")
                    return {}

            response.raise_for_status()
            data = response.json()
            return data

        except Exception as e:
            print(f"Error fetching {target_id} (attempt {attempt + 1}/{max_retries}): {e}")
            if attempt + 1 < max_retries:
                time.sleep(1)  # Wait before retry
            else:
                print("❌ All location fetch attempts failed")
                return {}


def poll_locations(interval=10):
    """Background loop to refresh all users' locations and names"""
    global tracked_users
    while True:
        for uid in tracked_users.keys():
            make_request(uid)
            data = get_location(uid)
            if data and "l" in data and "lo" in data:
                tracked_users[uid]["data"] = data

                # Always update label from Supabase API
                tracked_users[uid]["label"] = data.get("n", "Unknown")

                print(f"Updated {uid}: {data['l']}, {data['lo']}, name: {tracked_users[uid]['label']}")
            else:
                print(f"No valid location data received for {uid}")
        time.sleep(interval)


@app.route("/")
def map_page():
    return render_template('index.html')


@app.route("/get_map_data")
def get_map_data():
    """API endpoint to get all tracked user data including your location"""
    user_data = []
    
    # Add your location (still red)
    user_data.append({
        "type": "me",
        "coords": my_location["coords"],
        "label": my_location["label"],
        "icon": "Me",  # Keep 'Me' as the marker text
        "color": my_location["color"]
    })
    
    # Add tracked users
    for uid, info in tracked_users.items():
        data = info["data"]
        if not data or not data.get("l") or not data.get("lo"):
            continue
        
        lat, lon = float(data["l"]), float(data["lo"])
        activity = data.get("a", "unknown")
        in_car = data.get("ic", "false")
        city = data.get("c", "")
        region = data.get("r", "")
        speed_ms = data.get("s", "0")
        
        # ✅ Combine fn + ln for the label
        full_name = f"{data.get('fn', '')} {data.get('ln', '')}".strip()
        if not full_name.strip():
            full_name = "Unknown"
        
        # ✅ Use initials (i field) instead of color
        initials = data.get("i", "?")
        
        # Convert speed from m/s to mph
        try:
            speed_ms = float(speed_ms)
            speed_mph = speed_ms * 2.23694
            speed_display = f"{speed_mph:.1f} mph"
        except (ValueError, TypeError):
            speed_display = "Unknown"
        
        updated_raw = data.get("up", "N/A")
        if updated_raw != "N/A":
            dt_utc = datetime.strptime(updated_raw, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=pytz.UTC)
            dt_est = dt_utc.astimezone(pytz.timezone("US/Eastern"))
            updated = dt_est.strftime("%I:%M %p %Z")
        else:
            updated = "N/A"
        
        user_data.append({
            "type": "tracked",
            "coords": [lat, lon],
            "label": full_name,   # ✅ Jack Munger
            "icon": initials,     # ✅ JM on map pin
            "activity": activity,
            "in_car": in_car,
            "city": city,
            "region": region,
            "speed": speed_display,
            "updated": updated
        })
        
    return jsonify(user_data)


@app.route("/update_my_location", methods=["POST"])
def update_my_location():
    """API endpoint to update your location from browser geolocation"""
    from flask import request
    data = request.json
    
    if data and "lat" in data and "lng" in data:
        my_location["coords"] = [data["lat"], data["lng"]]
        return jsonify({"status": "success"})
    return jsonify({"status": "error", "message": "Invalid location data"})


if __name__ == "__main__":
    print(f"Starting with access token: {access_token[:10]}...")
    # Start background polling
    t = threading.Thread(target=poll_locations, daemon=True)
    t.start()
    app.run(debug=True)