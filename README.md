# Agente Conversacional Dual para Debates Éticos

Este repositorio contiene el código fuente y los artefactos de investigación para el trabajo de título "DISEÑO Y EVALUACIÓN DE UN AGENTE CONVERSACIONAL DUAL PARA FOMENTAR LA DIVERSIDAD ARGUMENTATIVA EN DEBATES ÉTICOS SIMULADOS".

El proyecto consiste en un prototipo de agente de IA (v1.0) diseñado para intervenir en discusiones, y un framework completo para su simulación y evaluación en un entorno controlado.


## Estructura del Repositorio
- `/backend`: Servicio Flask (API y lógica del agente).
- `/frontend`: Aplicación en React para la interfaz de chat.
- `/simulation_scripts`: Scripts de Python para ejecutar y analizar las simulaciones.
- `/shared`: Configuraciones compartidas (`.env.public`, `.env.private`, `caso-sebastian.txt`).
- `/nginx`: Configuración de Nginx como reverse proxy.
- `docker-compose.yml`: Orquestador de servicios.
- `sync-config.js`: Script para sincronizar configuraciones de forma segura.

---

## Guía de Puesta en Marcha y Replicación del Estudio

Para replicar este estudio, siga los siguientes pasos en orden.

### Requisitos Previos
- Docker (`20.10+`) y Docker Compose (`1.29+`)
- Node.js (`16+`) y npm (para el script de configuración)
- Python (`3.9+`) y `pip` (para los scripts de análisis)
- Git

### Paso 1: Configuración Inicial del Entorno

1.  **Clonar el repositorio:**
    ```bash
    git clone https://github.com/vijo30/genai-service-prototypes.git
    cd genai-service-prototypes
    ```

2.  **Instalar dependencias de Node.js:**
    ```bash
    npm install
    ```

3.  **Configurar las variables de entorno (Paso Crítico):**
    Este proyecto separa la configuración pública de la privada para máxima seguridad. Deberá crear dos archivos `.env` a partir de las plantillas en la carpeta `/shared`.

    a. **Variables Privadas (Solo para el Backend):**
    -   Copie el archivo de ejemplo: `cp shared/.env.private.example shared/.env.private`
    -   Abra `shared/.env.private` y **añada sus claves de API**. Estas claves NUNCA saldrán del backend.
        ```dotenv
        # shared/.env.private
        OPENAI_API_KEY="sk-..."
        GOOGLE_API_KEY="AIzaSy..."
        DEEPSEEK_API_KEY="sk-..."
        ```

    b. **Variables Públicas (Compartidas con el Frontend):**
    -   Copie el archivo de ejemplo: `cp shared/.env.public.example shared/.env.public`
    -   Abra `shared/.env.public` y configure las variables que necesiten ser conocidas por el frontend. Por defecto, puede dejar la URL de la API.
        ```dotenv
        # shared/.env.public
        API_BASE_URL=http://localhost:80
        ```

4.  **Sincronizar las configuraciones:**
    Ejecute el script de sincronización. Este comando distribuirá de forma inteligente y segura las variables a los directorios `/backend` y `/frontend`.
    ```bash
    node sync-config.js
    ```

### Paso 2: Ejecutar los Servicios con Docker

El sistema completo se levanta con un solo comando.

```bash
docker-compose up --build -d
```
Esto lanzará el backend, frontend, Redis, el worker y Nginx. Por defecto, Nginx expondrá la aplicación en el puerto `80` de su máquina local.

### Paso 3 (Opcional): Exponer el Servicio con Ngrok

Si necesita que la API de su bot sea accesible desde una URL pública (por ejemplo, para pruebas externas o para que los LLMs que corren en la nube puedan hacer callbacks si fuera necesario), puede usar `ngrok`.

1.  **Asegúrese de tener ngrok instalado y autenticado.**
2.  **Exponga el puerto 80**, que es donde Nginx está escuchando:
    ```bash
    ngrok http 80
    ```
3.  Ngrok le proporcionará una URL pública (`https://<hash>.ngrok-free.app`). Debe tomar esta URL base y actualizar la variable `API_BASE_URL` en el archivo `.env` del backend (y volver a sincronizar si es necesario) para que los scripts de simulación apunten a la dirección correcta.

### Paso 4: Ejecutar el Banco de Pruebas Sintético

Este es el paso más largo y consume recursos de las APIs.

1.  **Navegue a la carpeta de scripts:**
    ```bash
    cd simulation_scripts
    ```

2.  **Instale las dependencias de Python:**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Ejecute el script de simulación:**
    ```bash
    python chat_test.py
    ```
    Las conversaciones se guardarán en la carpeta `simulated_conversations`.

### Paso 5: Realizar el Análisis de Resultados

Una vez finalizadas las simulaciones:

1.  **Calcular las métricas proxy:**
    ```bash
    python 1_calculate_metrics.py
    ```

2.  **Ejecutar el análisis estadístico global:**
    ```bash
    python 2_run_analysis.py
    ```
    Esto generará los gráficos en `simulated_conversations/analysis_plots` y los informes estadísticos en formato `.csv`.

### Paso 6: Detener los Servicios

Cuando haya terminado, detenga todos los contenedores:
```bash
docker-compose down
```
---


## Estructura del Código Clave

-   `backend/chat_agent.py`: Contiene la lógica principal del agente dual (`Supervisor` y `DevilsAdvocate`), incluyendo los `prompts` que definen su comportamiento.
-   `simulation_scripts/chat_test.py`: Orquesta la ejecución de la matriz de experimentos completa, instanciando los agentes simuladores y gestionando las conversaciones.
-   `simulation_scripts/1_calculate_metrics.py` y `2_run_analysis.py`: Implementan el protocolo de medición y análisis estadístico descrito en la metodología del informe.

