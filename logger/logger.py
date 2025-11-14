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
        msg = json.loads(body)
        msg["id_logging_process"] = id_logging_process
        logs_operations.anexar_log(msg, CRAWLER_ERRORS)
        print(f"[crawler_log_queue] Mensaje recibido: {msg}")

        ch.basic_ack(delivery_tag=method.delivery_tag)

    return callback


def callback_scheduler(id_logging_process: int):
    def callback(ch, method, properties, body):
        msg = json.loads(body)
        msg["id_logging_process"] = id_logging_process
        logs_operations.anexar_log(msg, SCHEDULER_ERRORS)
        print(f"[scheduler_log_queue] Mensaje recibido: {msg}")

        ch.basic_ack(delivery_tag=method.delivery_tag)

    return callback


def callback_scraping(id_logging_process: int):
    def callback(ch, method, properties, body):
        msg = json.loads(body)
        msg["id_logging_process"] = id_logging_process
        logs_operations.anexar_log(msg, SCRAPING_RESULTS)
        print(f"[scraping_log_queue] Mensaje recibido: {msg}")

        ch.basic_ack(delivery_tag=method.delivery_tag)

    return callback


def callback_control(id_logging_process: int, state):
    def callback(ch, method, properties, body):
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

        logs_operations.anexar_log(msg, LOGGER_CTRL)

        ch.basic_ack(delivery_tag=method.delivery_tag)

    return callback


def queues_empty(channel, log_queues):
    for q in log_queues:
        q_state = channel.queue_declare(queue=q, passive=True)
        if q_state.method.message_count != 0:
            return False
    return True


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
    except Exception as e:
        print("Error al tratar de recibir mensajes en RabbitMQ")
        raise RuntimeError(f"Error al consumir mensajes en RabbitMQ: {e}") from e

    if state["terminating"]:
        print("[logger] Concluyendo últimos mensajes de loggeo")

        import time
        from datetime import datetime

        # esperar que colas estén vacías
        while not queues_empty(rabbit_channel, log_queues):
            time.sleep(0.5)
        print("[logger] Todas las colas en log_queues están vacías. Cerrando logger.")
        time.sleep(0.5)
        rabbit_channel.stop_consuming()

        # registrar final de cierre y anexar directamente en los logs de redis
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
