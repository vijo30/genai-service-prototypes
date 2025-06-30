# Agente Conversacional Dual para Debates Éticos

Este repositorio contiene el código fuente y los artefactos de investigación para el trabajo de título "DISEÑO Y EVALUACIÓN DE UN AGENTE CONVERSACIONAL DUAL PARA FOMENTAR LA DIVERSIDAD ARGUMENTATIVA EN DEBATES ÉTICOS SIMULADOS".

El proyecto consiste en un prototipo de agente de IA (v1.0) diseñado para intervenir en discusiones, y un framework completo para su simulación y evaluación en un entorno controlado.

## Estructura del Repositorio

-   `/backend`: Contiene el servicio Flask que actúa como API, el gestor de WebSockets y la lógica del agente de IA (`chat_agent.py`).
-   `/frontend`: Una aplicación simple en React para visualizar e interactuar con el chat en tiempo real.
-   `/simulation_scripts`: Scripts de Python para ejecutar las simulaciones (`chat_test.py`) y analizar los resultados (`1_calculate_metrics.py`, `2_run_analysis.py`).
-   `/simulated_conversations`: Directorio donde se guardan los resultados de las simulaciones (archivos `.csv`).
-   `/nginx`: Configuración de Nginx para actuar como reverse proxy.
-   `docker-compose.yml`: Archivo para orquestar todos los servicios con Docker.
-   `.env.example`: Plantilla para las variables de entorno necesarias.

---

## Requisitos Previos

-   Docker (`20.10+`)
-   Docker Compose (`1.29+`)
-   Python (`3.9+`) con `pip` para los scripts de análisis.
-   Git

---

## Guía de Puesta en Marcha y Replicación del Estudio

Para replicar completamente este estudio, siga los siguientes pasos en orden.

### Paso 1: Configuración del Entorno

1.  **Clonar el repositorio:**
    ```bash
    git clone [URL-DE-TU-REPOSITORIO]
    cd [NOMBRE-DE-TU-REPOSITORIO]
    ```

2.  **Configurar las variables de entorno:**
    -   Cree una copia del archivo de ejemplo:
        ```bash
        cp .env.example .env
        ```
    -   Abra el archivo `.env` con un editor de texto y añada sus claves de API para los LLMs (OpenAI, Google Gemini, DeepSeek).

    ```dotenv
    # .env
    OPENAI_API_KEY="sk-..."
    GOOGLE_API_KEY="AIzaSy..."
    DEEPSEEK_API_KEY="sk-..."
    # No es necesario modificar las otras variables si se usa Docker.
    ```

### Paso 2: Ejecutar los Servicios con Docker

El sistema completo (backend, frontend, Redis, etc.) se levanta con un solo comando. Esto es necesario para que el script de simulación pueda interactuar con el bot.

```bash
docker-compose up --build -d
```
-   `--build`: Fuerza la reconstrucción de las imágenes si ha habido cambios en el código.
-   `-d`: Ejecuta los contenedores en segundo plano (detached mode).

Para verificar que todo está funcionando, puede revisar los logs:
```bash
docker-compose logs -f backend worker
```
Presione `Ctrl+C` para salir de los logs.

### Paso 3: Ejecutar el Banco de Pruebas Sintético

Estas simulaciones generan los datos crudos que se usarán en el análisis. **Este es el paso más largo y puede tardar varias horas**, dependiendo del número de repeticiones y la latencia de las APIs de los LLMs.

1.  **Navegue a la carpeta de scripts:**
    ```bash
    cd simulation_scripts
    ```

2.  **Instale las dependencias necesarias para los scripts:**
    ```bash
    pip install -r requirements.txt
    ```
    *(Nota: Asegúrese de que `requirements.txt` en esta carpeta contenga `pandas`, `pysentimiento`, `readability-lxml`, `scipy`, etc.)*

3.  **Ejecute el script de simulación:**
    ```bash
    python chat_test.py
    ```
    El script imprimirá en la consola el progreso de cada simulación. Al finalizar, todos los archivos `.csv` de las conversaciones se encontrarán en la carpeta `simulated_conversations`.

### Paso 4: Realizar el Análisis de Resultados

Una vez que todas las simulaciones han finalizado, se procede a analizar los datos generados. Este proceso está dividido en dos fases para mayor modularidad.

1.  **Calcular las métricas proxy:**
    Este script lee todos los CSVs de conversaciones y calcula las métricas objetivas para cada una.
    ```bash
    python 1_calculate_metrics.py
    ```
    Esto generará un archivo `raw_metrics_summary.csv` dentro de la carpeta `simulated_conversations`.

2.  **Ejecutar el análisis estadístico global:**
    Este script toma el resumen anterior, calcula el índice compuesto (ICCA) y realiza las comparaciones estadísticas.
    ```bash
    python 2_run_analysis.py
    ```
    Los resultados del análisis se imprimirán directamente en la consola y se guardará un archivo final `final_analysis_with_icca.csv` con todos los datos procesados. Los resultados impresos en la consola son los que se reportan en el informe de tesis.

### Paso 5: Detener los Servicios

Cuando haya terminado con las simulaciones y el análisis, puede detener todos los servicios de Docker con el siguiente comando desde la raíz del proyecto:
```bash
docker-compose down
```

---

## Estructura del Código Clave

-   `backend/chat_agent.py`: Contiene la lógica principal del agente dual (`Supervisor` y `DevilsAdvocate`), incluyendo los `prompts` que definen su comportamiento.
-   `simulation_scripts/chat_test.py`: Orquesta la ejecución de la matriz de experimentos completa, instanciando los agentes simuladores y gestionando las conversaciones.
-   `simulation_scripts/1_calculate_metrics.py` y `2_run_analysis.py`: Implementan el protocolo de medición y análisis estadístico descrito en la metodología del informe.

