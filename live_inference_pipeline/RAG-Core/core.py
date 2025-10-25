import pika
import time
import os
import sys
import chromadb
import json
from datetime import datetime, timezone
from sentence_transformers import SentenceTransformer

RABBITMQ_HOST = os.getenv('RABBITMQ_HOST', 'rabbitmq')
CONSUME_QUEUE = 'redacted_queue'
PUBLISH_QUEUE = 'query_and_context'
PROCESS_QUEUE = 'process_updates'

CHROMA_HOST = os.getenv('CHROMA_HOST', 'chroma_service')
CHROMA_PORT = int(os.getenv('CHROMA_PORT', 8000))

def run_rag_query(user_query: str, channel) -> str:
    """
    Performs a RAG query by embedding the user's query, searching a ChromaDB
    collection for relevant documents, and constructing a final prompt.
    """
    try:
        client = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)
        collection_name = "document_embeddings"
        
        try:
            collection = client.get_collection(name=collection_name)
        except Exception as e:
            print(f"Collection '{collection_name}' not found. Error: {e}", file=sys.stderr)
            return "No relevant documents found in the knowledge base."

        print("[i] Loading sentence transformer model...")
        model = SentenceTransformer('all-MiniLM-L6-v2')
        query_embedding = model.encode(user_query, convert_to_tensor=False).tolist()
        print("[i] Query embedded successfully.")

        status_payload_1 = {
            "type": "stage_complete", 
            "stage": "vector_embedding",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        channel.basic_publish(exchange='', routing_key=PROCESS_QUEUE, body=json.dumps(status_payload_1))
        print(f"[>] Sent status update to '{PROCESS_QUEUE}': Vector Embedding complete")

        search_results = collection.query(
            query_embeddings=[query_embedding],
            n_results=3,
        )

        status_payload_2 = {
            "type": "stage_complete", 
            "stage": "contextual_retrieval",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        channel.basic_publish(exchange='', routing_key=PROCESS_QUEUE, body=json.dumps(status_payload_2))
        print(f"[>] Sent status update to '{PROCESS_QUEUE}': Contextual Retrieval complete")

        retrieved_documents = search_results.get('documents', [])
        
        if not retrieved_documents or not retrieved_documents[0]:
            context = "No relevant documents found in the knowledge base."
        else:
            context = " ".join(retrieved_documents[0])
            print(f"[i] Retrieved context: {context[:100]}...")

        prompt = (
            "You are a legal assistant. Based *only* on the following context, answer the user's question. Pay close attention to any exceptions or contradictions mentioned. If the context does not contain the answer, say so.\n\n"
            f"Context:\n{context}\n\n"
            f"Question:\n{user_query}\n"
        )
        
        return prompt

    except Exception as e:
        print(f"An unexpected error occurred in the RAG core: {e}", file=sys.stderr)
        return ""

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
        print("[-] Could not connect to RabbitMQ after several attempts. Exiting.", file=sys.stderr)
        sys.exit(1)

    channel = connection.channel()

    channel.queue_declare(queue=CONSUME_QUEUE, durable=False)
    channel.queue_declare(queue=PUBLISH_QUEUE, durable=False)

    def callback(ch, method, properties, body):
        try:
            user_query = body.decode()
            print(f"\n[x] Received from '{CONSUME_QUEUE}': '{user_query}'")

            final_prompt = run_rag_query(user_query, ch)

            if final_prompt:
                channel.basic_publish(
                    exchange='',
                    routing_key=PUBLISH_QUEUE,
                    body=final_prompt.encode('utf-8'),
                    properties=pika.BasicProperties(
                        delivery_mode=2,
                    ))
                print(f"[>] Sent final prompt to '{PUBLISH_QUEUE}'")
            else:
                print("[-] RAG query failed, not publishing message.")

            ch.basic_ack(delivery_tag=method.delivery_tag)

        except Exception as e:
            print(f"[-] An error occurred in the callback: {e}", file=sys.stderr)
            ch.basic_nack(delivery_tag=method.delivery_tag)

    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(queue=CONSUME_QUEUE, on_message_callback=callback)

    print(f"\n[*] rag-core service is waiting for messages. To exit press CTRL+C\n")
    channel.start_consuming()

if __name__ == '__main__':
    try:
        for i in range(10):
            try:
                print(f"[*] Attempting to connect to ChromaDB (attempt {i+1}/10)...")
                client = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)
                client.heartbeat()
                print("[+] Successfully connected to ChromaDB.")
                break
            except Exception as e:
                print(f"[-] ChromaDB not ready yet. Retrying in 5 seconds... Error: {e}", file=sys.stderr)
                time.sleep(5)
        else:
             print("[-] Could not connect to ChromaDB after several attempts. Exiting.", file=sys.stderr)
             sys.exit(1)

        main()
    except KeyboardInterrupt:
        print('Interrupted')
        try:
            sys.exit(0)
        except SystemExit:
            os._exit(0)