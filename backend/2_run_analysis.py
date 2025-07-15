import pandas as pd
import numpy as np
from scipy.stats import ttest_ind, pearsonr
from itertools import product
import os
import matplotlib.pyplot as plt
import seaborn as sns

# --- CONFIGURACIÓN ---
SIMULATIONS_DIR = "simulated_conversations"
METRICS_FILE = os.path.join(SIMULATIONS_DIR, "raw_metrics_summary.csv")
FINAL_DATA_FILE = os.path.join(SIMULATIONS_DIR, "final_data_with_icca.csv")
STATISTICAL_SUMMARY_FILE = os.path.join(SIMULATIONS_DIR, "statistical_summary.csv")
CORRELATION_SUMMARY_FILE = os.path.join(SIMULATIONS_DIR, "correlation_summary.csv")
PLOTS_DIR = os.path.join(SIMULATIONS_DIR, "analysis_plots")
os.makedirs(PLOTS_DIR, exist_ok=True)

# Configuración de estilo para los gráficos
sns.set_theme(style="whitegrid", palette="viridis")

def format_p_value(p):
    """Formatea el p-value para una presentación académica estándar."""
    if p < 0.001:
        return "< .001"
    else:
        return f"{p:.3f}"

def perform_analysis():
    """
    Lee métricas, calcula ICCA, realiza análisis estadístico, genera gráficos y guarda informes detallados.
    """
    if not os.path.exists(METRICS_FILE):
        print(f"Error: El archivo '{METRICS_FILE}' no existe. Ejecuta '1_calculate_metrics.py' primero.")
        return

    df = pd.read_csv(METRICS_FILE)
    print(f"Cargados {len(df)} registros desde '{METRICS_FILE}'.")

    # --- CÁLCULO DEL ICCA ---
    metrics_for_icca = ['emotional_charge', 'syntactic_complexity', 'dialectic_density']
    for metric in metrics_for_icca:
        mean, std = df[metric].mean(), df[metric].std()
        df[f'z_{metric}'] = (df[metric] - mean) / std if std > 0 else 0
    df['ICCA'] = df[[f'z_{metric}' for metric in metrics_for_icca]].mean(axis=1)
    
    df.to_csv(FINAL_DATA_FILE, index=False, float_format='%.4f')
    print(f"Datos finales con ICCA guardados en: {FINAL_DATA_FILE}")

    # --- ANÁLISIS DE VALIDACIÓN DE CONSTRUCTO DEL ICCA ---
    print("\n" + "="*60)
    print("VALIDACIÓN DE CONSTRUCTO DEL ICCA")
    print("="*60)
    
    corr_matrix = df[metrics_for_icca].corr()
    print("\nMatriz de Correlación de Pearson entre los Proxies:")
    print(corr_matrix.to_string(float_format="%.3f"))
    
    plt.figure(figsize=(8, 6))
    sns.heatmap(corr_matrix, annot=True, cmap='viridis', fmt=".3f", linewidths=.5)
    plt.title('Matriz de Correlación de los Proxies del ICCA')
    plt.savefig(os.path.join(PLOTS_DIR, 'ICCA_correlation_heatmap.png'))
    plt.close()
    print("\nHeatmap de correlación guardado en 'analysis_plots/'.")

    print("\nAnálisis de Correlación Bivariado (Pearson's r):")
    correlation_results = []
    pairs = [
        ('emotional_charge', 'syntactic_complexity'),
        ('emotional_charge', 'dialectic_density'),
        ('syntactic_complexity', 'dialectic_density')
    ]
    for var1, var2 in pairs:
        clean_df = df[[var1, var2]].dropna()
        if len(clean_df) > 2:
            r, p_value = pearsonr(clean_df[var1], clean_df[var2])
            correlation_results.append({
                'Variable_1': var1, 'Variable_2': var2,
                'Pearson_r': r, 'p_value': p_value
            })
            print(f"- {var1} vs {var2}: r = {r:.3f}, p = {format_p_value(p_value)} {'*' if p_value < 0.05 else ''}")
        else:
            print(f"- {var1} vs {var2}: No hay suficientes datos para la correlación.")

    if correlation_results:
        corr_df = pd.DataFrame(correlation_results)
        corr_df.to_csv(CORRELATION_SUMMARY_FILE, index=False, float_format='%.4f')
        print(f"\nResumen de correlaciones guardado en: {CORRELATION_SUMMARY_FILE}")
    
    # --- ANÁLISIS ESTADÍSTICO PRINCIPAL Y GENERACIÓN DE INFORME ---
    print("\n" + "="*60)
    print("GENERANDO INFORME ESTADÍSTICO Y GRÁFICOS")
    print("="*60)

    statistical_results = []
    scenarios = df['scenario'].unique()
    
    for scenario in scenarios:
        print(f"\nGenerando gráficos para el escenario '{scenario}'...")
        subset_df_scenario = df[df['scenario'] == scenario]
        
        # Gráficos (sin cambios)
        plt.figure(figsize=(12, 7)); sns.barplot(data=subset_df_scenario, x='bot_llm', y='ICCA', hue='condition', palette="mako", capsize=.1); plt.title(f'Impacto del Bot en ICCA - Escenario: {scenario.replace("_", " ").title()}'); plt.xlabel('Configuración del Bot (N/A para Control)'); plt.ylabel('ICCA (z-score promedio)'); plt.legend(title='Condición'); plt.tight_layout(); plt.savefig(os.path.join(PLOTS_DIR, f'ICCA_comparison_{scenario}.png')); plt.close()
        df_con_bot = subset_df_scenario[subset_df_scenario['condition'] == 'bot']
        if not df_con_bot.empty:
            plt.figure(figsize=(10, 6)); sns.boxplot(data=df_con_bot, x='bot_llm', y='avg_processing_time_s', palette="rocket"); plt.title(f'Latencia de Intervención del Bot - Escenario: {scenario.replace("_", " ").title()}'); plt.xlabel('Modelo de LLM del Bot'); plt.ylabel('Tiempo Promedio de Procesamiento (s)'); plt.tight_layout(); plt.savefig(os.path.join(PLOTS_DIR, f'Latency_comparison_{scenario}.png')); plt.close()
        print(f"Gráficos para '{scenario}' generados.")

        # Desglose Estadístico
        user_llms_in_scenario = subset_df_scenario['user_llm'].unique()
        for user_llm in user_llms_in_scenario:
            group_bot = subset_df_scenario[(subset_df_scenario['condition'] == 'bot') & (subset_df_scenario['user_llm'] == user_llm)]
            group_ctrl = subset_df_scenario[(subset_df_scenario['condition'] == 'ctrl') & (subset_df_scenario['user_llm'] == user_llm)]
            
            if group_bot.empty or group_ctrl.empty: continue

            bot_llm_name = group_bot['bot_llm'].iloc[0]
            
            # Estadísticas ICCA
            stats_bot_icca = {'mean': group_bot['ICCA'].mean(), 'std': group_bot['ICCA'].std(), 'n': len(group_bot)}
            stats_ctrl_icca = {'mean': group_ctrl['ICCA'].mean(), 'std': group_ctrl['ICCA'].std(), 'n': len(group_ctrl)}
            t_stat_icca, p_value_icca = ttest_ind(group_bot['ICCA'], group_ctrl['ICCA'], equal_var=False, nan_policy='omit')
            
            statistical_results.append({
                'escenario': scenario, 'user_llm': user_llm, 'bot_llm': bot_llm_name,
                'metrica': 'ICCA', 'media_exp': stats_bot_icca['mean'], 'std_exp': stats_bot_icca['std'], 'n_exp': stats_bot_icca['n'],
                'media_ctrl': stats_ctrl_icca['mean'], 'std_ctrl': stats_ctrl_icca['std'], 'n_ctrl': stats_ctrl_icca['n'],
                't_statistic': t_stat_icca, 'p_value': p_value_icca
            })
            
            # Estadísticas Latencia
            if not group_bot.empty:
                 stats_bot_latency = {'mean': group_bot['avg_processing_time_s'].mean(), 'std': group_bot['avg_processing_time_s'].std(), 'n': group_bot['avg_processing_time_s'].count()}
                 statistical_results.append({
                    'escenario': scenario, 'user_llm': user_llm, 'bot_llm': bot_llm_name,
                    'metrica': 'Latencia (s)', 'media_exp': stats_bot_latency['mean'], 'std_exp': stats_bot_latency['std'], 'n_exp': stats_bot_latency['n'],
                    'media_ctrl': np.nan, 'std_ctrl': np.nan, 'n_ctrl': 0,
                    't_statistic': np.nan, 'p_value': np.nan
                 })

    # Crear y guardar el DataFrame del informe estadístico
    if statistical_results:
        summary_df = pd.DataFrame(statistical_results)
        # Formatear el p-value para una mejor presentación
        summary_df['p_value_formatted'] = summary_df['p_value'].apply(lambda p: format_p_value(p) if pd.notna(p) else 'na')
        summary_df['significativo_p<0.05'] = summary_df['p_value'] < 0.05
        
        summary_df.to_csv(STATISTICAL_SUMMARY_FILE, index=False, float_format='%.4f')
        print(f"\nInforme estadístico completo guardado en: {STATISTICAL_SUMMARY_FILE}")
        
        # Imprimir un resumen en la consola para una revisión rápida
        print("\n--- RESUMEN DE PRUEBAS T (ICCA) ---")
        print(summary_df[summary_df['metrica'] == 'ICCA'][[
            'escenario', 'user_llm', 'bot_llm', 't_statistic', 'p_value_formatted', 'significativo_p<0.05'
        ]].rename(columns={'p_value_formatted': 'p-value'}).to_string(index=False))

if __name__ == "__main__":
    perform_analysis()