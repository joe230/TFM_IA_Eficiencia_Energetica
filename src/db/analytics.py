from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import func, extract

from src.db.models import DeviceTelemetry    
from src.utils.logger_config import setup_logger     

logger = setup_logger(__name__)

def get_monthly_energy_stats(db: Session) -> str:
    """
    Extracts monthly energy consumption statistics from the database and formats them into a structured report for LLM processing. 
    The function calculates total kWh consumed for each device in the current month and identifies the day of the week with the highest average power consumption.
    """
    now = datetime.now()
    current_year = now.year
    current_month = now.month

    logger.info(f"Generating monthly database analytics context for period: {current_month}/{current_year}...")

    try:
        monthly_consumption = (
            db.query(
                DeviceTelemetry.sensor_id,
                (func.max(DeviceTelemetry.total_energy_kwh) - func.min(DeviceTelemetry.total_energy_kwh)).label("kwh_consumed")
            )
            .filter(
                extract('year', DeviceTelemetry.timestamp) == current_year,
                extract('month', DeviceTelemetry.timestamp) == current_month
            )
            .group_by(DeviceTelemetry.sensor_id)
            .all()
        )

        if not monthly_consumption:
            logger.warning(f"Analytics aborted: No telemetry records found for the period {current_month}/{current_year}.")
            return None

        logger.info(f"Processing weekly patterns and activity peaks for {len(monthly_consumption)} active sensors...")

        dow_mapping = {0: "Domingo", 1: "Lunes", 2: "Martes", 3: "Miércoles", 4: "Jueves", 5: "Viernes", 6: "Sábado"}
        
        weekly_patterns = (
            db.query(
                DeviceTelemetry.sensor_id,
                extract('dow', DeviceTelemetry.timestamp).label("day_of_week"),
                func.avg(DeviceTelemetry.power_w).label("avg_power")
            )
            .filter(
                extract('year', DeviceTelemetry.timestamp) == current_year,
                extract('month', DeviceTelemetry.timestamp) == current_month
            )
            .group_by(DeviceTelemetry.sensor_id, "day_of_week")
            .order_by(DeviceTelemetry.sensor_id, func.avg(DeviceTelemetry.power_w).desc())
            .all()
        )

        top_days = {}
        for sensor_id, dow, avg_power in weekly_patterns:
            if sensor_id not in top_days:
                top_days[sensor_id] = dow_mapping.get(int(dow), "Desconocido")

        stats_context = f"Estadísticas extraídas de la base de datos para el periodo {current_month}/{current_year}:\n"
        
        for item in monthly_consumption:
            sensor = item.sensor_id
            kwh = round(item.kwh_consumed, 2) if item.kwh_consumed else 0.0
            peak_day = top_days.get(sensor, "No detectado")
            
            # Limpieza sintáctica para no confundir al LLM con nombres técnicos de entidades de Home Assistant
            friendly_name = sensor.replace("sensor.shelly_", "").replace("_kitchen", "").replace("_laundry", "").replace("_", " ")
            stats_context += f"- El dispositivo '{friendly_name}' registra {kwh} kWh consumidos. Su mayor patrón de actividad ocurre los {peak_day}s.\n"

        logger.info("Analytics payload compiled and formatted successfully for LLM ingestion.")
        return stats_context

    except Exception as e:
        logger.error(f"Database execution failed during analytics aggregation: {str(e)}", exc_info=True)
        raise e