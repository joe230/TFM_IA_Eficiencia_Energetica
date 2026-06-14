import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
import pandas as pd
import joblib
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.db.models import DeviceTelemetry
from src.ml.preprocessing import raw_telemetry_to_daily
from src.utils.logger_config import setup_logger

load_dotenv()
logger = setup_logger(__name__)

MODEL_PATH = os.getenv("MODEL_PATH", "models/monthly_spend_predictor.joblib")


def predict_next_30d_spend(sensor_id: str, db: Session) -> float:
    """
    Loads the trained Random Forest model, fetches the last 35 days of raw telemetry
    for the specified sensor, aggregates it into daily features, and predicts
    the total financial spend for the next 30 days.
    """
    logger.info(f"Initializing prediction pipeline for sensor: '{sensor_id}'")

    # Load the trained model
    if not os.path.exists(MODEL_PATH):
        error_msg = (
            f"Trained model artifact not found at '{MODEL_PATH}'. "
            f"Please run the training pipeline first: python -m src.ml.train"
        )
        logger.error(f"❌ Inference aborted: {error_msg}")
        raise FileNotFoundError(error_msg)
    
    logger.info(f"Loading model from configuration path: '{MODEL_PATH}'")
    artifact = joblib.load(MODEL_PATH)
    model = artifact['model']
    expected_features = artifact['features']

    # Query 35 days to ensure we have at least 30 full consolidated days after aggregation
    start_date = datetime.now() - timedelta(days=35)
    logger.info(f"Querying database for historical telemetry since {start_date.date()}")
    stmt = (
        select(DeviceTelemetry)
        .where(DeviceTelemetry.sensor_id == sensor_id)
        .where(DeviceTelemetry.timestamp >= start_date)
        .order_by(DeviceTelemetry.timestamp.asc())
    )
    records = db.scalars(stmt).all()

    if not records:
        error_msg = f"No telemetry data found for sensor '{sensor_id}' in the last 35 days."
        logger.error(error_msg)
        raise ValueError(error_msg)

    logger.info(f"Retrieved {len(records)} raw telemetry rows. Transforming into structured DataFrame...")

    # Convert SQLAlchemy ORM objects to a list of dictionaries for Pandas
    raw_data = [
        {
            "timestamp": r.timestamp,
            "sensor_id": r.sensor_id,
            "power_w": r.power_w,
            "total_energy_kwh": r.total_energy_kwh
        }
        for r in records
    ]
    df_raw = pd.DataFrame(raw_data)

    # Convert raw telemetry into daily intervals
    df_daily = raw_telemetry_to_daily(df_raw)

    # To calculate a 30-day rolling window, we strictly need at least 30 distinct days of history
    if len(df_daily) < 28:
        error_msg = (
            f"Insufficient history for sensor '{sensor_id}'. "
            f"The model requires 30 days of historical data to compute rolling trends, "
            f"but only {len(df_daily)} days were found in the database."
        )
        logger.warning(f"Preprocessing constraint: {error_msg}")
        raise ValueError(error_msg)

    # Calculate Time-Series Features for the current state (the latest day available)
    df_daily = df_daily.sort_values('date').reset_index(drop=True)
    df_daily['date'] = pd.to_datetime(df_daily['date'])

    # Compute rolling features over the daily dataframe
    df_daily['month'] = df_daily['date'].dt.month
    df_daily['day_of_week'] = df_daily['date'].dt.dayofweek
    df_daily['is_weekend'] = df_daily['date'].dt.dayofweek.isin([5, 6]).astype(int)

    df_daily['spend_yesterday'] = df_daily['daily_spend_euros'].shift(1)
    df_daily['spend_last_7d'] = df_daily['daily_spend_euros'].rolling(window=7).sum()
    df_daily['spend_last_30d'] = df_daily['daily_spend_euros'].rolling(window=30).sum()
    df_daily['average_power_7d'] = df_daily['average_power_w'].rolling(window=7).mean()

    # Extract strictly the LATEST row which represents "today" for real-time inference
    current_state = df_daily.iloc[[-1]].copy()

    # 5. Feature Alignment: One-Hot Encoding Reconstruction for Sensors
    target_sensor_col = f"sensor_id_{sensor_id}"
    
    for col in expected_features:
        if col not in current_state.columns:
            if col == target_sensor_col:
                current_state[col] = 1  # Active sensor being queried
            elif "sensor_id_" in col:
                current_state[col] = 0  # Inactive sensor in this query context
            else:
                current_state[col] = 0  # Safety fallback for any other missing column

    # Reorder columns to match the exact mathematical space expected by Scikit-Learn
    X_infer = current_state[expected_features]

    # Execute prediction and ensure the output is a single float value representing the next 30-day spend
    predicted_spend = model.predict(X_infer)[0]
    final_prediction = max(0.0, float(predicted_spend))

    logger.info(f"Successfully computed prediction for '{sensor_id}': {final_prediction:.2f} €")

    # Ensure the model never yields negative financial predictions due to minor mathematical fluctuations
    return final_prediction