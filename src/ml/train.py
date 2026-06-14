import os
import pandas as pd
from dotenv import load_dotenv
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, r2_score
import joblib

from src.ml.preprocessing import load_all_telemetry_df, build_training_features_and_target
from src.utils.logger_config import setup_logger

load_dotenv()
logger = setup_logger(__name__)

MODELS_DIR = "models"
MODEL_PATH = os.getenv("MODEL_PATH", "models/monthly_spend_predictor.joblib")


def train_monthly_predictor():
    logger.info("Connecting to database to extract historical records...")
    raw_df = load_all_telemetry_df()
    
    if raw_df.empty:
        logger.error("No data found in the database. Please run the Seeder first.")
        return
        
    logger.info(f"Telemetry records successfully retrieved: {len(raw_df)}")
    
    logger.info("Running preprocessing pipeline and feature engineering...")
    data = build_training_features_and_target(raw_df)
    
    if data.empty:
        logger.warning("Insufficient historical data to calculate time-series prediction windows.")
        return

    data = data.sort_values(by='date').reset_index(drop=True)

    # One-Hot Encoding for the sensor identifiers
    data = pd.get_dummies(data, columns=['sensor_id'], drop_first=False)
    sensor_cols = [col for col in data.columns if 'sensor_id_' in col]
    
    # Define exact feature space and target variable
    features = [
        'month', 'day_of_week', 'is_weekend', 
        'spend_yesterday', 'spend_last_7d', 'spend_last_30d', 
        'average_power_7d'
    ] + sensor_cols
    target = 'TARGET_spend_next_30d'
    
    X = data[features]
    y = data[target]
    
    # Strict Temporal Split
    split_index = int(len(data) * 0.8)
    X_train, X_test = X.iloc[:split_index], X.iloc[split_index:]
    y_train, y_test = y.iloc[:split_index], y.iloc[split_index:]
    
    logger.info(f"Training Random Forest Regressor with {len(X_train)} daily records...")
    model = RandomForestRegressor(n_estimators=100, max_depth=12, random_state=42, n_jobs=-1)
    model.fit(X_train, y_train)
    
    # Model Evaluation
    y_pred = model.predict(X_test)
    mae = mean_absolute_error(y_test, y_pred)
    r2 = r2_score(y_test, y_pred)
    
    metrics_summary = (
        "\n================ EVALUATION METRICS ================\n"
        f"  MAE (Mean Absolute Error): {mae:.2f} €\n"
        f"  R² Score (Coefficient of Determination): {r2:.4f}\n"
        "===================================================="
    )
    logger.info(metrics_summary)
    
    os.makedirs(MODELS_DIR, exist_ok=True)
    
    model_artifact = {
        'model': model,
        'features': features
    }
    
    joblib.dump(model_artifact, MODEL_PATH)
    logger.info(f"Trained model artifact successfully saved at: '{MODEL_PATH}'")