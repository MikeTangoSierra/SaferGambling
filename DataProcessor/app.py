from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import pandas as pd
import numpy as np
import joblib
import shap
from datetime import datetime
from confluent_kafka import Consumer, Producer, KafkaError
import json
import threading
import os

KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP", "kafka:9092")

# -----------------------------
# LOAD ARTIFACTS
# -----------------------------
model = joblib.load("./Model/logistic_model_v1.pkl")
scaler = joblib.load("./Model/scaler_v1.pkl")
features = joblib.load("./Model/model_features_v1.pkl")
explainer = shap.Explainer(model, np.zeros((1, len(features))))  # dummy init

# -----------------------------
# API INITIALIZATION
# -----------------------------
app = FastAPI(title="Explainable Hybrid ML Risk API", version="1.0")

# -----------------------------
# INPUT MODEL
# -----------------------------
class CustomerData(BaseModel):
    customer_id: str
    financial_risk_score: float
    behavioral_risk_score: float
    deposit_to_wager_ratio: float
    loss_to_deposit_ratio: float
    session_intensity: float
    financial_stress_score: float
    repeat_segment_entries_7d: float
    tr_extended_gameplay: float
    tr_long_session: float
    tr_at_risk_hours: float
    tr_weekly_hours: float
    tr_binges: float
    tr_big_win_then_increase: float
    tr_high_wagering: float

# -----------------------------
# SCORING FUNCTION
# -----------------------------
def score_customer(data: dict):
    df = pd.DataFrame([data])
    
    X = df[features]
    X_scaled = scaler.transform(X)
    
    ml_prob = float(model.predict_proba(X_scaled)[:, 1][0])
    ml_flag = bool(ml_prob > 0.5)
    
    early_risk = float(df["financial_risk_score"].iloc[0]*0.5 + df["behavioral_risk_score"].iloc[0]*0.5)
    final_score = float(0.5*early_risk + 0.5*ml_prob)
    
    shap_values = explainer(X_scaled)
    shap_contributions = {
        f: float(v) for f, v in sorted(
            zip(features, shap_values.values[0]),
            key=lambda x: abs(x[1]),
            reverse=True
        )[:5]
    }
    
    behavior_cols = [
        "repeat_segment_entries_7d","tr_extended_gameplay","tr_long_session",
        "tr_at_risk_hours","tr_weekly_hours","tr_binges","tr_big_win_then_increase","tr_high_wagering"
    ]
    triggers = [str(col) for col in behavior_cols if df[col].iloc[0] > 0]
    
    reasons = []
    if df["financial_risk_score"].iloc[0] > 0.7:
        reasons.append("High financial risk")
    reasons += triggers
    if ml_flag:
        reasons.append("ML anomaly")
    
    return {
        "customer_id": str(data["customer_id"]),
        "risk": {
            "final_score": final_score,
            "band": ("HIGH" if final_score >= 0.8 else
                     "MEDIUM" if final_score >= 0.5 else
                     "LOW" if final_score >= 0.2 else "MINIMAL"),
            "flag": ml_flag or final_score >= 0.5
        },
        "scores": {
            "ml_probability": ml_prob,
            "early_score": early_risk,
            "financial_score": float(df["financial_risk_score"].iloc[0]),
            "behavioral_score": float(df["behavioral_risk_score"].iloc[0])
        },
        "drivers": {
            "top_reasons": reasons,
            "ml_shap_top": shap_contributions
        },
        "metadata": {
            "model_version": "v1.0",
            "scored_at": datetime.utcnow().isoformat()
        }
    }

# -----------------------------
# HTTP POST ENDPOINT
# -----------------------------
@app.post("/score")
def score_endpoint(customer: CustomerData):
    try:
        return score_customer(customer.dict())
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# -----------------------------
# OPTIONAL KAFKA STREAMING WORKER
# -----------------------------
def kafka_worker():
    INPUT_TOPIC = "customer_events"
    OUTPUT_TOPIC = "risk_scores"
    
    consumer = Consumer({
        "bootstrap.servers": KAFKA_BOOTSTRAP,
        "group.id": "risk_worker",
        "auto.offset.reset": "earliest"
    })
    producer = Producer({"bootstrap.servers": KAFKA_BOOTSTRAP})
    consumer.subscribe([INPUT_TOPIC])
    
    print("⚡ Kafka scoring worker started...")
    
    try:
        while True:
            msg = consumer.poll(1.0)
            if msg is None:
                continue
            if msg.error():
                if msg.error().code() != KafkaError._PARTITION_EOF:
                    print("Kafka error:", msg.error())
                continue
            try:
                event = json.loads(msg.value().decode("utf-8"))
                scored = score_customer(event)
                producer.produce(
                    OUTPUT_TOPIC,
                    key=event["customer_id"],
                    value=json.dumps(scored).encode("utf-8")
                )
                producer.flush()
                print(f"Scored customer {event['customer_id']}")
            except Exception as e:
                print(f"Failed to score event: {e}")
    finally:
        consumer.close()

# -----------------------------
# START KAFKA WORKER IN BACKGROUND
# -----------------------------
threading.Thread(target=kafka_worker, daemon=True).start()