# --- chat_cli.py ---
# This script acts as the user interface for the RAG pipeline.
# It sends a user's query to the RabbitMQ pipeline and then waits
# to consume the final answer from the 'llm_output_queue',
# timing the entire process.

import pika
import sys
import time

# --- RabbitMQ Configuration ---
RABBITMQ_HOST = 'localhost'
PRODUCE_QUEUE = 'terminal_messages'
CONSUME_QUEUE = 'llm_output_queue'

def main():
    # --- Connection Setup ---
    try:
        connection_params = pika.ConnectionParameters(RABBITMQ_HOST, heartbeat=600)
        connection = pika.BlockingConnection(connection_params)
        channel = connection.channel()
    except pika.exceptions.AMQPConnectionError as e:
        print("Error: Could not connect to RabbitMQ.")
        print(f"Please ensure your Docker services are running: 'docker-compose up'")
        print(f"Details: {e}")
        sys.exit(1)

    # --- Queue Declaration ---
    # Ensure both the queue we send to and the queue we receive from exist.
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

            # --- Publish the User's Query ---
            channel.basic_publish(
                exchange='',
                routing_key=PRODUCE_QUEUE,
                body=user_query,
                properties=pika.BasicProperties(
                    delivery_mode=pika.spec.PERSISTENT_DELIVERY_MODE
                ))

            # --- Wait for the Final Response ---
            response_body = None

            # This callback function will be triggered when a message is received.
            def on_response(ch, method, properties, body):
                nonlocal response_body
                response_body = body
                # Stop consuming now that we have our answer.
                ch.stop_consuming()

            # Start consuming from the final output queue.
            # This is a blocking call that will wait until a message arrives.
            channel.basic_consume(queue=CONSUME_QUEUE, on_message_callback=on_response, auto_ack=True)
            channel.start_consuming()

            # --- Display the Result ---
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