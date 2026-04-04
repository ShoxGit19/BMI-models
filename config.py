# Configuration file
import os

class Config:
    """Application configuration"""
    DEBUG = True
    DATA_FILE = "sensor_monitoring_1M.csv"  # Advanced 7-parameter file
    MODEL_FILE = "hybrid_model.pkl"

    # Enhanced sensor limits (7 parameters)
    SENSOR_LIMITS = {
        "Harorat_min": 15,
        "Harorat_max": 45,
        "Tok_min": 8,
        "Tok_max": 22,
        "Kuchlanish_min": 210,
        "Kuchlanish_max": 235,
        "Vibratsiya_max": 1.8,
        "Sim_holati_min": 75,  # % healthy
        "Humidity_min": 35,
        "Humidity_max": 85
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

