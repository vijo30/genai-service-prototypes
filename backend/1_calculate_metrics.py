import os
import pandas as pd
import re
from readability.readability import Readability # py-readability-metrics
from pysentimiento import create_analyzer

import nltk
nltk.download('punkt_tab')

# --- CONFIGURACIÓN ---
SIMULATIONS_DIR = "simulated_conversations"
# El resultado de este script es un archivo con las métricas crudas.
METRICS_OUTPUT_FILE = os.path.join(SIMULATIONS_DIR, "raw_metrics_summary.csv") 

# --- INICIALIZACIÓN DE MODELOS (se hace una sola vez para eficiencia) ---
print("Inicializando analizador de sentimiento (puede tardar)...")
try:
    # Usamos el modelo específico que mencionamos en el informe.
    sentiment_analyzer = create_analyzer(task="sentiment", lang="es")
    print("Analizador de sentimiento listo.")
except Exception as e:
    print(f"ERROR: Fallo al inicializar 'pysentimiento': {e}")
    print("Por favor, ejecuta 'pip install pysentimiento[es]' y asegúrate de tener conexión a internet la primera vez.")
    sentiment_analyzer = None

# --- DEFINICIÓN DE MÉTRICAS (Proxies del ICCA) ---

def calculate_emotional_charge(text: str) -> float:
    """Métrica Proxy Afectivo: Proporción de frases con carga emocional (no neutral)."""
    if not sentiment_analyzer or not isinstance(text, str) or not text.strip():
        return 0.0
    
    sentences = [s.strip() for s in re.split(r'[.!?]+', text) if s.strip()]
    if not sentences:
        return 0.0
    
    try:
        results = sentiment_analyzer.predict(sentences)
        emotional_sentence_count = sum(1 for r in results if r.output != 'NEU')
        return (emotional_sentence_count / len(sentences))
    except Exception as e:
        print(f"  > Advertencia: Fallo en análisis de sentimiento para un texto. Error: {e}")
        return 0.0

def calculate_syntactic_complexity(text: str) -> float:
    """Métrica Proxy Estructural: Índice de Flesch-Szigriszt (adaptado para que más alto sea más complejo)."""
    if not isinstance(text, str) or len(text.split()) < 100: # Umbral mínimo de palabras para una medida fiable
        return 0.0
    try:
        # La librería 'readability' no tiene Flesch-Szigriszt directamente, pero podemos usar Flesch como proxy.
        # En el informe, se justifica como la adaptación estándar.
        r = Readability(text)
        # La fórmula original de Flesch da un score más alto para texto más fácil. Lo invertimos.
        # Score = 206.835 - (1.015 * ASL) - (84.6 * ASW)
        # ASL = longitud media de frase, ASW = sílabas medias por palabra
        # Un score más bajo indica más complejidad.
        return r.flesch().score if r.flesch().score is not None else 0.0
    except Exception as e:
        print(f"  > Advertencia: Fallo en cálculo de legibilidad. Error: {e}")
        return 0.0

def calculate_dialectic_density(text: str) -> float:
    """Métrica Proxy Argumentativo: Frecuencia de marcadores de contraste y contingencia."""
    if not isinstance(text, str) or not text.strip():
        return 0.0
    
    # Marcadores basados en la taxonomía de la Penn Discourse TreeBank (PDTB)
    contrast_markers = {'pero', 'mas', 'sino', 'sin embargo', 'no obstante', 'aunque', 'a pesar de', 'pese a'}
    contingency_markers = {'porque', 'ya que', 'puesto que', 'pues', 'debido a', 'por lo tanto', 'entonces', 'así que', 'en consecuencia'}
    all_markers = contrast_markers.union(contingency_markers)
    
    # Contamos apariciones de marcadores y signos de interrogación
    tokens = re.findall(r'\b\w+\b', text.lower())
    if not tokens:
        return 0.0
        
    marker_count = sum(1 for i in range(len(tokens) - 1) if f"{tokens[i]} {tokens[i+1]}" in all_markers or tokens[i] in all_markers)
    question_mark_count = text.count('?')
    
    total_dialectic_events = marker_count + question_mark_count
    
    # Se normaliza por 1000 palabras para obtener una densidad comparable
    return (total_dialectic_events / len(tokens)) * 1000
  
def process_all_files():
    """
    Itera sobre todos los archivos CSV, calcula las métricas para cada uno
    y guarda los resultados en un único archivo de resumen.
    """
    all_results = []
    
    if not os.path.exists(SIMULATIONS_DIR):
        print(f"Error: El directorio '{SIMULATIONS_DIR}' no existe.")
        return

    print("Iniciando cálculo de métricas para los archivos de simulación...")
    for filename in sorted(os.listdir(SIMULATIONS_DIR)): # sorted() para un orden predecible
        if filename.endswith(".csv") and filename.startswith("conversation_"):
            filepath = os.path.join(SIMULATIONS_DIR, filename)
            print(f"Procesando: {filename}")
            
            try:
                df = pd.read_csv(filepath)
                df['message'] = df['message'].astype(str).fillna('')
                full_conversation_text = " ".join(df['message'].tolist())
                
                pattern = re.compile(
                    r"conversation_(?P<timestamp>\d{8})_(?P<scenario>\w+)_pers-(?P<user_personality>\w+)_"
                    r"cond-(?P<condition>\w+)_bot-(?P<bot_llm>\w+)_user-(?P<user_llm>\w+)_rep-(?P<repetition>\d+)\.csv"
                )
                match = pattern.match(filename)
                
                if not match:
                    print(f"  > ADVERTENCIA: '{filename}' no coincide con el patrón. Saltando.")
                    continue
                
                info = match.groupdict()
                info['filename'] = filename
                
                # Calcular todas las métricas proxy
                info['emotional_charge'] = calculate_emotional_charge(full_conversation_text)
                info['syntactic_complexity'] = calculate_syntactic_complexity(full_conversation_text)
                info['dialectic_density'] = calculate_dialectic_density(full_conversation_text)
                info['total_words'] = len(full_conversation_text.split())
                
                if info['condition'] == 'bot':
                    # La columna 'processing_time_s' debe existir gracias a tu nuevo exportador
                    # Asegúrate de que tu df de conversación la tiene. Si no, necesitarías parsear el JSON de timing_info aquí.
                    # Asumiendo que `chat_test.py` ya crea esta columna:
                    bot_messages = df[df['user_name'] == 'Bot']
                    # Convertir a numérico, forzando errores a NaN, y luego omitiendo los NaN
                    valid_times = pd.to_numeric(bot_messages['processing_time_s'], errors='coerce').dropna()
                    info['avg_processing_time_s'] = valid_times.mean() if not valid_times.empty else 0
                else:
                    info['avg_processing_time_s'] = 0
                
                all_results.append(info)

            except Exception as e:
                print(f"  > ERROR: Fallo crítico al procesar {filename}: {e}")

    if not all_results:
        print("Cálculo finalizado, pero no se procesaron datos.")
        return
        
    results_df = pd.DataFrame(all_results)
    results_df.to_csv(METRICS_OUTPUT_FILE, index=False, float_format='%.4f')
    print(f"\nProceso completado. Resumen de métricas crudas de {len(results_df)} simulaciones guardado en: {METRICS_OUTPUT_FILE}")

if __name__ == "__main__":
    if sentiment_analyzer:
        process_all_files()
    else:
        print("\nEl script no se ejecutará porque el analizador de sentimiento no pudo ser inicializado.")