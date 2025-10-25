import pika
import time
import os
import sys
import ollama
import json
from datetime import datetime, timezone

RABBITMQ_HOST = os.getenv('RABBITMQ_HOST', 'rabbitmq')
CONSUME_QUEUE = 'query_and_context'
PUBLISH_QUEUE = 'llm_output_queue'
PROCESS_QUEUE = 'process_updates'
CUD_QUEUE = 'CUD_queue' # The queue for the psql-worker

OLLAMA_HOST = os.getenv('OLLAMA_HOST', 'ollama')
OLLAMA_MODEL = 'gemma:2b-instruct'

def split_prompt(merged_prompt: str):
    """
    Splits a merged RAG prompt back into its context and query.
    (This function remains the same)
    """
    try:
        question_marker = "\n\nQuestion:\n"
        context_marker = "Context:\n"
        parts = merged_prompt.split(question_marker)
        if len(parts) != 2: return None, None
        before_question_part = parts[0]
        query = parts[1].strip()
        context_parts = before_question_part.split(context_marker)
        if len(context_parts) != 2: return None, None
        context = context_parts[1].strip()
        return context, query
    except Exception:
        return None, None

# --- NEW FUNCTION FOR CUD PUBLISHING ---
def publish_cud_message(data_to_save):
    """
    Publishes a CREATE message to the CUD_queue for the psql-worker.
    Note: This creates a new, temporary connection for publishing, which is simple.
    For high-volume publishing, reusing connections/channels is better.
    """
    try:
        connection = pika.BlockingConnection(pika.ConnectionParameters(host=RABBITMQ_HOST))
        channel = connection.channel()
        
        # Ensure the CUD_queue is declared (it should be durable to match psql_worker)
        channel.queue_declare(queue=CUD_QUEUE, durable=True)

        # Build the structured CUD message for the psql-worker
        cud_payload = {
          "operation": "CREATE",
          "table": "chat_history", # Your desired table name
          "data": data_to_save
        }
        message_body = json.dumps(cud_payload)

        # Publish the message to the CUD queue
        channel.basic_publish(
            exchange='',
            routing_key=CUD_QUEUE,
            body=message_body.encode('utf-8'),
            properties=pika.BasicProperties(
                delivery_mode=pika.spec.PERSISTENT_DELIVERY_MODE # Durable message
            )
        )
        print(f"[>] Published CREATE message to '{CUD_QUEUE}' for chat_history.")
        connection.close()
        return True
    except pika.exceptions.AMQPConnectionError as e:
        print(f"[-] ERROR: Failed to publish to CUD_queue. RabbitMQ connection issue: {e}", file=sys.stderr)
        return False
    except Exception as e:
        print(f"[-] ERROR: Failed to publish CUD message: {e}", file=sys.stderr)
        return False

# --- MAIN RUNNER FUNCTION ---
def main():
    connection = None
    for i in range(10):
        try:
            print(f"[*] Attempting to connect to RabbitMQ (attempt {i+1}/10)...")
            # Increased heartbeat for robust connection
            connection = pika.BlockingConnection(pika.ConnectionParameters(RABBITMQ_HOST, heartbeat=600))
            print("[+] Successfully connected to RabbitMQ.")
            break
        except pika.exceptions.AMQPConnectionError:
            time.sleep(5)
    if not connection:
        print("[-] Could not connect to RabbitMQ. Exiting.", file=sys.stderr)
        sys.exit(1)
    
    channel = connection.channel()

    # Declaring queues (Consume/Publish/Process typically temporary)
    channel.queue_declare(queue=CONSUME_QUEUE, durable=False)
    channel.queue_declare(queue=PUBLISH_QUEUE, durable=False)
    channel.queue_declare(queue=PROCESS_QUEUE, durable=False)
    # The CUD_QUEUE should be declared durable here for completeness, though psql_worker also declares it
    channel.queue_declare(queue=CUD_QUEUE, durable=True) 

    def callback(ch, method, properties, body):
        context = None
        user_prompt = None
        output = None
        
        try:
            prompt = body.decode()
            print(f"\n[x] Received prompt from '{CONSUME_QUEUE}'")
            print("---\n[i] Sending prompt to Ollama...")

            client = ollama.Client(host=f'http://{OLLAMA_HOST}:11434')

            response = client.chat(
                model=OLLAMA_MODEL,
                messages=[{'role': 'user', 'content': prompt}]
            )

            # 1. Send Status Update
            status_payload = {
                "type": "stage_complete", 
                "stage": "llm_inference",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            ch.basic_publish(exchange='', routing_key=PROCESS_QUEUE, body=json.dumps(status_payload))
            print(f"[>] Sent status update to '{PROCESS_QUEUE}': LLM Inference complete")

            # 2. Extract Data
            context, user_prompt = split_prompt(prompt)
            output = response['message']['content']
            
            # 3. Prepare and Send Final Answer to PUBLISH_QUEUE
            final_answer = json.dumps({
                "input": user_prompt, # Renamed 'i' to 'user_prompt' for clarity
                "context": context,
                "output": output
            })

            ch.basic_publish(
                exchange='',
                routing_key=PUBLISH_QUEUE,
                body=final_answer.encode('utf-8'),
                properties=pika.BasicProperties(delivery_mode=1) # Non-persistent
            )
            print(f"[>] Sent final answer to '{PUBLISH_QUEUE}'")

            # 4. Prepare and Send Data to CUD_QUEUE for Persistence (NEW)
            history_data = {
                "user_prompt": user_prompt, 
                "llm_output": output,
                "context": context,
                "timestamp": datetime.now(timezone.utc).isoformat() # Optional: add timestamp
            }
            publish_cud_message(history_data)

            # 5. Acknowledge Message
            ch.basic_ack(delivery_tag=method.delivery_tag)

        except Exception as e:
            print(f"[-] An error occurred: {e}", file=sys.stderr)
            # NACK if processing fails (requeue=False prevents message loop for bad data)
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