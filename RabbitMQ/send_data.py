import pika, json
from datetime import datetime as dtime

# DE MOMENTO SOLO VERIFICAREMOS QUE LOS MENSAJES LLEGAN HASTA ENVIO DE DATOS (LOS IMPRIMIMOS)

SEND_DATA_QUEUE = "send_data_queue"

# --- bloque para la conexion global de RabbitMQ ---
connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
planner_channel = connection.channel()
# --- declaración de colas ---
planner_channel.queue_declare(queue=SEND_DATA_QUEUE, durable=True)

def callback(ch, method, properties, body):
    message = json.loads(body)
    print(message)
    print(f"Mensaje recibido en send_data: {message}")
    print("=============================================")   
    ch.basic_ack(delivery_tag=method.delivery_tag) 

# --- el planner consume los mensajes de su cola ---
print("Escuchando en send_data_queue...")
planner_channel.basic_consume(queue=SEND_DATA_QUEUE, on_message_callback=callback)
planner_channel.start_consuming()