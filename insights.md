Para el MVP, se selecciona una tarifa fija de 0.15 €/kWh por simplicidad. Sin embargo, la arquitectura del software en utils/finance.py queda desacoplada, lo que permitirá en el futuro integrar APIs de precios regulados en tiempo real (como el PVPC en España) sin modificar el modelo de IA.

Se descarta la predicción por meses naturales debido a la escasez de muestras para el entrenamiento del modelo tabular. En su lugar, se implementa un enfoque de "Ventana Deslizante" (Rolling Window) para predecir el coste de los siguientes 30 días, optimizando el tamaño del dataset de entrenamiento a más de 300 instancias temporales.

Sensor ➔ HA ➔ FastAPI ➔ PostgreSQL

El sistema cuenta con un pipeline de reentrenamiento continuo. Cuando el sistema acumula nuevos datos reales en la base de datos PostgreSQL, el microservicio puede reejecutar el script de entrenamiento para ajustar el modelo Random Forest a los nuevos hábitos estacionales del usuario sin detener los servicios operacionales.

docker exec -it ai_api python -m src.ml.train   

"El sistema se ha diseñado bajo una arquitectura desacoplada. Durante la fase de desarrollo, la telemetría de los dispositivos se ha validado mediante un script de simulación de datos históricos y en tiempo real. Sin embargo, el sistema está preparado para producción: para sustituir la simulación por hardware real (como dispositivos Shelly Plug), basta con aprovechar los Webhooks nativos del ecosistema Shelly o las automatizaciones de Home Assistant para redirigir el flujo de datos hacia la API de Inteligencia Artificial, manteniendo inalterada la lógica del modelo predictivo y la capa de presentación."

// TODO
Hacer el readme y/o Documentacion del proyecto
Repasar el codigo
Subirlo a github


que es datadis?