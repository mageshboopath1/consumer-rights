import pika
import sys
import time

# --- Connection Setup ---
try:
    connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
    channel = connection.channel()
except pika.exceptions.AMQPConnectionError as e:
    print("Error: Could not connect to RabbitMQ.")
    print("Please ensure RabbitMQ is running on 'localhost'.")
    print(f"Details: {e}")
    sys.exit(1)

# --- Queue Declaration ---
# We declare the queue here as well. It's a good practice to do this in both the
# producer and consumer. This ensures that if the consumer starts before the
# producer, the queue will still exist and we won't get an error.
channel.queue_declare(queue='terminal_messages', durable=True)

print(' [*] Waiting for messages. To exit press CTRL+C')


# --- Callback Function ---
# This function is called by the pika library whenever a message is received.
def callback(ch, method, properties, body):
    """
    Processes a received message from the queue.

    Args:
        ch: The channel object.
        method: Method frame with delivery information.
        properties: Header frame with message properties.
        body: The message body (as bytes).
    """
    print(f" [x] Received '{body.decode()}'")
    # Simulate some work being done.
    time.sleep(body.count(b'.'))
    print(" [x] Done")
    # Acknowledge the message. This tells RabbitMQ that the message has been
    # received and processed, and can be safely discarded. If the consumer
    # dies without sending an ack, RabbitMQ will re-queue the message.
    ch.basic_ack(delivery_tag=method.delivery_tag)


# --- Consume Messages ---
# This tells RabbitMQ that the 'callback' function should receive messages
# from our 'terminal_messages' queue.
channel.basic_consume(queue='terminal_messages', on_message_callback=callback)

# --- Start Consuming ---
# This is a blocking call that enters a loop to wait for messages and
# runs our callback function when they arrive.
try:
    channel.start_consuming()
except KeyboardInterrupt:
    print("\nInterrupted by user. Closing connection.")
    connection.close()
    sys.exit(0)
except Exception as e:
    print(f"An unexpected error occurred: {e}")
    connection.close()
    sys.exit(1)