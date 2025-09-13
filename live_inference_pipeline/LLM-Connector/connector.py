import pika
import time
import os
import sys
import ollama

RABBITMQ_HOST = os.getenv('RABBITMQ_HOST', 'rabbitmq')
CONSUME_QUEUE = 'query_and_context'
PUBLISH_QUEUE = 'llm_output_queue'

OLLAMA_HOST = os.getenv('OLLAMA_HOST', 'ollama')
OLLAMA_MODEL = 'gemma:2b-instruct'

def main():
    connection = None
    for i in range(10):
        try:
            print(f"[*] Attempting to connect to RabbitMQ (attempt {i+1}/10)...")
            connection = pika.BlockingConnection(pika.ConnectionParameters(RABBITMQ_HOST, heartbeat=600))
            print("[+] Successfully connected to RabbitMQ.")
            break
        except pika.exceptions.AMQPConnectionError:
            time.sleep(5)
    if not connection:
        print("[-] Could not connect to RabbitMQ. Exiting.", file=sys.stderr)
        sys.exit(1)
    
    channel = connection.channel()

    channel.queue_declare(queue=CONSUME_QUEUE, durable=True)
    channel.queue_declare(queue=PUBLISH_QUEUE, durable=True)

    def callback(ch, method, properties, body):
        try:
            prompt = body.decode()
            print(f"\n[x] Received prompt from '{CONSUME_QUEUE}'")
            print("---\n[i] Sending prompt to Ollama...")

            client = ollama.Client(host=f'http://{OLLAMA_HOST}:11434')

            response = client.chat(
                model=OLLAMA_MODEL,
                messages=[{'role': 'user', 'content': prompt}]
            )

            final_answer = response['message']['content']

            ch.basic_publish(
                exchange='',
                routing_key=PUBLISH_QUEUE,
                body=final_answer,
                properties=pika.BasicProperties(
                    delivery_mode=pika.spec.PERSISTENT_DELIVERY_MODE
                ))
            
            print(f"[>] Sent final answer to '{PUBLISH_QUEUE}'")

            ch.basic_ack(delivery_tag=method.delivery_tag)

        except Exception as e:
            print(f"[-] An error occurred: {e}", file=sys.stderr)
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(queue=CONSUME_QUEUE, on_message_callback=callback)
    print(f"\n[*] LLM Connector is waiting for messages. To exit press CTRL+C\n")
    channel.start_consuming()

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('Interrupted')
        try:
            sys.exit(0)
        except SystemExit:
            os._exit(0)