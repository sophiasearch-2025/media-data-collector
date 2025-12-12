import json
import os
from datetime import datetime

from logger import logs_operations
from logger.queue_key_config import QueueKeyConfig as Config


class MetricsEngine:
    def __init__(self, output_dir="metrics"):
        self._output_dir = output_dir
        self._scraping_key = Config.KEY_SCRAPING_RESULTS

    def calculate_scraping_metrics(self):
        try:
            scraping_logs = logs_operations.get_logs_list(self._scraping_key)

            # Agrupar logs por medio
            logs_por_medio = {}
            for log in scraping_logs:
                medio = log.get("medio", "unknown")
                if medio not in logs_por_medio:
                    logs_por_medio[medio] = []
                logs_por_medio[medio].append(log)

            # Leer métricas existentes o crear diccionario vacío
            metrics_file = os.path.join(self._output_dir, "scraper_metrics.json")
            existing_metrics = {}

            if os.path.exists(metrics_file):
                try:
                    with open(metrics_file, "r", encoding="utf-8") as f:
                        existing_metrics = json.load(f)
                except Exception:
                    existing_metrics = {}

            # Calcular métricas para cada medio
            for medio, medio_logs in logs_por_medio.items():
                # Contar URLs únicos (para evitar contar duplicados)
                # Usar un diccionario para guardar el último status de cada URL única
                url_status = {}
                for l in medio_logs:
                    url = l.get("url")
                    status = l.get("status")
                    if url:
                        url_status[url] = status  # Sobrescribe con el último log

                # total es el número de URLs únicos procesados
                total = len(url_status)
                exitos = sum(1 for status in url_status.values() if status == "success")
                fallos = total - exitos

                starts = []
                finishes = []
                dur_ms = []

                for l in medio_logs:
                    st = l.get("starting_time")
                    ft = l.get("finishing_time")
                    dm = l.get("duration_ms")

                    if st:
                        try:
                            starts.append(datetime.strptime(st, "%Y-%m-%d %H:%M:%S"))
                        except Exception:
                            pass
                    if ft:
                        try:
                            finishes.append(datetime.strptime(ft, "%Y-%m-%d %H:%M:%S"))
                        except Exception:
                            pass
                    if dm:
                        try:
                            dur_ms.append(float(dm))
                        except Exception:
                            pass

                if starts and finishes:
                    duracion_segundos = (max(finishes) - min(starts)).total_seconds()
                elif dur_ms:
                    duracion_segundos = sum(dur_ms) / 1000.0
                else:
                    duracion_segundos = 0

                porcentaje = (exitos / total) * 100 if total > 0 else 0
                noticias_por_minuto = (
                    exitos / (duracion_segundos / 60) if duracion_segundos > 0 else 0
                )
                tiempo_promedio = (
                    (sum(dur_ms) / 1000.0) / exitos if (exitos > 0 and dur_ms) else 0
                )

                # Calcular publicaciones por fecha para este medio
                publicaciones_por_fecha = {}
                for l in medio_logs:
                    fecha_pub = l.get("fecha_publicacion")
                    if fecha_pub and fecha_pub.strip():
                        try:
                            fecha_normalizada = None

                            # Primero: extraer solo la parte de fecha (antes del |) del formato "Día DD mes de YYYY | HH:MM"
                            fecha_parte = (
                                fecha_pub.split("|")[0].strip()
                                if "|" in fecha_pub
                                else fecha_pub.strip()
                            )

                            # Mapa de nombres de días y meses en español
                            dias_es = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
                            meses_es = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio',
                                       'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre']
                            
                            # Intentar parsear formato ISO 8601 (de La Tercera): 2025-05-19T21:22:48.24Z
                            if "T" in fecha_parte and ("Z" in fecha_parte or "+" in fecha_parte or "-" in fecha_parte[-6:]):
                                try:
                                    # Remover microsegundos si existen
                                    if "." in fecha_parte:
                                        fecha_parte_limpia = fecha_parte.split(".")[0]
                                    else:
                                        fecha_parte_limpia = fecha_parte.rstrip("Z")
                                    
                                    fecha_dt = datetime.fromisoformat(fecha_parte_limpia.rstrip("Z"))
                                    # Convertir a formato español: "Día DD mes de YYYY"
                                    dia_semana = dias_es[fecha_dt.weekday()]
                                    mes_nombre = meses_es[fecha_dt.month - 1]
                                    fecha_normalizada = f"{dia_semana} {fecha_dt.day:02d} {mes_nombre} de {fecha_dt.year}"
                                except (ValueError, AttributeError):
                                    pass
                            
                            # Si no es ISO, intentar parsear formatos estándar
                            if not fecha_normalizada:
                                for fmt in ["%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d"]:
                                    try:
                                        fecha_dt = datetime.strptime(fecha_parte, fmt)
                                        # Convertir a formato español
                                        dia_semana = dias_es[fecha_dt.weekday()]
                                        mes_nombre = meses_es[fecha_dt.month - 1]
                                        fecha_normalizada = f"{dia_semana} {fecha_dt.day:02d} {mes_nombre} de {fecha_dt.year}"
                                        break
                                    except ValueError:
                                        continue

                            # Si no coincidió con formatos conocidos, usar la parte antes del | como está
                            if not fecha_normalizada:
                                fecha_normalizada = fecha_parte

                            publicaciones_por_fecha[fecha_normalizada] = (
                                publicaciones_por_fecha.get(fecha_normalizada, 0) + 1
                            )
                        except Exception:
                            pass

                # Actualizar métricas solo para este medio
                existing_metrics[medio] = {
                    "total_urls_procesadas": total,
                    "scrape_exitosos": exitos,
                    "scrape_fallidos": fallos,
                    "porcentaje_exito": round(porcentaje, 2),
                    "duracion_segundos": round(duracion_segundos, 2),
                    "noticias_por_minuto": round(noticias_por_minuto, 3),
                    "tiempo_promedio_scrape": round(tiempo_promedio, 3),
                    "publicaciones_por_fecha": dict(
                        sorted(publicaciones_por_fecha.items())
                    ),
                }

            # CORRECCIÓN: Verificar con scraper_progress.json (más confiable)
            # Si tiene números más altos, usarlos (algunos logs pueden perderse en Redis)
            progress_file = os.path.join(self._output_dir, "scraper_progress.json")
            if os.path.exists(progress_file):
                try:
                    with open(progress_file, "r", encoding="utf-8") as f:
                        all_progress = json.load(f)
                    
                    # Iterar por cada medio en existing_metrics
                    for medio in existing_metrics:
                        progress = all_progress.get(medio, {})
                        
                        total_progress = progress.get("total_articulos_exitosos", 0) + progress.get("total_articulos_fallidos", 0)
                        
                        # Si scraper_progress tiene más artículos, usar esos números
                        # (significa que algunos logs no llegaron a Redis)
                        if total_progress > 0:
                            redis_total = existing_metrics[medio]["total_urls_procesadas"]
                            
                            # Si Redis tiene menos que progress, progress es más confiable
                            if total_progress > redis_total:
                                # Calcular duración desde start_time
                                start_time_str = progress.get("start_time")
                                last_update_str = progress.get("ultima_actualizacion")
                                
                                if start_time_str and last_update_str:
                                    try:
                                        start_dt = datetime.strptime(start_time_str, "%Y-%m-%d %H:%M:%S")
                                        end_dt = datetime.strptime(last_update_str, "%Y-%m-%d %H:%M:%S")
                                        duracion_real = (end_dt - start_dt).total_seconds()
                                        
                                        # Continuar procesando este medio específico:
                                        print(f"[logger] Corrigiendo métricas de '{medio}': Redis tiene {redis_total}, scraper_progress tiene {total_progress}")
                                        
                                        exitos = progress.get("total_articulos_exitosos", 0)
                                        fallos = progress.get("total_articulos_fallidos", 0)
                                        porcentaje = (exitos / total_progress * 100) if total_progress > 0 else 0
                                        noticias_por_minuto = (total_progress / (duracion_real / 60)) if duracion_real > 0 else 0
                                        tiempo_promedio = progress.get("duracion_promedio_ms", 0) / 1000.0
                                        
                                        existing_metrics[medio]["total_urls_procesadas"] = total_progress
                                        existing_metrics[medio]["scrape_exitosos"] = exitos
                                        existing_metrics[medio]["scrape_fallidos"] = fallos
                                        existing_metrics[medio]["porcentaje_exito"] = round(porcentaje, 2)
                                        existing_metrics[medio]["duracion_segundos"] = round(duracion_real, 2)
                                        existing_metrics[medio]["noticias_por_minuto"] = round(noticias_por_minuto, 3)
                                        existing_metrics[medio]["tiempo_promedio_scrape"] = round(tiempo_promedio, 3)
                                    except Exception as e:
                                        print(f"[logger] Error parseando fechas de scraper_progress: {e}")
                except Exception as e:
                    print(f"[logger] Error leyendo scraper_progress.json: {e}")

            os.makedirs(self._output_dir, exist_ok=True)
            with open(metrics_file, "w", encoding="utf-8") as f:
                json.dump(existing_metrics, f, ensure_ascii=False, indent=4)

            print(f"[logger] Métricas de scraping escritas en {metrics_file}")

        except Exception as e:
            print(f"Error calculando métricas de scraping: {e}")
