# analyze_evaluation_results.py

import pandas as pd
import numpy as np
import os

OUTPUT_DIR = "simulated_conversations"
EVALUATION_RESULTS_FILE = os.path.join(OUTPUT_DIR, "evaluation_results.csv")
STATISTICS_OUTPUT_FILE = os.path.join(OUTPUT_DIR, "evaluation_statistics_detailed.csv")
BOT_USERNAME = "Bot"  # Define el nombre de usuario del bot

def calculate_statistics(df, group_column):
    """Calcula las estadísticas (media, desviación estándar, mediana) por grupo."""
    grouped = df.groupby(group_column)
    statistics = grouped[['coherencia_general', 'tono_general', 'pertinencia_general', 'reflexion_general']].agg(
        ['mean', 'std', 'median']
    )
    statistics.columns = ['_'.join(col).strip() for col in statistics.columns]
    statistics = statistics.reset_index()
    return statistics

if __name__ == "__main__":
    try:
        df_results = pd.read_csv(EVALUATION_RESULTS_FILE)
    except FileNotFoundError:
        print(f"Error: No se encontró el archivo '{EVALUATION_RESULTS_FILE}'. Asegúrate de que `evaluator_agent.py` se haya ejecutado primero.")
        exit()

    # Añadir una columna para contar las intervenciones del bot
    df_results['bot_interventions'] = 0
    for index, row in df_results.iterrows():
        filepath = os.path.join(OUTPUT_DIR, row['filename'])
        try:
            conversation_df = pd.read_csv(filepath)
            bot_message_count = conversation_df[conversation_df['user_name'] == BOT_USERNAME].shape[0]
            df_results.at[index, 'bot_interventions'] = bot_message_count
        except Exception as e:
            print(f"Error al leer el archivo de conversación {row['filename']}: {e}")
            df_results.at[index, 'bot_interventions'] = -1  # Indica error

    # Separar resultados para conversaciones con bot y sin bot
    df_con_bot = df_results[df_results['con_bot'] == True]
    df_sin_bot = df_results[df_results['con_bot'] == False]

    # Calcular estadísticas para conversaciones con bot
    stats_con_bot = calculate_statistics(df_con_bot, 'caso')
    stats_con_bot['con_bot'] = True
    stats_con_bot['avg_bot_interventions'] = df_con_bot.groupby('caso')['bot_interventions'].mean().values

    # Calcular estadísticas para conversaciones sin bot
    stats_sin_bot = calculate_statistics(df_sin_bot, 'caso')
    stats_sin_bot['con_bot'] = False
    stats_sin_bot['avg_bot_interventions'] = 0  # No hay intervenciones del bot

    # Combinar las estadísticas
    df_statistics = pd.concat([stats_con_bot, stats_sin_bot], ignore_index=True)

    # Guardar las estadísticas detalladas en un nuevo archivo CSV
    df_statistics.to_csv(STATISTICS_OUTPUT_FILE, index=False)

    print(f"\n--- Se calcularon las estadísticas de evaluación detalladas y se guardaron en: {STATISTICS_OUTPUT_FILE} ---")