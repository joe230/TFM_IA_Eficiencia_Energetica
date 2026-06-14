# TFM de Predicción de Gasto Energético en el hogar con IA

Este proyecto implementa un pipeline de Machine Learning para la monitorización y predicción del consumo eléctrico en el hogar. Utiliza un modelo de **Random Forest Regressor** capaz de predecir el gasto económico acumulado para los **próximos 30 días** con un **$R^2$ Score de 0.9015** y un error medio absoluto (MAE) de solo **0.68 €**. Ademas de un informe de ahorro energético creado por LLM(llama3.2) de **Ollama**.

El sistema está diseñado para recibir telemetría en tiempo real desde **Home Assistant** (sensores Shelly virtuales/reales) a través de una API construida en **FastAPI**, almacenando los datos en **PostgreSQL**.

Este proyecto viene con una preconfiguracion de Home Assistant con dispositivos/sensores simulados en el dashboard `Simulated Shelly Devices`. (Puedes añadir dispositivos/sensores reales si quieres)

Cuenta con 3 apartados:
* **Consumo de Potencia(W) en tiempo real**. Tambien muestra barras de medicion.
* **Predicciones IA de Gasto**. Tambien tiene los botones *Recalcular Predicciones* y *Reentrenar Modelo ML*.
* **Informe de Ahorro Energético**. Suele tardar ~30 segundos en generar la respuesta.

---

## Variables de Entorno (`.env`)

El proyecto cuenta con un archivo `.env` en la raíz para parametrizar tanto la infraestructura de Docker como el comportamiento del núcleo de IA.

```env
POSTGRES_USER=user
POSTGRES_PASSWORD=password
POSTGRES_DB=devices_db
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
PRICE_KWH=0.15                                      # Tarifa eléctrica simulada (€/kWh) para el cálculo de costes
MODEL_PATH=models/monthly_spend_predictor.joblib    # Ruta donde se exporta/carga el modelo entrenado

# Token preconfigurado para 'iot_simulator_dev/sensor_simulator.py'
HA_API=http://localhost:8123/api/states
HA_TOKEN=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiI3ZDA5ZjAwY2U2YzI0Zjg1ODI5MTdkN2FlNjkwMTMxNyIsImlhdCI6MTc4MDMwNzE1MiwiZXhwIjoyMDk1NjY3MTUyfQ.UjWc3_7HAufU9EGkXQY18sIozvdT_1XyT-7-GMMySYM
```

## Despliegue con Docker Compose
Toda la infraestructura (FastAPI + PostgreSQL + Home Assistant + Ollama) está contenerizada para desplegarse con un solo comando.

```bash
docker compose up --build
```
* **Home Assistant** estará disponible en http://localhost:8123 con usuario `admin` y contraseña `admin123`.
* **API** estará disponible en http://localhost:8000/docs

**Nota sobre el HA_TOKEN:** Si quieres crear un nuevo token, haz clic en tu nombre de usuario (abajo a la izquierda en Home Assistant), baja hasta el fondo de la página, ve a **"Tokens de acceso de larga duración"**, crea uno nuevo y pégalo en tu archivo `.env`. Luego, reinicia el contenedor de la API.

Una vez levantado el docker compose, sigue con el entorno de simulación.

## Entorno de Simulación (`iot_simulator_dev/`)
Para el desarrollo, entrenamiento del modelo sin necesidad de hardware real, el proyecto incluye un ecosistema de simulación dentro del directorio `iot_simulator_dev/`.

Para que el sistema funcione correctamente, los scripts deben ejecutarse en el siguiente orden:

1. `data_generator.py` (Generador de los datos)
    * Genera un archivo CSV con 1 año de datos históricos horarios para tres dispositivos: una nevera, un horno  y una lavadora.
    *   ```bash
        python iot_simulator_dev/data_generator.py
        ```
        Nota: Creará los archivos `.csv` correspondientes en el directorio `data/`.
2. `db_seeder.py` (Ingesta de Datos)
    * Se conecta a la base de datos PostgreSQL de Docker, lee los archivos CSV generados por el script anterior y los guarda en la base de datos.
    *   ```bash
        python iot_simulator_dev/db_seeder.py
        ```
3. Antes de pasar al simulador, debes entrenar el modelo por primera vez para que genere el archivo de IA (`.joblib`). Puedes hacerlo de dos formas:
    * **Desde Home Assistant:** Presionando el botón *`Reentrenar Modelo ML`* del Dashboard.
    * **Desde la API:** Haciendo una petición **POST** a `http://localhost:8000/api/train`.
4. `sensor_simulator.py` (Simulación en Tiempo Real)
    * Simula el comportamiento de los sensores físicos Shelly interactuando en tiempo real.
    *   ```bash
        python iot_simulator_dev/sensor_simulator.py
        ```

## ¿Cómo añadir un nuevo dispositivo/sensor?

### Si el dispositivo es SIMULADO:
Antes de ir a Home Assistant, debes dar de alta el dispositivo en tu entorno de desarrollo. Abre `iot_simulator_dev/data_generator.py`, añade tu nuevo dispositivo en la lista `device_configs` con su tipo, y vuelve a ejecutar el generador y el seeder para crear su histórico. 

Solo he creado 3 tipos. `fridge`, `oven` y `washing_machine`. Sientete libre de modificar el script para tener mas tipos de dispositivos.

### Si el dispositivo es REAL o ya has creado su simulación, sigue estos pasos:

### 1. Actualizar `ha_config/automations.yaml` (Para el envío de datos)
Como la automatización utiliza variables dinámicas para capturar los datos, solo tienes que añadir el nuevo sensor a la lista de entidades que disparan el *trigger*:

```yaml
- id: 'forward_shelly_telemetry_to_fastapi'
  alias: "Forward Shelly Telemetry to FastAPI"
  trigger:
    - platform: state
      entity_id:
        - sensor.shelly_fridge_kitchen
        - sensor.shelly_oven_kitchen
        - sensor.shelly_washing_machine_laundry
        - sensor.ejemplo_sensor # <--- Añade el nuevo sensor aqui
```
### 2. Actualizar `ha_config/configuration.yaml` (Para recibir la predicción)
Para poder visualizar la predicción de los próximos 30 días en Home Assistant, creamos un sensor conectado a la URL de prediccion de la API en el apartado `sensor:`
```yaml
sensor:
  - platform: rest
    name: "Prediccion Ejemplo Sensor"
    unique_id: "ia_ac_predicted_spend_01"
    resource: "http://ai_api:8000/api/predict/monthly/sensor.ejemplo_sensor" # <--- URL con el nombre del sensor
    timeout: 30
    method: GET
    value_template: >
      {% if value_json is defined and value_json.predicted_spend_next_30d is defined %}
        {{ value_json.predicted_spend_next_30d | float }}
      {% else %}
        {{ states('sensor.prediccion_ejemplo_sensor') | default(0, true) }}
      {% endif %}
    unit_of_measurement: "€"
    device_class: monetary
    scan_interval: 43200 # Se actualiza automaticamente cada 12 horas
```
### 3. Actualizar el Dashboard (Para la visualización)
Añade el sensor en las cards correspondientes en el dashboard de Home Assistant. El nombre de la entidad sera el `name` que le has puesto al sensor con '`sensor.`' delante y los espacios en guiones bajos y todo en minúsculas. Por ejemplo, `sensor.prediccion_ejemplo_sensor` para la prediccion configurada en `configuration.yaml`.

## Decisiones de Desarrollo

### ¿Por qué Random Forest?
Se eligió **Random Forest** frente a otros modelos de Machine Learning (como redes neuronales o modelos lineales) por tres razones sencillas:
* **Mejor con los picos de consumo:** Electrodomésticos como la lavadora o el horno tienen picos de potencia muy bruscos. Este modelo entiende estos cambios repentinos perfectamente sin desestabilizarse.
* **Muy ligero:** No consume apenas recursos de procesador o memoria. Puede ejecutarse rápidamente en cualquier ordenador o en una Raspberry Pi sin ralentizar el sistema.
* **Fácil y rápido:** Al agrupar los datos por días, el modelo aprende en pocos segundos y ofrece una precisión altísima (90%) sin configuraciones complejas.

### ¿Por qué Ollama (LLM Local)?
La elección de **Ollama** se hizo principalmente por la oportunidad de probar y experimentar con un modelo de inteligencia artificial (LLM) ejecutado en local. Esto aporta una gran ventaja: **no hay que pasar por ninguna API externa**. Al funcionar de forma local, el sistema es 100% gratuito (sin suscripciones ni pagos por uso), no depende de internet y garantiza que los datos de tu casa sean totalmente privados.