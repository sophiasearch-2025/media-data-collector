import argparse

from logger.logger_service import LoggerService
from logger.metrics_engine import MetricsEngine
from utils import rabbitmq_utils


def main():
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
    print("Generando métricas...")
    metrics = MetricsEngine()
    metrics.calculate_scraping_metrics()
    print("Métricas generadas")

    conn.close()


if __name__ == "__main__":
    main()
