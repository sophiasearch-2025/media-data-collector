import pika, json
from datetime import datetime as dtime
from utils.stop_signal_handler import StopSignalHandler

# DE MOMENTO SOLO VERIFICAREMOS QUE LOS MENSAJES LLEGAN HASTA ENVIO DE DATOS (LOS IMPRIMIMOS)

SEND_DATA_QUEUE = "send_data_queue"

# --- bloque para la conexion global de RabbitMQ ---
connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
planner_channel = connection.channel()
# --- declaración de colas (durable=False para coincidir con logger) ---
planner_channel.queue_declare(queue=SEND_DATA_QUEUE, durable=False, auto_delete=True)

def callback(ch, method, properties, body):
    message = json.loads(body)
    print(message)
    print(f"Mensaje recibido en send_data: {message}")
    print("=============================================")
    ch.basic_ack(delivery_tag=method.delivery_tag)

# --- el planner consume los mensajes de su cola ---
print("Escuchando en send_data_queue...")
planner_channel.basic_consume(queue=SEND_DATA_QUEUE, on_message_callback=callback)
signal_handler = StopSignalHandler(planner_channel, planner_channel, "Sender")
while not signal_handler._should_stop():
    connection.process_data_events(time_limit=1)
connection.close()
