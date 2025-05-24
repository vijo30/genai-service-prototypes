import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os

OUTPUT_DIR = "simulated_conversations"
STATISTICS_FILE = os.path.join(OUTPUT_DIR, "evaluation_statistics_detailed.csv")
EVALUATION_RESULTS_FILE = os.path.join(OUTPUT_DIR, "evaluation_results.csv")

def plot_bar_chart_means(df_raw_results):
    """
    Genera un gráfico de barras comparando las medias de las métricas
    entre conversaciones con y sin bot, incluyendo barras de error.
    Utiliza los datos brutos y deja que Seaborn calcule las medias y STDs.
    """
    metrics = ['coherencia_general', 'tono_general', 'pertinencia_general', 'reflexion_general']

    # Melt the raw results to have a single 'value' column for all metrics
    df_melted = pd.melt(df_raw_results,
                        id_vars=['con_bot', 'caso'], # Keep 'caso' if you want to differentiate
                        value_vars=metrics,
                        var_name='metrica_raw',
                        value_name='puntuacion')

    # Clean metric names for plotting
    df_melted['metrica'] = df_melted['metrica_raw'].str.replace('_general', '').str.capitalize()

    plt.figure(figsize=(12, 7))
    sns.barplot(
        x='metrica',
        y='puntuacion',
        hue='con_bot',
        data=df_melted,
        errorbar='sd', # Use 'sd' to display standard deviation as error bars
        capsize=0.1,
        palette='viridis'
    )
    plt.title('Comparación de Métricas de Evaluación (Media y Desviación Estándar)', fontsize=16)
    plt.xlabel('Métrica de Evaluación', fontsize=12)
    plt.ylabel('Puntuación Media (1-5)', fontsize=12)
    plt.xticks(rotation=45, ha='right', fontsize=10)
    plt.yticks(fontsize=10)
    plt.ylim(0, 5) # Asegura que el eje Y vaya de 0 a 5
    plt.legend(title='Con Bot', fontsize=10, title_fontsize=12, loc='upper right')
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, 'mean_metrics_comparison.png'))
    plt.show()

def plot_box_plots(df):
    """
    Genera gráficos de caja para cada métrica de evaluación,
    comparando las distribuciones con y sin bot.
    """
    metrics = ['coherencia_general', 'tono_general', 'pertinencia_general', 'reflexion_general']

    plt.figure(figsize=(14, 10))
    for i, metric in enumerate(metrics):
        plt.subplot(2, 2, i + 1)
        sns.boxplot(x='con_bot', y=metric, data=df, palette='plasma')
        plt.title(f'Distribución de {metric.replace("_general", "").capitalize()}', fontsize=14)
        plt.xlabel('Con Bot', fontsize=12)
        plt.ylabel('Puntuación (1-5)', fontsize=12)
        plt.xticks(ticks=[0, 1], labels=['Sin Bot', 'Con Bot'], fontsize=10)
        plt.yticks(fontsize=10)
        plt.ylim(1, 5) # Asegura que el eje Y vaya de 1 a 5
        plt.grid(axis='y', linestyle='--', alpha=0.7)
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, 'metric_distributions_boxplot.png'))
    plt.show()

def plot_bot_interventions_correlation():
    """
    Genera gráficos de dispersión para explorar la correlación entre
    el número de intervenciones del bot y cada métrica de evaluación.
    Solo se grafica para las conversaciones 'con_bot'.
    """
    try:
        df_raw_results = pd.read_csv(EVALUATION_RESULTS_FILE)
        for col in ['coherencia_general', 'tono_general', 'pertinencia_general', 'reflexion_general', 'bot_interventions']:
             df_raw_results[col] = pd.to_numeric(df_raw_results[col], errors='coerce')
    except FileNotFoundError:
        print(f"Advertencia: No se encontró '{EVALUATION_RESULTS_FILE}', no se generará el gráfico de correlación de intervenciones del bot.")
        return
    except Exception as e:
        print(f"Error al cargar '{EVALUATION_RESULTS_FILE}' para el gráfico de correlación: {e}")
        return

    df_with_bot = df_raw_results[df_raw_results['con_bot'] == True].copy()
    
    if df_with_bot.empty or 'bot_interventions' not in df_with_bot.columns:
        print("No hay datos de conversaciones con bot o la columna 'bot_interventions' no está presente para graficar la correlación.")
        return

    metrics = ['coherencia_general', 'tono_general', 'pertinencia_general', 'reflexion_general']

    plt.figure(figsize=(14, 10))
    for i, metric in enumerate(metrics):
        plt.subplot(2, 2, i + 1)
        sns.scatterplot(x='bot_interventions', y=metric, data=df_with_bot,
                        hue='caso', palette='deep', s=100, alpha=0.8)
        plt.title(f'Intervenciones del Bot vs. {metric.replace("_general", "").capitalize()}', fontsize=14)
        plt.xlabel('Número de Intervenciones del Bot', fontsize=12)
        plt.ylabel(f'{metric.replace("_general", "").capitalize()} (Puntuación)', fontsize=12)
        plt.xticks(fontsize=10)
        plt.yticks(fontsize=10)
        plt.grid(axis='both', linestyle='--', alpha=0.7)
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, 'bot_interventions_correlation.png'))
    plt.show()


if __name__ == "__main__":
    try:
        # Cargamos el archivo de estadísticas detalladas (df_stats is still useful for debugging or other uses)
        df_stats = pd.read_csv(STATISTICS_FILE)
    except FileNotFoundError:
        print(f"Error: No se encontró el archivo '{STATISTICS_FILE}'. Asegúrate de que `analyze_evaluation_results.py` se haya ejecutado primero.")
        exit()

    # Cargar los resultados brutos para los boxplots y barplots
    try:
        df_raw_results = pd.read_csv(EVALUATION_RESULTS_FILE)
        # Asegurarse de que las columnas de evaluación son numéricas
        for col in ['coherencia_general', 'tono_general', 'pertinencia_general', 'reflexion_general', 'bot_interventions']:
             df_raw_results[col] = pd.to_numeric(df_raw_results[col], errors='coerce')
    except FileNotFoundError:
        print(f"Error: No se encontró el archivo '{EVALUATION_RESULTS_FILE}'. Asegúrate de que `evaluator_agent.py` se haya ejecutado primero.")
        exit()
    except Exception as e:
        print(f"Error al cargar '{EVALUATION_RESULTS_FILE}': {e}")
        exit()

    print("Generando gráficos de resultados...")

    # Gráfico 1: Comparación de medias con barras de error
    # Pass the raw results to the function, letting seaborn handle aggregation
    plot_bar_chart_means(df_raw_results)

    # Gráfico 2: Gráficos de caja
    plot_box_plots(df_raw_results)

    # Gráfico 3: Correlación con intervenciones del bot
    plot_bot_interventions_correlation()

    print("Generación de gráficos finalizada. Revisa la carpeta 'simulated_conversations'.")