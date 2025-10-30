import json
import os
import sys
import time
from datetime import datetime, timezone

import boto3
import pika

# --- Configuration ---
RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "rabbitmq")
CONSUME_QUEUE = "query_and_context"
PUBLISH_QUEUE = "llm_output_queue"
PROCESS_QUEUE = "process_updates"
CUD_QUEUE = "CUD_queue"

# AWS Bedrock Configuration
AWS_REGION = os.getenv("AWS_REGION", "ap-south-1")
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
BEDROCK_MODEL_ID = os.getenv("BEDROCK_MODEL_ID", "meta.llama3-70b-instruct-v1:0")
BEDROCK_MAX_TOKENS = int(os.getenv("BEDROCK_MAX_TOKENS", "512"))
BEDROCK_TEMPERATURE = float(os.getenv("BEDROCK_TEMPERATURE", "0.7"))

# Initialize Bedrock client
print(f"[i] Initializing AWS Bedrock client...")
print(f"    Region: {AWS_REGION}")
print(f"    Model: {BEDROCK_MODEL_ID}")

try:
    bedrock_runtime = boto3.client(
        service_name="bedrock-runtime",
        region_name=AWS_REGION,
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    )
    print("[+] Bedrock client initialized successfully")
except Exception as e:
    print(f"[!] Failed to initialize Bedrock client: {e}", file=sys.stderr)
    sys.exit(1)


def query_bedrock(prompt: str) -> str:
    """
    Query AWS Bedrock Llama 3 70B model

    Args:
        prompt: The formatted prompt with context and question

    Returns:
        Generated response from Llama 3 70B
    """
    try:
        # Llama 3 request format for Bedrock
        request_body = {
            "prompt": prompt,
            "max_gen_len": BEDROCK_MAX_TOKENS,
            "temperature": BEDROCK_TEMPERATURE,
            "top_p": 0.9,
        }

        print(f"[i] Sending request to Bedrock...")
        start_time = time.time()

        response = bedrock_runtime.invoke_model(
            modelId=BEDROCK_MODEL_ID, body=json.dumps(request_body)
        )

        elapsed_time = time.time() - start_time

        # Parse response
        response_body = json.loads(response["body"].read())
        output = response_body.get("generation", "")

        print(
            f"[+] Received response from Bedrock in {elapsed_time:.2f}s ({len(output)} characters)"
        )
        return output

    except bedrock_runtime.exceptions.ValidationException as e:
        print(f"[!] Bedrock Validation Error: {e}", file=sys.stderr)
        return "I apologize, but the request format was invalid. Please try again."

    except bedrock_runtime.exceptions.ThrottlingException as e:
        print(f"[!] Bedrock Throttling Error (rate limit): {e}", file=sys.stderr)
        return "I apologize, but the service is currently busy. Please try again in a moment."

    except bedrock_runtime.exceptions.ModelNotReadyException as e:
        print(f"[!] Bedrock Model Not Ready: {e}", file=sys.stderr)
        return "I apologize, but the AI model is currently unavailable. Please try again later."

    except bedrock_runtime.exceptions.AccessDeniedException as e:
        print(f"[!] Bedrock Access Denied: {e}", file=sys.stderr)
        print(
            f"[!] Please check: 1) AWS credentials are correct, 2) IAM permissions for Bedrock, 3) Model access is granted",
            file=sys.stderr,
        )
        return "I apologize, but I don't have permission to access the AI model. Please contact the administrator."

    except Exception as e:
        print(f"[!] Bedrock API Error: {e}", file=sys.stderr)
        return "I apologize, but I'm having trouble processing your request right now."


def split_prompt(merged_prompt: str):
    """
    Splits a merged RAG prompt back into its context and query.
    """
    try:
        question_marker = "\n\nQuestion:\n"
        context_marker = "Context:\n"
        parts = merged_prompt.split(question_marker)
        if len(parts) != 2:
            return None, None
        before_question_part = parts[0]
        query = parts[1].strip()
        context_parts = before_question_part.split(context_marker)
        if len(context_parts) != 2:
            return None, None
        context = context_parts[1].strip()
        return context, query
    except Exception:
        return None, None


def publish_cud_message(data_to_save):
    """
    Publishes a CREATE message to the CUD_queue for the psql-worker.
    """
    try:
        connection = pika.BlockingConnection(
            pika.ConnectionParameters(host=RABBITMQ_HOST)
        )
        channel = connection.channel()

        channel.queue_declare(queue=CUD_QUEUE, durable=True)

        cud_payload = {
            "operation": "CREATE",
            "table": "chat_history",
            "data": data_to_save,
        }
        message_body = json.dumps(cud_payload)

        channel.basic_publish(
            exchange="",
            routing_key=CUD_QUEUE,
            body=message_body.encode("utf-8"),
            properties=pika.BasicProperties(
                delivery_mode=pika.spec.PERSISTENT_DELIVERY_MODE
            ),
        )
        print(f"[>] Published CREATE message to '{CUD_QUEUE}' for chat_history.")
        connection.close()
        return True
    except pika.exceptions.AMQPConnectionError as e:
        print(
            f"[-] ERROR: Failed to publish to CUD_queue. RabbitMQ connection issue: {e}",
            file=sys.stderr,
        )
        return False
    except Exception as e:
        print(f"[-] ERROR: Failed to publish CUD message: {e}", file=sys.stderr)
        return False


def main():
    connection = None
    for i in range(10):
        try:
            print(f"[*] Attempting to connect to RabbitMQ (attempt {i+1}/10)...")
            connection = pika.BlockingConnection(
                pika.ConnectionParameters(RABBITMQ_HOST, heartbeat=600)
            )
            print("[+] Successfully connected to RabbitMQ.")
            break
        except pika.exceptions.AMQPConnectionError:
            time.sleep(5)
    if not connection:
        print("[-] Could not connect to RabbitMQ. Exiting.", file=sys.stderr)
        sys.exit(1)

    channel = connection.channel()

    channel.queue_declare(queue=CONSUME_QUEUE, durable=False)
    channel.queue_declare(queue=PUBLISH_QUEUE, durable=False)
    channel.queue_declare(queue=PROCESS_QUEUE, durable=False)
    channel.queue_declare(queue=CUD_QUEUE, durable=True)

    def callback(ch, method, properties, body):
        context = None
        user_prompt = None
        output = None

        try:
            prompt = body.decode()
            print(f"\n[x] Received prompt from '{CONSUME_QUEUE}'")

            # Send status update - LLM processing started
            status_payload = {
                "type": "stage_complete",
                "stage": "llm_processing_started",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            ch.basic_publish(
                exchange="", routing_key=PROCESS_QUEUE, body=json.dumps(status_payload)
            )
            print(
                f"[>] Sent status update to '{PROCESS_QUEUE}': LLM processing started"
            )

            # Query Bedrock
            output = query_bedrock(prompt)

            # Send status update - LLM inference complete
            status_payload = {
                "type": "stage_complete",
                "stage": "llm_inference",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            ch.basic_publish(
                exchange="", routing_key=PROCESS_QUEUE, body=json.dumps(status_payload)
            )
            print(
                f"[>] Sent status update to '{PROCESS_QUEUE}': LLM Inference complete"
            )

            # Extract context and user prompt
            context, user_prompt = split_prompt(prompt)
            if not user_prompt:
                user_prompt = prompt
            if not context:
                context = "No context provided"

            # Prepare and send final answer to PUBLISH_QUEUE
            final_answer = json.dumps(
                {"input": user_prompt, "context": context, "output": output}
            )

            ch.basic_publish(
                exchange="",
                routing_key=PUBLISH_QUEUE,
                body=final_answer.encode("utf-8"),
                properties=pika.BasicProperties(delivery_mode=1),
            )
            print(f"[>] Sent final answer to '{PUBLISH_QUEUE}'")

            # Prepare and send data to CUD_QUEUE for persistence
            history_data = {
                "user_prompt": user_prompt,
                "llm_output": output,
                "context": context,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            publish_cud_message(history_data)

            # Acknowledge message
            ch.basic_ack(delivery_tag=method.delivery_tag)

        except Exception as e:
            print(f"[-] An error occurred: {e}", file=sys.stderr)
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(
        queue=CONSUME_QUEUE, on_message_callback=callback, auto_ack=False
    )

    print(
        f"\n[*] LLM Connector (AWS Bedrock) is waiting for messages. To exit press CTRL+C\n"
    )
    channel.start_consuming()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Interrupted")
        try:
            sys.exit(0)
        except SystemExit:
            os._exit(0)
