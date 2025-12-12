import argparse
import time
import signal
import sys
import signal

from logger.logger_service import LoggerService
from logger.metrics_engine import MetricsEngine
from utils import rabbitmq_utils

# Variable global para generar métricas al finalizar
metrics_generated = False

def generate_final_metrics():
    """Genera las métricas finales antes de cerrar"""
    global metrics_generated
    if not metrics_generated:
        print("[Logger Main] Generando métricas finales antes de cerrar...")
        try:
            time.sleep(3)  # Esperar a que Redis termine de escribir
            metrics = MetricsEngine()
            metrics.calculate_scraping_metrics()
            print("[Logger Main] Métricas generadas exitosamente")
            metrics_generated = True
        except Exception as e:
            print(f"[Logger Main] Error generando métricas: {e}")

def signal_handler(signum, frame):
    """Manejador de señales SIGTERM/SIGINT para cerrar gracefully"""
    print(f"[Logger Main] Recibida señal {signum}, cerrando gracefully...")
    generate_final_metrics()
    sys.exit(0)

def main():
    signal.signal(
        signal.SIGINT, signal.SIG_IGN
    )  # scheduler maneja SIGINT, no logger.main
    parser = argparse.ArgumentParser()
    parser.add_argument("--id", type=int, required=True)
    args = parser.parse_args()

    # Setup conexión-canal RabbitMQ
    conn = rabbitmq_utils.get_rabbit_connection()
    channel = conn.channel()

    # Iniciar Logger
    logger = LoggerService(working_batch_id=args.id, channel=channel)
    logger.run()  # Esto bloquea hasta que termine

    # Al finalizar, calcular métricas
    print("[Logger] Generando métricas con MetricsEngine...")
    metrics = MetricsEngine()
    metrics.calculate_scraping_metrics()
    print("[Logger] Métricas generadas.")

    conn.close()


if __name__ == "__main__":
    main()
