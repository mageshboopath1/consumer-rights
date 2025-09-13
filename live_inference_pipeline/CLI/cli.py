import pika
import sys
import time

RABBITMQ_HOST = 'localhost'
PRODUCE_QUEUE = 'terminal_messages'
CONSUME_QUEUE = 'llm_output_queue'

def main():
    try:
        connection_params = pika.ConnectionParameters(RABBITMQ_HOST, heartbeat=600)
        connection = pika.BlockingConnection(connection_params)
        channel = connection.channel()
    except pika.exceptions.AMQPConnectionError as e:
        print("Error: Could not connect to RabbitMQ.")
        print(f"Please ensure your Docker services are running: 'docker-compose up'")
        print(f"Details: {e}")
        sys.exit(1)

    channel.queue_declare(queue=PRODUCE_QUEUE, durable=True)
    channel.queue_declare(queue=CONSUME_QUEUE, durable=True)

    print("Connection successful. Your RAG chatbot is ready.")
    print("Enter your query below. Press CTRL+C to exit.")

    try:
        while True:
            user_query = input("\n> ")
            if not user_query:
                continue

            start_time = time.time()
            print("[i] Query sent. Waiting for a response...")

            channel.basic_publish(
                exchange='',
                routing_key=PRODUCE_QUEUE,
                body=user_query,
                properties=pika.BasicProperties(
                    delivery_mode=pika.spec.PERSISTENT_DELIVERY_MODE
                ))

            response_body = None

            def on_response(ch, method, properties, body):
                nonlocal response_body
                response_body = body
                ch.stop_consuming()

            channel.basic_consume(queue=CONSUME_QUEUE, on_message_callback=on_response, auto_ack=True)
            channel.start_consuming()

            end_time = time.time()
            duration = end_time - start_time

            print("\n--- Chatbot Response ---")
            if response_body:
                print(response_body.decode())
            else:
                print("No response received.")
            print("------------------------")
            print(f"[i] Time taken: {duration:.2f} seconds")


    except KeyboardInterrupt:
        print("\nExiting.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
    finally:
        if connection.is_open:
            connection.close()
        sys.exit(0)

if __name__ == '__main__':
    main()