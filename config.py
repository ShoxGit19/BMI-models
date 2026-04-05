# Configuration file
import os

class Config:
    """Application configuration"""
    DEBUG = True
    DATA_FILE = "sensor_monitoring_1M.csv"  # Advanced 8-parameter file
    MODEL_FILE = "hybrid_model.pkl"

    # Real elektr uzatish liniyasi parametr chegaralari (3 daraja)
    SENSOR_LIMITS = {
        # Kuchlanish (V): Normal 210-230, Ogohlantirish 200-210/230-240, Favqulodda <200/>240
        "Kuchlanish_normal_min": 210,
        "Kuchlanish_normal_max": 230,
        "Kuchlanish_warn_min": 200,
        "Kuchlanish_warn_max": 240,
        # Chastota (Hz): Normal 49.5-50.5, Ogohlantirish 49.0-49.5/50.5-51.0, Favqulodda <49/>51
        "Chastota_normal_min": 49.5,
        "Chastota_normal_max": 50.5,
        "Chastota_warn_min": 49.0,
        "Chastota_warn_max": 51.0,
        # Muhit harorat (C): Normal <40, Ogohlantirish 40-45, Favqulodda >45
        "Harorat_normal_max": 40,
        "Harorat_warn_max": 45,
        # Shamol tezligi (km/h): Normal <15, Ogohlantirish 15-25, Favqulodda >25
        "Shamol_normal_max": 15,
        "Shamol_warn_max": 25,
        # Vibratsiya: Normal <1.0, Ogohlantirish 1.0-1.5, Favqulodda >1.5
        "Vibratsiya_normal_max": 1.0,
        "Vibratsiya_warn_max": 1.5,
        # Sim holati (%): Normal >85, Ogohlantirish 75-85, Favqulodda <75
        "Sim_holati_normal_min": 85,
        "Sim_holati_warn_min": 75,
        # Namlik (%): Normal 35-85, Ogohlantirish 30-35/85-90, Favqulodda <30/>90
        "Humidity_normal_min": 35,
        "Humidity_normal_max": 85,
        "Humidity_warn_min": 30,
        "Humidity_warn_max": 90,
        # Quvvat (kW): Normal <=5, Ogohlantirish 5-5.5, Favqulodda >5.5
        "Quvvat_normal_max": 5.0,
        "Quvvat_warn_max": 5.5,
    }

    # App settings
    REFRESH_INTERVAL = 30000  # milliseconds
    PORT = 5000
    HOST = "0.0.0.0"

class DevelopmentConfig(Config):
    DEBUG = True

class ProductionConfig(Config):
    DEBUG = False

config = DevelopmentConfig()

