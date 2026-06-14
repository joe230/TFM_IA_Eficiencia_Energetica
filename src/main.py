from datetime import datetime
from fastapi import FastAPI, Depends, HTTPException, status, BackgroundTasks
from fastapi.concurrency import asynccontextmanager
from sqlalchemy.orm import Session

from src.db.analytics import get_monthly_energy_stats
from src.schemas import TelemetryCreate, TelemetryResponse, PredictionResponse, EnergyReportResponse, HealthCheckResponse, TrainingResponse
from src.db.database import Base, engine, get_db
from src.db.models import DeviceTelemetry, DevicePrediction
from src.ml.predict import predict_next_30d_spend
from src.ml.train import train_monthly_predictor
from src.llm.report_generator import generate_energy_report
from src.utils.logger_config import setup_logger

logger = setup_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI lifespan event to ensure database tables are created before the app starts.
    """
    logger.info("Initializing system lifecycle: Verifying database tables...")
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables successfully verified/created.")
    except Exception as e:
        logger.critical(f"Failed to initialize database tables: {str(e)}", exc_info=True)
        raise e
    yield
    logger.info("Shutting down system lifecycle...")

app = FastAPI(     
    title="Device AI Prediction API",     
    description="Production API Gateway for electrical consumption data ingestion and machine learning pipelines",     
    version="1.0.0",
    lifespan=lifespan
)

training_in_progress = False

def run_training_wrapper():
    """Wrapper function to run the training process in a background thread."""
    global training_in_progress
    logger.info("Background task: Starting training pipeline...")
    try:
        train_monthly_predictor()
    except Exception as e:
        logger.error(f"Background task: Error during training execution: {str(e)}", exc_info=True)
    finally:
        training_in_progress = False
        logger.info("Background task: Flag reset. Ready for next training session.")

# =====================================================================
# API ENDPOINTS
# =====================================================================

@app.get("/", response_model=HealthCheckResponse)
def read_root():
    """Health check endpoint."""
    return HealthCheckResponse(
        status="online",
        message="Device AI Prediction API is running smoothly.",
        timestamp=datetime.now()
    )

@app.post("/api/train", status_code=202, response_model=TrainingResponse)
async def trigger_training(background_tasks: BackgroundTasks):
    """
    Endpoint to trigger the training of the monthly spend predictor in a non-blocking way.
    Uses FastAPI's BackgroundTasks to run the training function asynchronously, allowing for immediate response.
    """
    global training_in_progress
    
    if training_in_progress:
        return TrainingResponse(
            status="in_progress",
            message="El modelo se está entrenando en este momento."
        )
    
    training_in_progress = True
    
    # Delegate the training process to a background thread to avoid blocking the API response
    background_tasks.add_task(run_training_wrapper)
    
    return TrainingResponse(
        status="started",
        message="Entrenamiento del predictor mensual iniciado en segundo plano con éxito."
    )

@app.post("/api/telemetry", response_model=TelemetryResponse, status_code=status.HTTP_201_CREATED)
def receive_telemetry(payload: TelemetryCreate, db: Session = Depends(get_db)):
    """
    Ingests new telemetry records from smart devices.
    Validates data using Pydantic and saves it to PostgreSQL using SQLAlchemy.
    """
    try:
        db_telemetry = DeviceTelemetry(
            sensor_id=payload.sensor_id,
            power_w=payload.power_w,
            voltage_v=payload.voltage_v,
            total_energy_kwh=payload.total_energy_kwh,
            timestamp=datetime.now()
        )
        
        db.add(db_telemetry)
        db.commit()
        db.refresh(db_telemetry)
        
        return db_telemetry
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error during telemetry ingestion: {str(e)}"
        )


@app.get("/api/predict/monthly/{sensor_id}", response_model=PredictionResponse)
def get_monthly_prediction(sensor_id: str, db: Session = Depends(get_db)):
    """
    Triggers the machine learning inference pipeline for a given sensor.
    Calculates features, runs the Random Forest model, logs the prediction
    into the database, and returns the expected 30-day financial spend.
    """
    try:
        # Execute the ML inference pipeline
        forecasted_spend = predict_next_30d_spend(sensor_id=sensor_id, db=db)
        execution_time = datetime.now()
        
        # Saves the prediction into the database
        db_prediction = DevicePrediction(
            sensor_id=sensor_id,
            predicted_spend_next_30d=forecasted_spend,
            timestamp=execution_time
        )
        db.add(db_prediction)
        db.commit()
        
        return PredictionResponse(
            sensor_id=sensor_id,
            predicted_spend_next_30d=round(forecasted_spend, 2),
            calculated_at=execution_time
        )
        
    except FileNotFoundError as fnf_err:
        # If the model .joblib file doesn't exist yet
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(fnf_err))
        
    except ValueError as val_err:
        # If there are less than 30 days of data in the DB for this sensor
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(val_err))
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred during prediction: {str(e)}"
        )
    
@app.post("/api/energy-report")
async def get_ai_report(db: Session = Depends(get_db)):
    """
    Endpoint to generate an AI-powered energy consumption report in Markdown format.
    """
    real_stats = get_monthly_energy_stats(db)
    
    if real_stats is None:
        return EnergyReportResponse(
            status="no_data",
            generated_at=datetime.now(),
            report="Datos insuficientes\nNo se han encontrado registros de consumo en la base de datos para este mes. No es posible generar el informe."
        )
    
    markdown_text = await generate_energy_report(real_stats)
    
    return EnergyReportResponse(
        status="success",
        generated_at=datetime.now(),
        report=markdown_text
    )