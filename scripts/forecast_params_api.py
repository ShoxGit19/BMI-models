# Bu yordamchi API kodini app.py ga qo'shish uchun namunadir
# So'nggi 7 kun uchun barcha parametrlarni va xavfni massiv ko'rinishida qaytaradi
from flask import jsonify
import datetime

def forecast_params_api(df, hybrid_model):
    now = datetime.datetime.now()
    week_ago = now - datetime.timedelta(days=7)
    last_week = df[df["Timestamp"] >= week_ago]
    feature_cols = [
        "Harorat (C)", "Tok_kuchi (A)", "Kuchlanish (V)",
        "Vibratsiya", "Sim_mexanik_holati (%)",
        "Atrof_muhit_humidity (%)", "Quvvati (kW)"
    ]
    param_dict = {col: last_week[col].tolist() for col in feature_cols}
    param_dict["timestamp"] = last_week["Timestamp"].astype(str).tolist()
    param_dict["xavf"] = hybrid_model.predict(last_week[feature_cols]).tolist()
    return jsonify(param_dict)
