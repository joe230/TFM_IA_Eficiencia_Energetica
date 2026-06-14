import os
import pandas as pd
import numpy as np
from dotenv import load_dotenv

from src.db.database import SessionLocal, engine
from src.db.models import DeviceTelemetry
from src.utils.finance import convert_energy_to_cost
from src.utils.logger_config import setup_logger

load_dotenv()
logger = setup_logger(__name__)

PRICE_KWH = float(os.getenv("PRICE_KWH"))

def load_all_telemetry_df() -> pd.DataFrame:
    """
    Queries the database using the global engine and returns 
    all telemetry historical records as a clean Pandas DataFrame.
    """
    try:
        with SessionLocal() as db:
            query = db.query(DeviceTelemetry)
            return pd.read_sql_query(query.statement, engine)
    except Exception as e:
        logger.error(f"Error extracting records from database: {str(e)}")
        return pd.DataFrame()

def raw_telemetry_to_daily(df_raw: pd.DataFrame) -> pd.DataFrame:
    """
    Transforms raw telemetry from the database into aggregated daily records
    per sensor, calculating the daily financial cost in euros.
    """
    df_raw['timestamp'] = pd.to_datetime(df_raw['timestamp'])
    df_raw['date'] = df_raw['timestamp'].dt.date
    
    daily_chunks = []
    for sensor_id, group in df_raw.groupby('sensor_id'):
        group = group.sort_values('timestamp')
        
        # Aggregate telemetry features on a daily level
        daily_summary = group.groupby('date').agg(
            average_power_w=('power_w', 'mean'),
            kwh_max=('total_energy_kwh', 'max'),
            kwh_min=('total_energy_kwh', 'min')
        ).reset_index()
        
        # Calculate differential daily energy consumption
        daily_summary['daily_energy_kwh'] = daily_summary['kwh_max'] - daily_summary['kwh_min']
        
        # Fallback correction in case the Home Assistant accumulator reset or failed
        daily_summary['daily_energy_kwh'] = np.where(
            daily_summary['daily_energy_kwh'] <= 0,
            (daily_summary['average_power_w'] * 24) / 1000.0,
            daily_summary['daily_energy_kwh']
        )
        
        # Financial transformation using the utility module and the loaded .env tariff
        daily_summary['daily_spend_euros'] = daily_summary['daily_energy_kwh'].apply(
            lambda x: convert_energy_to_cost(x, PRICE_KWH)
        )
        
        daily_summary['sensor_id'] = sensor_id
        daily_chunks.append(daily_summary)
        
    return pd.concat(daily_chunks, ignore_index=True)


def build_training_features_and_target(df_raw: pd.DataFrame) -> pd.DataFrame:
    """
    Full processing pipeline for training: Aggregates telemetry data daily,
    calculates Lags, and the future 30-day spend TARGET.
    """
    # 1. Convert raw telemetry to cleaned daily summaries
    df_daily = raw_telemetry_to_daily(df_raw)
    
    # 2. Compute time-series features
    processed_sensors = []
    for sensor_id, group in df_daily.groupby('sensor_id'):
        group = group.sort_values('date').copy()
        group['date'] = pd.to_datetime(group['date'])
        
        # Calendar features
        group['month'] = group['date'].dt.month
        group['day_of_week'] = group['date'].dt.dayofweek
        group['is_weekend'] = group['date'].dt.dayofweek.isin([5, 6]).astype(int)
        
        # Historical time-series features (Lags & Rolling Windows)
        group['spend_yesterday'] = group['daily_spend_euros'].shift(1)
        group['spend_last_7d'] = group['daily_spend_euros'].rolling(window=7).sum()
        group['spend_last_30d'] = group['daily_spend_euros'].rolling(window=30).sum()
        group['average_power_7d'] = group['average_power_w'].rolling(window=7).mean()
        
        # TARGET: Sum of the cost for the NEXT 30 days (looking into the future)
        group['TARGET_spend_next_30d'] = (
            group['daily_spend_euros']
            .iloc[::-1]
            .rolling(window=30)
            .sum()
            .iloc[::-1]
            .shift(-1)
        )
        
        # Clean rows with NaN values introduced by shifting/rolling
        group = group.dropna()
        processed_sensors.append(group)
        
    return pd.concat(processed_sensors, ignore_index=True)