import pika, json
from datetime import datetime as dtime

# DE MOMENTO SOLO VERIFICAREMOS QUE LOS MENSAJES LLEGAN HASTA ENVIO DE DATOS

SEND_DATA_QUEUE = "send_data_queue"

# --- bloque para la conexion global de RabbitMQ ---
connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
planner_channel = connection.channel()
# --- declaración de colas ---
planner_channel.queue_declare(queue=SEND_DATA_QUEUE, durable=True)

def callback(ch, method, properties, body):
    message = json.loads(body)
    print(message)
    print("===================================")    

# --- el planner consume los mensajes de su cola ---
planner_channel.basic_qos(prefetch_count=1)
planner_channel.basic_consume(queue=SEND_DATA_QUEUE, on_message_callback=callback)
planner_channel.start_consuming()