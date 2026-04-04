# --- Ma'lumot va modelni yuklash funksiyasi ---
import os
import logging
import pandas as pd
import numpy as np

# --- Yagona importlar va sozlamalar ---
import os
import logging
import pandas as pd
import numpy as np
import datetime
import pickle
from flask import Flask, render_template, jsonify, request

# --- Flask va logger ---
app = Flask(__name__)
logger = logging.getLogger("bmi-app")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter('[%(asctime)s] %(levelname)s: %(message)s')
handler.setFormatter(formatter)
if not logger.hasHandlers():
    logger.addHandler(handler)

# --- Ma'lumot va modelni yuklash funksiyasi ---
def load_data_and_model():
    df, hybrid_model = None, None
    try:
        if os.path.exists("sensor_monitoring_1M.csv"):
            df = pd.read_csv("sensor_monitoring_1M.csv")
            if "Timestamp" in df.columns:
                df["Timestamp"] = pd.to_datetime(df["Timestamp"], errors='coerce')
        if os.path.exists("hybrid_model.pkl"):
            with open("hybrid_model.pkl", "rb") as f:
                hybrid_model = pickle.load(f)
    except Exception as e:
        logger.error(f"Yuklash xatosi: {e}")
    return df, hybrid_model

df, hybrid_model = load_data_and_model()

# --- ROUTES ---
@app.route("/")
def home():
    return render_template("index.html")

@app.route("/graphs")
def graphs():
    return render_template("graphs.html")

@app.route("/table")
def table():
    return render_template("table.html")

@app.route("/map")
def map_page():
    return render_template("map.html")

@app.route("/model", methods=["GET", "POST"])
def model_page():
    prediction = None
    if request.method == "POST":
        try:
            harorat = float(request.form.get("harorat", 25))
            tok = float(request.form.get("tok", 15))
            kuchlanish = float(request.form.get("kuchlanish", 220))
            vibratsiya = float(request.form.get("vibratsiya", 0.5))
            sim_holati = float(request.form.get("sim_holati", 90))
            humidity = float(request.form.get("humidity", 50))
            quvvat = float(request.form.get("quvvat", 3))
            if hybrid_model is None:
                prediction = "❌ Model tayyor emas"
            else:
                columns = [
                    "Harorat (C)", "Tok_kuchi (A)", "Kuchlanish (V)",
                    "Vibratsiya", "Sim_mexanik_holati (%)",
                    "Atrof_muhit_humidity (%)", "Quvvati (kW)"
                ]
                X_pred = pd.DataFrame([[harorat, tok, kuchlanish, vibratsiya, sim_holati, humidity, quvvat]], columns=columns)
                pred = hybrid_model.predict(X_pred)[0]
                prediction = "⚠️ MUAMMO!" if pred == 1 else "✅ HAVFSIZ"
        except Exception as e:
            prediction = f"❌ Xato: {str(e)}"
    return render_template("model.html", prediction=prediction)

@app.route("/forecast")
def forecast_page():
    return render_template("forecast.html")

# --- API ROUTES ---
@app.route("/api/forecast")
def forecast():
    """So'nggi 7 kun va kelajak uchun xavf prognozi"""
    try:
        if df is None or df.empty or hybrid_model is None:
            return jsonify({"error": "Ma'lumot yoki model yo'q"}), 404

        # So'nggi 7 kun
        now = datetime.datetime.now()
        week_ago = now - datetime.timedelta(days=7)
        last_week = df[df["Timestamp"] >= week_ago]

        # Faqat kerakli ustunlar
        feature_cols = [
            "Harorat (C)", "Tok_kuchi (A)", "Kuchlanish (V)",
            "Vibratsiya", "Sim_mexanik_holati (%)",
            "Atrof_muhit_humidity (%)", "Quvvati (kW)"
        ]
        X = last_week[feature_cols]
        timestamps = last_week["Timestamp"].astype(str).tolist()
        preds = hybrid_model.predict(X)

        # Natijalar
        result = []
        for t, p in zip(timestamps, preds):
            result.append({"timestamp": t, "xavf": int(p)})

        # Kelajak prognozi uchun oxirgi 1 kunlik o'rtacha qiymatlar asosida 24 soatga bashorat
        future = []
        if not last_week.empty:
            avg_vals = X.tail(24).mean().values.reshape(1, -1)
            for i in range(1, 25):
                future_time = now + datetime.timedelta(hours=i)
                pred = int(hybrid_model.predict(avg_vals)[0])
                future.append({"timestamp": future_time.strftime("%Y-%m-%d %H:00"), "xavf": pred})

        return jsonify({"last_week": result, "future": future})
    except Exception as e:
        logger.error(f"Forecast error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/forecast-params")
def forecast_params_api():
    if df is None or df.empty or hybrid_model is None:
        return jsonify({"error": "Ma'lumot yoki model yo'q"}), 404
    now = datetime.datetime.now()
    week_ago = now - datetime.timedelta(days=7)
    last_week = df[df["Timestamp"] >= week_ago].copy()
    feature_cols = [
        "Harorat (C)", "Tok_kuchi (A)", "Kuchlanish (V)",
        "Vibratsiya", "Sim_mexanik_holati (%)",
        "Atrof_muhit_humidity (%)", "Quvvati (kW)"
    ]
    param = request.args.get("param")
    # Resample to 6-hourly means for clarity
    if "Timestamp" in last_week.columns:
        last_week = last_week.set_index("Timestamp").resample("6H").mean().dropna().reset_index()
    result = {"timestamp": last_week["Timestamp"].astype(str).tolist()}
    # Add both raw and smoothed (trend) values
    if param and param in feature_cols:
        values = last_week[param].tolist()
        result[param] = values
        # Only add trend if not Vibratsiya
        if param != "Vibratsiya":
            trend = pd.Series(values).rolling(window=4, min_periods=1).mean().tolist()
            result[param+"_trend"] = trend
    else:
        for col in feature_cols:
            values = last_week[col].tolist()
            result[col] = values
            if col != "Vibratsiya":
                trend = pd.Series(values).rolling(window=4, min_periods=1).mean().tolist()
                result[col+"_trend"] = trend
    # Predict xavf for each resampled row
    if not last_week.empty:
        result["xavf"] = [int(x) for x in hybrid_model.predict(last_week[feature_cols])]
    else:
        result["xavf"] = []
    return jsonify(result)

@app.route("/api/stats")
def get_stats():
    """Statistics with 7 parameters"""
    try:
        if df is None or df.empty:
            return jsonify({"error": "Ma'lumot yo'q"}), 404

        total = df["SensorID"].nunique() if "SensorID" in df.columns else len(df)
        faults = int(df["Fault"].sum())
        ok_count = int((df["Fault"] == 0).sum())
        ok_percent = round(100 * ok_count / len(df), 2) if len(df) > 0 else 0
        # So'nggi 7 kun uchun xavfli vaqtlar
        last_week = df[df["Timestamp"] >= (datetime.datetime.now() - datetime.timedelta(days=7))]
        week_faults = int(last_week["Fault"].sum()) if not last_week.empty else 0
        week_total = len(last_week)
        week_fault_times = last_week[last_week["Fault"] == 1]["Timestamp"].tolist() if "Timestamp" in last_week else []

        return jsonify({
            "total_sensors": total,
            "safe_sensors": ok_count,
            "faults": faults,
            "ok_percent": ok_percent,
            "week_faults": week_faults,
            "week_total": week_total,
            "week_fault_times": week_fault_times,
            "status": "🟢 Barqaror" if ok_percent >= 70 else "🔴 Muammolar",
            "avg_harorat": round(df["Harorat (C)"].mean(), 1),
            "avg_tok": round(df["Tok_kuchi (A)"].mean(), 2),
            "avg_kuchlanish": round(df["Kuchlanish (V)"].mean(), 1),
            "avg_vibratsiya": round(df["Vibratsiya"].mean(), 4),
            "avg_sim_holati": round(df["Sim_mexanik_holati (%)"].mean(), 1),
            "avg_namlik": round(df["Atrof_muhit_humidity (%)"].mean(), 1),
            "avg_quvvat": round(df["Quvvati (kW)"].mean(), 2),
            "timestamp": datetime.datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Stats error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/map-data")
def map_data():
    """Map data - 500 samples for performance"""
    try:
        if df is None or df.empty:
            return jsonify([]), 404

        # Sample for performance
        sample_size = min(500, len(df))
        sample_rate = max(1, len(df) // sample_size)
        data = df.iloc[::sample_rate].copy()

        result = []
        for idx, row in data.iterrows():
            result.append({
                "District": str(row.get("District", "Unknown")),
                "Latitude": float(row.get("Latitude", 41.3111)),
                "Longitude": float(row.get("Longitude", 69.2797)),
                "Harorat": round(float(row.get("Harorat (C)", 25)), 1),
                "Tok": round(float(row.get("Tok_kuchi (A)", 15)), 2),
                "Kuchlanish": round(float(row.get("Kuchlanish (V)", 220)), 1),
                "Vibratsiya": round(float(row.get("Vibratsiya", 0.5)), 4),
                "Sim_holati": round(float(row.get("Sim_mexanik_holati (%)", 90)), 1),
                "Namlik": round(float(row.get("Atrof_muhit_humidity (%)", 50)), 1),
                "Quvvat": round(float(row.get("Quvvati (kW)", 3)), 2),
                "Fault": int(row.get("Fault", 0)),
                "Color": "#dc3545" if int(row.get("Fault", 0)) == 1 else "#28a745"
            })

        return jsonify(result)
    except Exception as e:
        logger.error(f"Map error: {e}")
        return jsonify([]), 500

@app.route("/api/data")
def get_data():
    """All sensor data - 1000 samples"""
    try:
        if df is None or df.empty:
            return jsonify([]), 404

        sample_size = min(1000, len(df))
        sample_rate = max(1, len(df) // sample_size)
        data = df.iloc[::sample_rate].copy()

        result = []
        for idx, row in data.iterrows():
            result.append({
                "District": str(row.get("District", "Unknown")),
                "Timestamp": str(row.get("Timestamp", "")),
                "Harorat": round(float(row.get("Harorat (C)", 25)), 1),
                "Tok": round(float(row.get("Tok_kuchi (A)", 15)), 2),
                "Kuchlanish": round(float(row.get("Kuchlanish (V)", 220)), 1),
                "Vibratsiya": round(float(row.get("Vibratsiya", 0.5)), 4),
                "Sim_holati": round(float(row.get("Sim_mexanik_holati (%)", 90)), 1),
                "Namlik": round(float(row.get("Atrof_muhit_humidity (%)", 50)), 1),
                "Quvvat": round(float(row.get("Quvvati (kW)", 3)), 2),
                "Fault": int(row.get("Fault", 0)),
                "Status": "🔴 MUAMMO" if int(row.get("Fault", 0)) == 1 else "🟢 HAVFSIZ"
            })

        return jsonify(result)
    except Exception as e:
        logger.error(f"Data error: {e}")
        return jsonify([]), 500

# ========================
# ERROR HANDLERS
# ========================
@app.errorhandler(404)
def not_found(error):
    return render_template("error.html", error_code=404, message="Sahifa topilmadi!"), 404

@app.errorhandler(500)
def server_error(error):
    logger.error(f"Server error: {error}")
    return render_template("error.html", error_code=500, message="Serverda xatolik!"), 500

# ========================
# MAIN
# ========================
if __name__ == "__main__":
    logger.info("🚀 Server 0.0.0.0:5000 ishga tushmmoqda")
    app.run(host="0.0.0.0", port=5000, debug=True)
