import pika
import sys
import time
from deepeval.metrics import AnswerRelevancyMetric
from deepeval.models import OllamaModel
from deepeval.test_case import LLMTestCase
import json
from deepeval.metrics import AnswerRelevancyMetric, ContextualPrecisionMetric
from deepeval import evaluate

RABBITMQ_HOST = 'localhost'
PRODUCE_QUEUE = 'terminal_messages'
CONSUME_QUEUE = 'llm_output_queue'

#RAG eval
model = OllamaModel(model="gemma:2b-instruct", base_url="http://localhost:11434")
task_completion_metric = AnswerRelevancyMetric(model=model)
expectedOutput = """A product seller can be held liable if they:
Exercised significant control over the designing, testing, manufacturing, or labeling of the harmful product.
Altered or modified the product, and this change was a substantial factor in causing the harm.
Made an independent express warranty that the product failed to meet.
Sold the product when the manufacturer's identity is unknown or if legal action cannot be enforced against the manufacturer.
Failed to use reasonable care in assembling or inspecting the product, or did not pass on the manufacturer's warnings to the consumer."""

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

    channel.queue_declare(queue=PRODUCE_QUEUE, durable=False)
    channel.queue_declare(queue=CONSUME_QUEUE, durable=False)

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
                #print(response_body.decode())
                llm_response = json.loads(response_body.decode())
                print(llm_response["output"])
            else:
                print("No response received.")
            print("------------------------")
            print(f"[i] Time taken: {duration:.2f} seconds")

            test_case = LLMTestCase(
                input = llm_response["input"],
                actual_output = llm_response["output"],
                retrieval_context = [llm_response["context"]],
                expected_output = expectedOutput
            )

            answer_relevancy = AnswerRelevancyMetric(
                threshold=0.8,
                model=model,
                include_reason=True
            )
            contextual_precision = ContextualPrecisionMetric(
                threshold=0.8,
                model=model,
                include_reason=True
            )

            evaluate([test_case], metrics=[answer_relevancy, contextual_precision])
            print("Evaluated!!")


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