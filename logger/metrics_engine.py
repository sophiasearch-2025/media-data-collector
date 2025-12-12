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

                            # Intentar parsear formatos estándar
                            for fmt in ["%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d"]:
                                try:
                                    fecha_dt = datetime.strptime(fecha_parte, fmt)
                                    fecha_normalizada = fecha_dt.strftime("%Y-%m-%d")
                                    break
                                except ValueError:
                                    continue

                            # Si no coincidió con formatos estándar, usar la parte antes del | como está
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

            os.makedirs(self._output_dir, exist_ok=True)
            with open(metrics_file, "w", encoding="utf-8") as f:
                json.dump(existing_metrics, f, ensure_ascii=False, indent=4)

            print(f"[logger] Métricas de scraping escritas en {metrics_file}")

        except Exception as e:
            print(f"Error calculando métricas de scraping: {e}")
