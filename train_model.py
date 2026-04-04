import pandas as pd
import numpy as np
import pickle
import logging
from sklearn.ensemble import RandomForestClassifier, VotingClassifier
from sklearn.neural_network import MLPClassifier
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

logger.info("📊 CSV yuklanmoqda...")
df = pd.read_csv("sensor_monitoring_1M.csv")
logger.info(f"✅ {len(df)} rows, {len(df.columns)} cols yuklandi")

# 7 features - exact column names expected in CSV
feature_cols = [
    "Harorat (C)",
    "Tok_kuchi (A)",
    "Kuchlanish (V)",
    "Vibratsiya",
    "Sim_mexanik_holati (%)",
    "Atrof_muhit_humidity (%)",
    "Quvvati (kW)"
]

target_col = "Fault"

# Select features and target
X = df[feature_cols].copy()
y = df[target_col].copy()

logger.info(f"Features shape: {X.shape}")

# Sample for faster training (keep deterministic)
sample_size = min(100000, len(X))
if sample_size < len(X):
    rng = np.random.default_rng(42)
    indices = rng.choice(len(X), sample_size, replace=False)
    X_sample = X.iloc[indices]
    y_sample = y.iloc[indices]
else:
    X_sample = X
    y_sample = y

logger.info(f"Sample size: {X_sample.shape[0]} rows")

# Split data
X_train, X_test, y_train, y_test = train_test_split(
    X_sample, y_sample, test_size=0.2, random_state=42
)

# Build pipeline: scaler + voting classifier (RandomForest + MLP)
rf = RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=-1)
mlp = MLPClassifier(hidden_layer_sizes=(100, 50), max_iter=300, random_state=42)

voting = VotingClassifier(estimators=[("rf", rf), ("mlp", mlp)], voting="soft", n_jobs=-1)

pipeline = Pipeline([
    ("scaler", StandardScaler()),
    ("voting", voting)
])

logger.info("Training VotingClassifier pipeline...")
pipeline.fit(X_train, y_train)

score = pipeline.score(X_test, y_test)
logger.info(f"Pipeline accuracy: {score:.3f}")

# Save trained pipeline
with open("hybrid_model.pkl", "wb") as f:
    pickle.dump(pipeline, f)

logger.info("Pipeline saved to hybrid_model.pkl")
