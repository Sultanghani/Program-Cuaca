from flask import Flask, render_template, request, jsonify
import requests
import pandas as pd
import numpy as np
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
from datetime import datetime, timedelta
import os

app = Flask(__name__)

# BAGIAN 1: TRAINING MODEL DARI DATASET CSV

FEATURES = [
    "Suhu (Celsius)",
    "Kelembaban (%)",
    "Kecepatan Angin (km/jam)",
    "Tebal Awan (meter)",
    "Tekanan Atmosfer (hPa)"
]
LABEL = "Prakiraan Cuaca"
LABEL_ICON = {"Cerah": "☀️", "Berawan": "⛅", "Hujan": "🌧️"}

MODEL = None
MODEL_ACCURACY = 0
MODEL_CLASSES = []
DATASET_INFO = {}

def load_and_train():
    global MODEL, MODEL_ACCURACY, MODEL_CLASSES, DATASET_INFO

    csv_path = os.path.join(os.path.dirname(__file__), "prakiraan_cuaca_dummy.csv")
    if not os.path.exists(csv_path):
        print("[!] Dataset tidak ditemukan. ML tidak aktif.")
        return

    df = pd.read_csv(csv_path)
    total = len(df)
    df = df.dropna(subset=FEATURES + [LABEL])
    used = len(df)

    X = df[FEATURES]
    y = df[LABEL]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    clf = GradientBoostingClassifier(n_estimators=200, random_state=42)
    clf.fit(X_train, y_train)

    acc = accuracy_score(y_test, clf.predict(X_test))

    MODEL = clf
    MODEL_ACCURACY = round(acc * 100, 1)
    MODEL_CLASSES = list(clf.classes_)
    DATASET_INFO = {
        "total_baris": total,
        "baris_dipakai": used,
        "baris_dibuang": total - used,
        "distribusi_label": y.value_counts().to_dict(),
        "akurasi_test": MODEL_ACCURACY,
        "fitur": {
            col: {
                "min": round(float(df[col].min()), 1),
                "max": round(float(df[col].max()), 1),
                "rata_rata": round(float(df[col].mean()), 1)
            }
            for col in FEATURES
        }
    }
    print(f"[✓] Model siap — Akurasi: {MODEL_ACCURACY}% — Dataset: {used} baris")

# Jalankan training saat app pertama kali distart
load_and_train()


def predict(suhu, kelembaban, angin, tebal_awan, tekanan):
    """Prediksi label cuaca dari input numerik."""
    if MODEL is None:
        return None, None, {}

    input_df = pd.DataFrame(
        [[suhu, kelembaban, angin, tebal_awan, tekanan]],
        columns=FEATURES
    )
    pred = MODEL.predict(input_df)[0]
    proba = MODEL.predict_proba(input_df)[0]
    confidence = round(float(max(proba)) * 100, 1)
    all_probs = {
        cls: round(float(p) * 100, 1)
        for cls, p in zip(MODEL_CLASSES, proba)
    }
    return pred, confidence, all_probs


def estimate_cloud_thickness(cloud_cover_pct, pressure_hpa):
    """
    Estimasi tebal awan dalam meter dari persentase cloud cover dan tekanan.
    Ini pendekatan sederhana buat bridging data API ke fitur dataset.
    """
    base = (cloud_cover_pct / 100.0) * 1200
    pressure_factor = max(0, (1013 - pressure_hpa) / 1013) * 200
    return max(0.0, round(base + pressure_factor, 1))


# BAGIAN 2: KONEKSI KE OPEN-METEO API

GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
WEATHER_URL   = "https://api.open-meteo.com/v1/forecast"

WMO_CODES = {
    0:  ("Cerah", "☀️"),
    1:  ("Sebagian Cerah", "🌤️"),
    2:  ("Berawan Sebagian", "⛅"),
    3:  ("Mendung", "☁️"),
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
    80: ("Hujan Lokal", "🌦️"),
    81: ("Hujan Lokal Sedang", "🌧️"),
    82: ("Hujan Lokal Lebat", "⛈️"),
    95: ("Badai Petir", "⛈️"),
    96: ("Badai Petir + Hujan Es", "⛈️"),
    99: ("Badai Petir Lebat", "⛈️"),
}

def wmo_desc(code):
    return WMO_CODES.get(code, ("Tidak Diketahui", "🌡️"))

def uv_label(uv):
    if uv <= 2:   return ("Rendah", "#4CAF50")
    elif uv <= 5: return ("Sedang", "#FFC107")
    elif uv <= 7: return ("Tinggi", "#FF9800")
    elif uv <= 10: return ("Sangat Tinggi", "#F44336")
    else:          return ("Ekstrem", "#9C27B0")

def wind_dir(deg):
    dirs = ["U", "BL", "T", "TG", "S", "BD", "B", "BT"]
    return dirs[round(deg / 45) % 8]


# BAGIAN 3: ROUTES

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/model-info")
def model_info():
    """Endpoint untuk menampilkan info model dan dataset di UI."""
    return jsonify({
        "model_aktif": MODEL is not None,
        "akurasi": MODEL_ACCURACY,
        "dataset": DATASET_INFO,
        "catatan": (
            "Dataset ini berisi 149 baris data dummy. "
            "Akurasi model terbatas karena ukuran dataset yang kecil, "
            "tapi cukup untuk demo integrasi ML ke dalam Flask."
        )
    })


@app.route("/api/predict-manual", methods=["POST"])
def predict_manual():
    """
    Prediksi cuaca dari input manual pengguna.
    Menerima JSON: { suhu, kelembaban, angin, tebal_awan, tekanan }
    """
    body = request.get_json()
    if not body:
        return jsonify({"error": "Body JSON kosong"}), 400

    try:
        suhu       = float(body["suhu"])
        kelembaban = float(body["kelembaban"])
        angin      = float(body["angin"])
        tebal_awan = float(body["tebal_awan"])
        tekanan    = float(body["tekanan"])
    except (KeyError, ValueError) as e:
        return jsonify({"error": f"Input tidak valid: {e}"}), 400

    pred, confidence, all_probs = predict(suhu, kelembaban, angin, tebal_awan, tekanan)
    if pred is None:
        return jsonify({"error": "Model belum tersedia"}), 500

    return jsonify({
        "prediksi": pred,
        "icon": LABEL_ICON.get(pred, "🌡️"),
        "confidence": confidence,
        "semua_probabilitas": all_probs
    })


@app.route("/api/search")
def search_city():
    """Cari nama kota via Open-Meteo Geocoding API."""
    query = request.args.get("q", "").strip()
    if not query:
        return jsonify({"error": "Query kosong"}), 400

    try:
        resp = requests.get(GEOCODING_URL, params={
            "name": query, "count": 6,
            "language": "id", "format": "json"
        }, timeout=10)
        data = resp.json()

        results = []
        for r in data.get("results", []):
            results.append({
                "name":     r.get("name"),
                "country":  r.get("country", ""),
                "admin1":   r.get("admin1", ""),
                "lat":      r.get("latitude"),
                "lon":      r.get("longitude"),
                "timezone": r.get("timezone", "Asia/Jakarta")
            })
        return jsonify(results)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/weather")
def get_weather():
    """
    Ambil data cuaca real-time dari Open-Meteo,
    lalu jalankan prediksi ML dari data yang diterima.
    """
    lat = request.args.get("lat")
    lon = request.args.get("lon")
    tz  = request.args.get("timezone", "Asia/Jakarta")

    if not lat or not lon:
        return jsonify({"error": "Koordinat diperlukan"}), 400

    try:
        resp = requests.get(WEATHER_URL, params={
            "latitude": lat, "longitude": lon,
            "current": [
                "temperature_2m", "relative_humidity_2m", "apparent_temperature",
                "precipitation", "weather_code", "surface_pressure",
                "wind_speed_10m", "wind_direction_10m", "wind_gusts_10m",
                "uv_index", "visibility", "is_day", "cloud_cover"
            ],
            "hourly": [
                "temperature_2m", "precipitation_probability",
                "weather_code", "wind_speed_10m", "cloud_cover",
                "relative_humidity_2m", "surface_pressure"
            ],
            "daily": [
                "weather_code", "temperature_2m_max", "temperature_2m_min",
                "precipitation_sum", "precipitation_probability_max",
                "wind_speed_10m_max", "sunrise", "sunset", "uv_index_max"
            ],
            "timezone": tz,
            "forecast_days": 7,
            "wind_speed_unit": "kmh"
        }, timeout=15)

        raw   = resp.json()
        cur   = raw.get("current", {})
        daily = raw.get("daily",   {})
        hrly  = raw.get("hourly",  {})

        # Data cuaca saat ini
        temp      = cur.get("temperature_2m", 25)
        humidity  = cur.get("relative_humidity_2m", 70)
        wind      = cur.get("wind_speed_10m", 10)
        pressure  = cur.get("surface_pressure", 1013)
        cloud_pct = cur.get("cloud_cover", 50)

        # Estimasi tebal awan dari cloud cover % dan tekanan
        tebal_awan = estimate_cloud_thickness(cloud_pct, pressure)

        # Jalankan prediksi ML
        ml_pred, ml_conf, ml_probs = predict(temp, humidity, wind, tebal_awan, pressure)

        wcode = cur.get("weather_code", 0)
        desc, icon = wmo_desc(wcode)
        uv_val = cur.get("uv_index", 0)
        uv_lbl, uv_clr = uv_label(uv_val)

        # Prakiraan per jam (24 jam ke depan)
        hourly_list = []
        for i, t in enumerate(hrly.get("time", [])[:48]):
            try:
                dt = datetime.fromisoformat(t)
                if dt < datetime.now() - timedelta(hours=1):
                    continue

                h_cloud    = hrly.get("cloud_cover", [50]*48)[i]
                h_pressure = hrly.get("surface_pressure", [1013]*48)[i]
                h_humidity = hrly.get("relative_humidity_2m", [70]*48)[i]
                h_wind     = hrly["wind_speed_10m"][i]
                h_temp     = hrly["temperature_2m"][i]
                h_awan     = estimate_cloud_thickness(h_cloud, h_pressure)

                h_pred, h_conf, _ = predict(h_temp, h_humidity, h_wind, h_awan, h_pressure)

                hourly_list.append({
                    "time":      dt.strftime("%H:%M"),
                    "temp":      round(h_temp),
                    "rain_prob": hrly["precipitation_probability"][i],
                    "code":      hrly["weather_code"][i],
                    "icon":      wmo_desc(hrly["weather_code"][i])[1],
                    "wind":      round(h_wind),
                    "ml_pred":   h_pred,
                    "ml_icon":   LABEL_ICON.get(h_pred, "") if h_pred else "",
                    "ml_conf":   h_conf
                })

                if len(hourly_list) >= 24:
                    break
            except Exception:
                pass

        # Prakiraan 7 hari
        daily_list = []
        for i in range(len(daily.get("time", []))):
            try:
                dt    = datetime.fromisoformat(daily["time"][i])
                label = "Hari Ini" if i == 0 else ("Besok" if i == 1 else dt.strftime("%A")[:3])
                d, ic = wmo_desc(daily["weather_code"][i])
                daily_list.append({
                    "label":     label,
                    "date":      dt.strftime("%d %b"),
                    "desc":      d,
                    "icon":      ic,
                    "max":       round(daily["temperature_2m_max"][i]),
                    "min":       round(daily["temperature_2m_min"][i]),
                    "rain":      daily["precipitation_sum"][i],
                    "rain_prob": daily["precipitation_probability_max"][i],
                    "wind_max":  round(daily["wind_speed_10m_max"][i]),
                    "sunrise":   daily["sunrise"][i].split("T")[1] if daily.get("sunrise") else "--",
                    "sunset":    daily["sunset"][i].split("T")[1]  if daily.get("sunset")  else "--",
                    "uv":        daily["uv_index_max"][i]
                })
            except Exception:
                pass

        return jsonify({
            "current": {
                "temp":        round(temp),
                "feels_like":  round(cur.get("apparent_temperature", temp)),
                "humidity":    humidity,
                "pressure":    round(pressure),
                "wind_speed":  round(wind),
                "wind_dir":    wind_dir(cur.get("wind_direction_10m", 0)),
                "wind_deg":    cur.get("wind_direction_10m", 0),
                "wind_gust":   round(cur.get("wind_gusts_10m", 0)),
                "visibility":  round(cur.get("visibility", 10000) / 1000, 1),
                "precipitation": cur.get("precipitation", 0),
                "cloud_cover": cloud_pct,
                "uv_index":    uv_val,
                "uv_label":    uv_lbl,
                "uv_color":    uv_clr,
                "description": desc,
                "icon":        icon,
                "weather_code": wcode,
                "is_day":      cur.get("is_day", 1)
            },
            "ml": {
                "prediksi":     ml_pred,
                "icon":         LABEL_ICON.get(ml_pred, "") if ml_pred else "",
                "confidence":   ml_conf,
                "probabilitas": ml_probs,
                "input_dipakai": {
                    "suhu":       round(temp, 1),
                    "kelembaban": humidity,
                    "angin":      round(wind, 1),
                    "tebal_awan": tebal_awan,
                    "tekanan":    round(pressure, 1)
                }
            },
            "hourly":  hourly_list,
            "daily":   daily_list,
            "updated": datetime.now().strftime("%d %b %Y, %H:%M")
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True, port=5000)
