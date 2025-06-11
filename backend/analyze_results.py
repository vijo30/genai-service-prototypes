import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os
import json # Para parsear columnas que pueden contener JSON strings
import numpy as np # Necesario para las claves de la paleta con np.True_ y np.False_

# --- Configuración ---
OUTPUT_DIR = "simulated_conversations" # Directorio donde eval_conversations.py guarda los CSV
EVALUATION_RESULTS_FILE = os.path.join(OUTPUT_DIR, "evaluation_results.csv")
PLOTS_OUTPUT_DIR = os.path.join(OUTPUT_DIR, "analysis_plots")
SUMMARY_OUTPUT_DIR = os.path.join(OUTPUT_DIR, "summary_data") # Nuevo directorio para los CSV de resúmenes

# Asegurarse de que los directorios existan
os.makedirs(PLOTS_OUTPUT_DIR, exist_ok=True)
os.makedirs(SUMMARY_OUTPUT_DIR, exist_ok=True) # Asegurar que el directorio de resúmenes exista

print(f"Buscando resultados de evaluación en: {EVALUATION_RESULTS_FILE}")

# --- Cargar y Preparar Datos ---
try:
    df = pd.read_csv(EVALUATION_RESULTS_FILE)
    print(f"Se cargaron {len(df)} filas de datos.")
    print("Columnas disponibles:", df.columns.tolist())
except FileNotFoundError:
    print(f"Error: El archivo '{EVALUATION_RESULTS_FILE}' no fue encontrado.")
    print("Asegúrate de ejecutar 'eval_conversations.py' primero para generar los resultados.")
    exit()
except pd.errors.EmptyDataError:
    print(f"Error: El archivo '{EVALUATION_RESULTS_FILE}' está vacío.")
    exit()
except Exception as e:
    print(f"Error al cargar el archivo CSV: {e}")
    exit()

# Convertir la columna 'con_bot' a tipo booleano para facilitar el agrupamiento
df['con_bot'] = df['con_bot'].astype(bool)

# Convertir columnas relevantes a numéricas, forzando errores a NaN
numeric_cols = [
    'coherencia_general', 'tono_general', 'pertinencia_general', 'reflexion_general',
    'total_interventions', 'vp_count', 'fp_count', 'fn_count', 'vn_count',
    'precision', 'recall', 'f1_score',
    'avg_quality_clarity', 'avg_quality_relevance', 'avg_quality_depth',
    'avg_quality_adherence', 'avg_quality_role_compliance',
    'avg_processing_time_seconds'
]
for col in numeric_cols:
    if col in df.columns:
        # Usar pd.to_numeric con errors='coerce' es robusto para NaN o valores no numéricos
        df[col] = pd.to_numeric(df[col], errors='coerce')
    else:
        print(f"Advertencia: La columna '{col}' no se encontró en los datos y no se pudo convertir.")

# Rellenar NaN en métricas de calidad y procesamiento de intervenciones si 'con_bot' es False
# o si no hubo intervenciones, con 0 para facilitar el análisis comparativo
for col in ['total_interventions', 'vp_count', 'fp_count', 'fn_count', 'vn_count', 'precision', 'recall', 'f1_score',
            'avg_quality_clarity', 'avg_quality_relevance', 'avg_quality_depth',
            'avg_quality_adherence', 'avg_quality_role_compliance', 'avg_processing_time_seconds']:
    if col in df.columns:
        df.loc[df['con_bot'] == False, col] = 0 # Asumir 0 para simulaciones sin bot
        df[col] = df[col].fillna(0) # Rellenar cualquier otro NaN que pueda haber quedado por coerción o si vp_count fue 0


# --- Análisis Descriptivo General ---
print("\n--- Estadísticas Descriptivas por Condición (con/sin Bot) ---")
summary_stats_general = df.groupby('con_bot')[['coherencia_general', 'tono_general', 'pertinencia_general', 'reflexion_general']].agg(['mean', 'std', 'median', 'min', 'max'])

# Aplanar el MultiIndex de las columnas para el CSV (esto es correcto aquí)
summary_stats_general.columns = ['_'.join(col).strip() for col in summary_stats_general.columns.values]
# Opcional: Nombrar el índice para que la primera columna del CSV no esté vacía
summary_stats_general.index.name = 'Bot_Present'

print(summary_stats_general)
# Guardar como CSV
summary_stats_general.to_csv(os.path.join(SUMMARY_OUTPUT_DIR, 'general_conversation_summary.csv'))
print(f"Resumen 'general_conversation_summary.csv' guardado en {SUMMARY_OUTPUT_DIR}")


if True in df['con_bot'].unique():
    print("\n--- Estadísticas Descriptivas de Intervenciones (Solo con Bot) ---")
    df_con_bot_only = df[df['con_bot'] == True]
    intervention_stats = df_con_bot_only[['total_interventions', 'vp_count', 'fp_count', 'fn_count', 'vn_count', 'precision', 'recall', 'f1_score', 'avg_quality_clarity', 'avg_quality_relevance', 'avg_quality_depth', 'avg_quality_adherence', 'avg_quality_role_compliance', 'avg_processing_time_seconds']].agg(['mean', 'std', 'median', 'min', 'max'])
    
    # CORRECCIÓN: Eliminar la línea de aplanado de columnas para intervention_stats.
    # Sus columnas ya son nombres simples, no un MultiIndex.

    # Nombrar el índice para que la primera columna del CSV sea legible
    intervention_stats.index.name = 'Aggregation_Function'

    print(intervention_stats)
    # Guardar como CSV
    intervention_stats.to_csv(os.path.join(SUMMARY_OUTPUT_DIR, 'intervention_metrics_summary.csv'))
    print(f"Resumen 'intervention_metrics_summary.csv' guardado en {SUMMARY_OUTPUT_DIR}")


    print("\n--- Métricas de Intervención por Modelo de Bot (Promedio) ---")
    # Este DataFrame ya tiene columnas planas porque usa .mean() directamente con reset_index()
    intervention_metrics_by_bot = df_con_bot_only.groupby('bot_llm_choice')[['precision', 'recall', 'f1_score', 'avg_quality_clarity', 'avg_quality_relevance', 'avg_quality_depth', 'avg_quality_adherence', 'avg_quality_role_compliance', 'avg_processing_time_seconds']].mean().reset_index()
    print(intervention_metrics_by_bot)
    # Guardar como CSV
    intervention_metrics_by_bot.to_csv(os.path.join(SUMMARY_OUTPUT_DIR, 'intervention_metrics_by_bot_llm.csv'), index=False)
    print(f"Resumen 'intervention_metrics_by_bot_llm.csv' guardado en {SUMMARY_OUTPUT_DIR}")


# --- Visualizaciones ---

# CORRECCIÓN CLAVE AQUÍ: Las claves del diccionario palette deben ser objetos np.bool_
palette = {np.True_: "#4CAF50", np.False_: "#F44336"} # Verde para con_bot, Rojo para sin_bot

# 1. Comparación de Medias de Métricas Generales (Bar Plot)
fig, axes = plt.subplots(1, 4, figsize=(20, 5), sharey=True)
fig.suptitle('Comparación de Puntuaciones Medias de Conversación (con vs. sin Bot)', fontsize=16)

metrics = ['coherencia_general', 'tono_general', 'pertinencia_general', 'reflexion_general']
titles = ['Coherencia', 'Tono', 'Pertinencia', 'Reflexión']

for i, metric in enumerate(metrics):
    # CORRECCIÓN: Añadir 'hue=con_bot' de nuevo, y con legend=False ya no será redundante
    sns.barplot(x='con_bot', y=metric, data=df, ax=axes[i], hue='con_bot', palette=palette, capsize=0.1, legend=False)
    axes[i].set_title(titles[i])
    axes[i].set_xlabel('Con Bot')
    axes[i].set_ylabel('Puntuación Media')
    axes[i].set_xticklabels(['Sin Bot', 'Con Bot'])
    axes[i].set_ylim(0, 5) # Escala de 1 a 5

plt.tight_layout(rect=[0, 0.03, 1, 0.95])
plt.savefig(os.path.join(PLOTS_OUTPUT_DIR, 'mean_metrics_comparison.png'))
plt.close()
print("Gráfica 'mean_metrics_comparison.png' generada.")

# 2. Distribución de Puntuaciones de Métricas Generales (Box Plot)
fig, axes = plt.subplots(1, 4, figsize=(20, 5), sharey=True)
fig.suptitle('Distribución de Puntuaciones de Conversación (con vs. sin Bot)', fontsize=16)

for i, metric in enumerate(metrics):
    # CORRECCIÓN: Añadir 'hue=con_bot' de nuevo, y con legend=False ya no será redundante
    sns.boxplot(x='con_bot', y=metric, data=df, ax=axes[i], hue='con_bot', palette=palette, legend=False)
    axes[i].set_title(titles[i])
    axes[i].set_xlabel('Con Bot')
    axes[i].set_ylabel('Puntuación')
    axes[i].set_xticklabels(['Sin Bot', 'Con Bot'])
    axes[i].set_ylim(0, 5)

plt.tight_layout(rect=[0, 0.03, 1, 0.95])
plt.savefig(os.path.join(PLOTS_OUTPUT_DIR, 'metric_distributions_boxplot.png'))
plt.close()
print("Gráfica 'metric_distributions_boxplot.png' generada.")

# 3. Correlación con el Número de Intervenciones (Scatter Plot)
# Solo para las conversaciones donde el bot estuvo presente
df_con_bot = df[df['con_bot'] == True].copy()

if not df_con_bot.empty:
    fig, axes = plt.subplots(1, 4, figsize=(20, 5), sharey=True)
    fig.suptitle('Relación entre Intervenciones del Bot y Calidad de la Conversación', fontsize=16)

    # Convertir 'bot_llm_choice' y 'user_llm_choice' a tipo category para asegurar colores y estilos consistentes
    df_con_bot['bot_llm_choice'] = df_con_bot['bot_llm_choice'].astype('category')
    df_con_bot['user_llm_choice'] = df_con_bot['user_llm_choice'].astype('category')

    for i, metric in enumerate(metrics):
        sns.scatterplot(x='total_interventions', y=metric, data=df_con_bot, ax=axes[i], hue='bot_llm_choice', style='user_llm_choice', s=100)
        sns.regplot(x='total_interventions', y=metric, data=df_con_bot, ax=axes[i], scatter=False, color='gray', line_kws={'linestyle':'--'}) # Línea de tendencia
        axes[i].set_title(titles[i])
        axes[i].set_xlabel('Número de Intervenciones del Bot')
        axes[i].set_ylabel('Puntuación')
        axes[i].set_ylim(0, 5) # Escala de 1 a 5
        if i == 3: # Añadir leyenda solo una vez
            axes[i].legend(title='LLM Bot / User', bbox_to_anchor=(1.05, 1), loc='upper left')

    plt.tight_layout(rect=[0, 0.03, 0.95, 0.95])
    plt.savefig(os.path.join(PLOTS_OUTPUT_DIR, 'bot_interventions_correlation.png'))
    plt.close()
    print("Gráfica 'bot_interventions_correlation.png' generada.")
else:
    print("No hay datos de conversaciones con bot para generar la gráfica de correlación de intervenciones.")

# 4. Calidad Promedio de las Intervenciones Correctas (True Positives)
# Solo para las conversaciones donde el bot intervino y el evaluador consideró que debió hacerlo
if not df_con_bot.empty and df_con_bot['vp_count'].sum() > 0:
    quality_metrics = [
        'avg_quality_clarity', 'avg_quality_relevance', 'avg_quality_depth',
        'avg_quality_adherence', 'avg_quality_role_compliance'
    ]
    quality_titles = [
        'Claridad', 'Relevancia', 'Profundidad', 'Adherencia a Guías', 'Cumplimiento del Rol'
    ]

    # Calcular la media de las métricas de calidad para las intervenciones de VP
    # Solo en filas donde vp_count es > 0, porque si vp_count es 0, los promedios son 0 por diseño.
    df_vp_interventions = df_con_bot[df_con_bot['vp_count'] > 0]
    
    if not df_vp_interventions.empty:
        # Calcular los promedios por cada LLM Bot
        avg_quality_by_bot = df_vp_interventions.groupby('bot_llm_choice')[quality_metrics].mean().reset_index()
        # Guardar como CSV
        avg_quality_by_bot.to_csv(os.path.join(SUMMARY_OUTPUT_DIR, 'avg_true_positive_quality_by_bot_llm.csv'), index=False)
        print(f"Resumen 'avg_true_positive_quality_by_bot_llm.csv' guardado en {SUMMARY_OUTPUT_DIR}")

        # Reestructurar para seaborn barplot
        metric_title_map = dict(zip(quality_metrics, quality_titles))
        avg_quality_melted = avg_quality_by_bot.melt(id_vars='bot_llm_choice', var_name='Metric', value_name='Score')
        avg_quality_melted['Metric'] = avg_quality_melted['Metric'].map(metric_title_map)

        plt.figure(figsize=(12, 7))
        sns.barplot(x='Metric', y='Score', hue='bot_llm_choice', data=avg_quality_melted, palette='viridis')
        plt.title('Calidad Promedio de Intervenciones Correctas del Bot (True Positives) por Modelo', fontsize=14)
        plt.ylabel('Puntuación Promedio (1-5)')
        plt.ylim(0, 5)
        plt.xticks(rotation=45, ha='right')
        plt.grid(axis='y', linestyle='--', alpha=0.7)
        plt.tight_layout()
        plt.savefig(os.path.join(PLOTS_OUTPUT_DIR, 'avg_intervention_quality.png'))
        plt.close()
        print("Gráfica 'avg_intervention_quality.png' generada.")
    else:
        print("No hay True Positives para generar la gráfica de calidad de intervenciones.")
else:
    print("No hay datos de True Positives para generar la gráfica de calidad de intervenciones.")


# 5. Métricas de Intervención (Precision, Recall, F1-Score)
if not df_con_bot.empty and df_con_bot[['precision', 'recall', 'f1_score']].sum().sum() > 0:
    # Agrupar por bot_llm_choice para ver diferencias entre bots
    intervention_metrics_grouped = df_con_bot.groupby('bot_llm_choice')[['precision', 'recall', 'f1_score']].mean().reset_index()
    
    if not intervention_metrics_grouped.empty:
        # Guardar como CSV
        intervention_metrics_grouped.to_csv(os.path.join(SUMMARY_OUTPUT_DIR, 'avg_precision_recall_f1_by_bot_llm.csv'), index=False)
        print(f"Resumen 'avg_precision_recall_f1_by_bot_llm.csv' guardado en {SUMMARY_OUTPUT_DIR}")

        # Reestructurar para seaborn barplot
        intervention_metrics_melted = intervention_metrics_grouped.melt(id_vars='bot_llm_choice', var_name='Metric', value_name='Score')

        plt.figure(figsize=(10, 6))
        sns.barplot(x='bot_llm_choice', y='Score', hue='Metric', data=intervention_metrics_melted, palette='muted')
        plt.title('Métricas de Rendimiento de Intervención por Modelo de Bot (Promedio)', fontsize=14)
        plt.ylabel('Puntuación')
        plt.ylim(0, 1) # Precision, Recall, F1-Score están entre 0 y 1
        plt.grid(axis='y', linestyle='--', alpha=0.7)
        plt.tight_layout()
        plt.savefig(os.path.join(PLOTS_OUTPUT_DIR, 'intervention_performance_metrics.png'))
        plt.close()
        print("Gráfica 'intervention_performance_metrics.png' generada.")
    else:
        print("No hay datos suficientes para generar la gráfica de métricas de intervención agrupadas por bot.")
else:
    print("No hay datos de intervenciones con bot para generar la gráfica de métricas de rendimiento.")


# 6. Tiempo de Procesamiento Promedio de Intervenciones
if not df_con_bot.empty and df_con_bot['avg_processing_time_seconds'].sum() > 0:
    # Asegurarse de filtrar por total_interventions > 0 para promedios significativos
    df_processing_time = df_con_bot[df_con_bot['total_interventions'] > 0]

    if not df_processing_time.empty:
        # Si quisieras, podrías guardar los promedios de tiempo de procesamiento por bot a CSV así:
        # processing_time_summary = df_processing_time.groupby('bot_llm_choice')['avg_processing_time_seconds'].mean().reset_index()
        # processing_time_summary.to_csv(os.path.join(SUMMARY_OUTPUT_DIR, 'avg_processing_time_by_bot_llm.csv'), index=False)
        # print(f"Resumen 'avg_processing_time_by_bot_llm.csv' guardado en {SUMMARY_OUTPUT_DIR}")
        
        plt.figure(figsize=(8, 6))
        sns.barplot(x='bot_llm_choice', y='avg_processing_time_seconds', data=df_processing_time, palette='cividis', estimator=pd.Series.mean, ci='sd')
        plt.title('Tiempo Promedio de Procesamiento por Intervención del Bot', fontsize=14)
        plt.ylabel('Tiempo (segundos)')
        plt.xlabel('Modelo LLM del Bot')
        plt.grid(axis='y', linestyle='--', alpha=0.7)
        plt.tight_layout()
        plt.savefig(os.path.join(PLOTS_OUTPUT_DIR, 'avg_processing_time.png'))
        plt.close()
        print("Gráfica 'avg_processing_time.png' generada.")
    else:
        print("No hay intervenciones registradas para generar la gráfica de tiempo de procesamiento.")
else:
    print("No hay datos de tiempo de procesamiento para generar la gráfica de tiempo promedio de intervenciones.")

print(f"\nAnálisis de datos finalizado.")
print(f"Verifique el directorio '{PLOTS_OUTPUT_DIR}' para las gráficas.")
print(f"Verifique el directorio '{SUMMARY_OUTPUT_DIR}' para los CSV de resúmenes (ahora con encabezados y etiquetas corregidos).")