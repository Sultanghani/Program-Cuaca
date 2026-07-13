from flask import Flask, render_template, request, jsonify
import requests
import math
from datetime import datetime, timedelta
import random

app = Flask(__name__)

# Open-Meteo API - FREE, no API key needed!
GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
WEATHER_URL = "https://api.open-meteo.com/v1/forecast"

WMO_CODES = {
    0: ("Cerah", "☀️"),
    1: ("Sebagian Cerah", "🌤️"),
    2: ("Berawan Sebagian", "⛅"),
    3: ("Mendung", "☁️"),
    45: ("Berkabut", "🌫️"),
    48: ("Kabut Tebal", "🌫️"),
    51: ("Gerimis Ringan", "🌦️"),
    53: ("Gerimis Sedang", "🌦️"),
    55: ("Gerimis Lebat", "🌧️"),
    61: ("Hujan Ringan", "🌧️"),
    63: ("Hujan Sedang", "🌧️"),
    65: ("Hujan Lebat", "🌧️"),
    71: ("Salju Ringan", "🌨️"),
    73: ("Salju Sedang", "🌨️"),
    75: ("Salju Lebat", "❄️"),
    77: ("Butiran Salju", "❄️"),
    80: ("Hujan Lokal", "🌦️"),
    81: ("Hujan Lokal Sedang", "🌧️"),
    82: ("Hujan Lokal Lebat", "⛈️"),
    85: ("Hujan Salju", "🌨️"),
    86: ("Hujan Salju Lebat", "❄️"),
    95: ("Badai Petir", "⛈️"),
    96: ("Badai Petir + Hujan Es", "⛈️"),
    99: ("Badai Petir Lebat", "⛈️"),
}

def get_weather_description(code):
    return WMO_CODES.get(code, ("Tidak Diketahui", "🌡️"))

def get_uv_label(uv):
    if uv <= 2: return ("Rendah", "#4CAF50")
    elif uv <= 5: return ("Sedang", "#FFC107")
    elif uv <= 7: return ("Tinggi", "#FF9800")
    elif uv <= 10: return ("Sangat Tinggi", "#F44336")
    else: return ("Ekstrem", "#9C27B0")

def get_wind_direction(degrees):
    dirs = ["U", "BL", "T", "TG", "S", "BD", "B", "BT"]
    ix = round(degrees / 45) % 8
    return dirs[ix]

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/search")
def search_city():
    query = request.args.get("q", "").strip()
    if not query:
        return jsonify({"error": "Query kosong"}), 400
    
    try:
        resp = requests.get(GEOCODING_URL, params={
            "name": query,
            "count": 6,
            "language": "id",
            "format": "json"
        }, timeout=10)
        data = resp.json()
        
        results = []
        for r in data.get("results", []):
            results.append({
                "name": r.get("name"),
                "country": r.get("country", ""),
                "admin1": r.get("admin1", ""),
                "lat": r.get("latitude"),
                "lon": r.get("longitude"),
                "timezone": r.get("timezone", "Asia/Jakarta")
            })
        return jsonify(results)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/weather")
def get_weather():
    lat = request.args.get("lat")
    lon = request.args.get("lon")
    tz = request.args.get("timezone", "Asia/Jakarta")
    
    if not lat or not lon:
        return jsonify({"error": "Koordinat diperlukan"}), 400
    
    try:
        params = {
            "latitude": lat,
            "longitude": lon,
            "current": [
                "temperature_2m", "relative_humidity_2m", "apparent_temperature",
                "precipitation", "weather_code", "surface_pressure",
                "wind_speed_10m", "wind_direction_10m", "wind_gusts_10m",
                "uv_index", "visibility", "is_day"
            ],
            "hourly": [
                "temperature_2m", "precipitation_probability",
                "weather_code", "wind_speed_10m"
            ],
            "daily": [
                "weather_code", "temperature_2m_max", "temperature_2m_min",
                "precipitation_sum", "precipitation_probability_max",
                "wind_speed_10m_max", "sunrise", "sunset", "uv_index_max"
            ],
            "timezone": tz,
            "forecast_days": 7,
            "wind_speed_unit": "kmh"
        }
        
        resp = requests.get(WEATHER_URL, params=params, timeout=15)
        raw = resp.json()
        
        cur = raw.get("current", {})
        daily = raw.get("daily", {})
        hourly = raw.get("hourly", {})
        
        wcode = cur.get("weather_code", 0)
        desc, icon = get_weather_description(wcode)
        uv_val = cur.get("uv_index", 0)
        uv_label, uv_color = get_uv_label(uv_val)
        
        # Process hourly (next 24h)
        hourly_list = []
        now_hour = datetime.now().hour
        times = hourly.get("time", [])
        for i, t in enumerate(times[:48]):
            try:
                dt = datetime.fromisoformat(t)
                if dt >= datetime.now() - timedelta(hours=1):
                    hourly_list.append({
                        "time": dt.strftime("%H:%M"),
                        "date": dt.strftime("%d %b"),
                        "temp": round(hourly["temperature_2m"][i]),
                        "rain_prob": hourly["precipitation_probability"][i],
                        "code": hourly["weather_code"][i],
                        "icon": get_weather_description(hourly["weather_code"][i])[1],
                        "wind": round(hourly["wind_speed_10m"][i])
                    })
                    if len(hourly_list) >= 24:
                        break
            except:
                pass
        
        # Process daily
        daily_list = []
        day_names = ["Sen", "Sel", "Rab", "Kam", "Jum", "Sab", "Min"]
        for i in range(len(daily.get("time", []))):
            try:
                dt = datetime.fromisoformat(daily["time"][i])
                label = "Hari Ini" if i == 0 else ("Besok" if i == 1 else dt.strftime("%A")[:3])
                d, ic = get_weather_description(daily["weather_code"][i])
                daily_list.append({
                    "label": label,
                    "date": dt.strftime("%d %b"),
                    "desc": d,
                    "icon": ic,
                    "max": round(daily["temperature_2m_max"][i]),
                    "min": round(daily["temperature_2m_min"][i]),
                    "rain": daily["precipitation_sum"][i],
                    "rain_prob": daily["precipitation_probability_max"][i],
                    "wind_max": round(daily["wind_speed_10m_max"][i]),
                    "sunrise": daily["sunrise"][i].split("T")[1] if daily.get("sunrise") else "--",
                    "sunset": daily["sunset"][i].split("T")[1] if daily.get("sunset") else "--",
                    "uv": daily["uv_index_max"][i]
                })
            except:
                pass
        
        result = {
            "current": {
                "temp": round(cur.get("temperature_2m", 0)),
                "feels_like": round(cur.get("apparent_temperature", 0)),
                "humidity": cur.get("relative_humidity_2m", 0),
                "pressure": cur.get("surface_pressure", 0),
                "wind_speed": round(cur.get("wind_speed_10m", 0)),
                "wind_dir": get_wind_direction(cur.get("wind_direction_10m", 0)),
                "wind_deg": cur.get("wind_direction_10m", 0),
                "wind_gust": round(cur.get("wind_gusts_10m", 0)),
                "visibility": round(cur.get("visibility", 0) / 1000, 1),
                "precipitation": cur.get("precipitation", 0),
                "uv_index": uv_val,
                "uv_label": uv_label,
                "uv_color": uv_color,
                "description": desc,
                "icon": icon,
                "weather_code": wcode,
                "is_day": cur.get("is_day", 1)
            },
            "hourly": hourly_list,
            "daily": daily_list,
            "updated": datetime.now().strftime("%d %b %Y, %H:%M")
        }
        
        return jsonify(result)
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True, port=5000)
