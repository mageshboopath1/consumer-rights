import pika
import sys
import time
import re

connection = None
for i in range(10):
    try:
        connection_params = pika.ConnectionParameters('rabbitmq', heartbeat=600)
        connection = pika.BlockingConnection(connection_params)
        print("pii-filter successfully connected to RabbitMQ.")
        break
    except pika.exceptions.AMQPConnectionError:
        print(f"Connection attempt {i+1}/10 failed. Retrying in 5 seconds...")
        time.sleep(5)

if not connection:
    print("Error: Could not connect to RabbitMQ after multiple attempts.")
    sys.exit(1)

channel = connection.channel()

channel.queue_declare(queue='terminal_messages', durable=True)

channel.queue_declare(queue='redacted_queue', durable=True)

channel.basic_qos(prefetch_count=1)
print(' [*] pii-filter service is waiting for messages...')


def process_message(body):
    text = body.decode()
    print(f" [x] Received from 'terminal_messages': '{text}'")

    name_regex = r"\b(?!Mr\.|Ms\.|Dr\.|Mrs\.|Mr|Ms|Dr|and)\b([A-Z][a-z]+)\s+([A-Z][a-z]+)\b"
    email_regex = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
    phone_regex = r"(\(\d{3}\)\s*\d{3}-\d{4}|\d{3}-\d{3}-\d{4})"

    redacted_text = re.sub(email_regex, "[EMAIL]", text)
    redacted_text = re.sub(phone_regex, "[PHONE]", redacted_text)
    redacted_text = re.sub(name_regex, "[NAME]", redacted_text)
    
    channel.basic_publish(
        exchange='',
        routing_key='redacted_queue',
        body=redacted_text.encode(),
        properties=pika.BasicProperties(
            delivery_mode=2,
        ))
    print(f" [>] Sent to 'redacted_queue': '{redacted_text}'")


def callback(ch, method, properties, body):
    process_message(body)
    ch.basic_ack(delivery_tag=method.delivery_tag)

channel.basic_consume(queue='terminal_messages', on_message_callback=callback)

try:
    channel.start_consuming()
except KeyboardInterrupt:
    print("\nInterrupted.")
finally:
    if connection.is_open:
        connection.close()