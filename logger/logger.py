import argparse
import json
import os
import sys

from pika.exceptions import AMQPChannelError

import utils.rabbitmq_utils as rabbit

from . import logs_operations

# listas de logging en redis
CRAWLER_ERRORS = "crawler_errors"
SCHEDULER_ERRORS = "scheduler_errors"
SCRAPING_RESULTS = "scraping_results"
LOGGER_CTRL = "logging_control"


def callback_crawler(id_logging_process: int):
    def callback(ch, method, properties, body):
        try:
            msg = json.loads(body)
            msg["id_logging_process"] = id_logging_process
            logs_operations.anexar_log(msg, CRAWLER_ERRORS)
            print(f"[crawler_log_queue] Mensaje recibido: {msg}")
            ch.basic_ack(delivery_tag=method.delivery_tag)
        except Exception as e:
            print(f"[crawler_log_queue] ERROR procesando mensaje: {e}")
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

    return callback


def callback_scheduler(id_logging_process: int):
    def callback(ch, method, properties, body):
        try:
            msg = json.loads(body)
            msg["id_logging_process"] = id_logging_process
            logs_operations.anexar_log(msg, SCHEDULER_ERRORS)
            print(f"[scheduler_log_queue] Mensaje recibido: {msg}")
            ch.basic_ack(delivery_tag=method.delivery_tag)
        except Exception as e:
            print(f"[scheduler_log_queue] ERROR procesando mensaje: {e}")
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

    return callback


def callback_scraping(id_logging_process: int):
    def callback(ch, method, properties, body):
        try:
            msg = json.loads(body)
            msg["id_logging_process"] = id_logging_process
            logs_operations.anexar_log(msg, SCRAPING_RESULTS)
            print(f"[scraping_log_queue] Mensaje recibido: {msg}")
            ch.basic_ack(delivery_tag=method.delivery_tag)
        except Exception as e:
            print(f"[scraping_log_queue] ERROR procesando mensaje: {e}")
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

    return callback


def callback_control(id_logging_process: int, state):
    def callback(ch, method, properties, body):
        try:
            msg = json.loads(body)

            # Si escuchó que se está iniciando una nueva tanda de scrapeo,
            # limpia logs anteriores
            if msg.get("action") == "start_batch":
                for lista in [
                    CRAWLER_ERRORS,
                    SCHEDULER_ERRORS,
                    SCRAPING_RESULTS,
                    LOGGER_CTRL,
                ]:
                    logs_operations.clear_logs_list(lista)

            if msg.get("action") == "end_batch_received":
                print(
                    "[logging_control] end_batch_received (se recibió señal para concluir logging). Cerrando el proceso de loggeo y esperando los últimos resultados de scrapeo o mensajes..."
                )
                # Cambia estado interno
                state["terminating"] = True
                try:
                    # Detener el loop de consuming para que el flujo principal continúe
                    ch.stop_consuming()
                except Exception:
                    pass

            logs_operations.anexar_log(msg, LOGGER_CTRL)
            ch.basic_ack(delivery_tag=method.delivery_tag)
        except Exception as e:
            print(f"[logging_control_queue] ERROR procesando mensaje: {e}")
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

    return callback


def queues_empty(channel, log_queues):
    try:
        for q in log_queues:
            q_state = channel.queue_declare(queue=q, passive=True)
            if q_state.method.message_count != 0:
                return False
        return True
    except Exception as e:
        print(f"[logger] Error verificando colas: {e}")
        return False  # Asumir no vacías si hay error


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--id", type=int, required=True)
    id_logging_process = parser.parse_args().id

    state = {"terminating": False}

    try:
        rabbit_channel = rabbit.get_rabbit_connection().channel()
    except AMQPChannelError as e:
        print("Error al establecer canal en RabbitMQ")
        raise RuntimeError(f"Error de canal en RabbitMQ: {e}") from e

    log_queues = [
        "crawler_log_queue",
        "scheduler_log_queue",
        "scraping_log_queue",
        "logging_control_queue",
    ]
    for queue_name in log_queues:
        rabbit_channel.queue_declare(queue=queue_name, durable=True)

    rabbit_channel.basic_consume(
        queue="crawler_log_queue",
        on_message_callback=callback_crawler(id_logging_process),
    )
    rabbit_channel.basic_consume(
        queue="scheduler_log_queue",
        on_message_callback=callback_scheduler(id_logging_process),
    )
    rabbit_channel.basic_consume(
        queue="scraping_log_queue",
        on_message_callback=callback_scraping(id_logging_process),
    )
    rabbit_channel.basic_consume(
        queue="logging_control_queue",
        on_message_callback=callback_control(id_logging_process, state),
    )

    print("Escuchando logs en RabbitMQ...")

    # loop de escucha/consuming
    try:
        rabbit_channel.start_consuming()
    except KeyboardInterrupt:
        print("[logger] Interrupción manual detectada")
        rabbit_channel.stop_consuming()
    except Exception as e:
        print(f"[logger] Error al consumir mensajes en RabbitMQ: {e}")
        # No hacer raise, simplemente continuar con el cierre

    if state["terminating"]:
        print("[logger] Concluyendo últimos mensajes de loggeo")

        import time
        from datetime import datetime

        # esperar que colas estén vacías
        try:
            timeout = 300  # 5 minutos máximo
            elapsed = 0
            while not queues_empty(rabbit_channel, log_queues) and elapsed < timeout:
                time.sleep(0.5)
                elapsed += 0.5
            
            if elapsed >= timeout:
                print(f"[logger] ADVERTENCIA - Timeout esperando colas vacías después de {timeout}s")
            else:
                print("[logger] Todas las colas en log_queues están vacías. Cerrando logger.")
            
            time.sleep(0.5)
            rabbit_channel.stop_consuming()
        except Exception as e:
            print(f"[logger] Error esperando colas vacías: {e}")

        # registrar final de cierre y anexar directamente en los logs de redis
        

        # Calcular métricas del scraping a partir de los logs almacenados en Redis
        try:
            from datetime import datetime

            scraping_logs = logs_operations.get_logs_list(SCRAPING_RESULTS)
            
            # Agrupar logs por medio
            logs_por_medio = {}
            for log in scraping_logs:
                medio = log.get("medio", "unknown")
                if medio not in logs_por_medio:
                    logs_por_medio[medio] = []
                logs_por_medio[medio].append(log)
            
            # Leer métricas existentes o crear diccionario vacío
            metrics_file = "metrics/scraper_metrics.json"
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
                noticias_por_minuto = exitos / (duracion_segundos / 60) if duracion_segundos > 0 else 0
                tiempo_promedio = (sum(dur_ms) / 1000.0) / exitos if (exitos > 0 and dur_ms) else 0

                # Calcular publicaciones por fecha para este medio
                publicaciones_por_fecha = {}
                for l in medio_logs:
                    fecha_pub = l.get("fecha_publicacion")
                    if fecha_pub and fecha_pub.strip():
                        try:
                            fecha_normalizada = None
                            
                            # Primero: extraer solo la parte de fecha (antes del |) del formato "Día DD mes de YYYY | HH:MM"
                            fecha_parte = fecha_pub.split("|")[0].strip() if "|" in fecha_pub else fecha_pub.strip()
                            
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
                            
                            publicaciones_por_fecha[fecha_normalizada] = publicaciones_por_fecha.get(fecha_normalizada, 0) + 1
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
                    "publicaciones_por_fecha": dict(sorted(publicaciones_por_fecha.items())),
                }

            os.makedirs("metrics", exist_ok=True)
            with open(metrics_file, "w", encoding="utf-8") as f:
                json.dump(existing_metrics, f, ensure_ascii=False, indent=4)
            print("[logger] Métricas de scraping escritas en metrics/scraper_metrics.json")
        except Exception as e:
            print(f"Error calculando métricas de scraping: {e}")



        end_complete_ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        end_msg = {
            "action": "end_batch_completed",
            "id_logging_process": id_logging_process,
            "timestamp": end_complete_ts,
        }

        logs_operations.anexar_log(end_msg, LOGGER_CTRL)

        rabbit_channel.close()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Interrupted")
        try:
            sys.exit(0)
        except SystemExit:
            os._exit(0)
