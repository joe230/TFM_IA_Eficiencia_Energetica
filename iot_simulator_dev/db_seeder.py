import os
import glob
import pandas as pd
from sqlalchemy import create_engine
from dotenv import load_dotenv

load_dotenv(override=True)  

POSTGRES_USER = os.getenv("POSTGRES_USER")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")
POSTGRES_DB = os.getenv("POSTGRES_DB")
POSTGRES_HOST = os.getenv("POSTGRES_HOST")
POSTGRES_PORT = os.getenv("POSTGRES_PORT")

DATABASE_URL = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"

TABLE_NAME = "device_telemetry"

def get_db_connection():
    """Creates a secure connection engine to the PostgreSQL container."""
    return create_engine(DATABASE_URL)

def seed_database():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(base_dir, 'data')
    
    # Find all generated device data CSV files
    csv_files = glob.glob(os.path.join(data_dir, "device-*-data.csv"))
    
    if not csv_files:
        print("No synthetic CSV data found. Run 'python iot_simulator_dev/data_generator.py' first.")
        return
        
    print(f"Connecting to database '{POSTGRES_DB}' on {POSTGRES_HOST}:{POSTGRES_PORT}...")
    conn = get_db_connection()
    total_rows_seeded = 0
    
    # Process csv data to PostgreSQL
    for file_path in csv_files:
        filename = os.path.basename(file_path)
        print(f"Streaming data from file: {filename}...")
        
        df = pd.read_csv(file_path, parse_dates=['timestamp'])
        
        # Stream into database using chunks to keep RAM footprint low
        df.to_sql(
            name=TABLE_NAME,
            con=conn,
            if_exists="append",
            index=False,
            chunksize=1000
        )
        
        file_rows = len(df)
        total_rows_seeded += file_rows
        print(f"Successfully ingested {file_rows} records from {filename}.")
        
    print("\n==================================================")
    print(f"DATABASE SEEDING COMPLETE!")
    print(f"Total rows successfully loaded into table '{TABLE_NAME}': {total_rows_seeded}")
    print("==================================================")

if __name__ == "__main__":
    seed_database()