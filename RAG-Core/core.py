# --- core.py ---
# This script consumes messages from the 'redacted_queue',
# performs a RAG query using ChromaDB, and then publishes
# the final context-rich prompt to the 'query_and_context' queue.

import pika
import time
import os
import sys
import chromadb
from sentence_transformers import SentenceTransformer

# --- RabbitMQ Configuration ---
RABBITMQ_HOST = os.getenv('RABBITMQ_HOST', 'rabbitmq')
CONSUME_QUEUE = 'redacted_queue'
PUBLISH_QUEUE = 'query_and_context' # New queue for the final prompt

# --- ChromaDB Configuration ---
CHROMA_HOST = os.getenv('CHROMA_HOST', 'chroma')
CHROMA_PORT = int(os.getenv('CHROMA_PORT', 8000))

def run_rag_query(user_query: str) -> str:
    """
    Performs a RAG query by embedding the user's query, searching a ChromaDB
    collection for relevant documents, and constructing a final prompt.
    """
    try:
        # Step 1: Initialize the ChromaDB client (already connected in main)
        client = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)
        collection_name = "document_embeddings"
        
        try:
            collection = client.get_collection(name=collection_name)
        except Exception as e:
            print(f"Collection '{collection_name}' not found. Error: {e}", file=sys.stderr)
            return "No relevant documents found in the knowledge base."

        # Step 2: Load the embedding model
        print("[i] Loading sentence transformer model...")
        model = SentenceTransformer('all-MiniLM-L6-v2')
        query_embedding = model.encode(user_query, convert_to_tensor=False).tolist()
        print("[i] Query embedded successfully.")

        # Step 3: Perform a semantic search
        search_results = collection.query(
            query_embeddings=[query_embedding],
            n_results=3,
        )

        # Step 4: Extract the retrieved documents
        retrieved_documents = search_results.get('documents', [])
        
        if not retrieved_documents or not retrieved_documents[0]:
            context = "No relevant documents found in the knowledge base."
        else:
            context = " ".join(retrieved_documents[0])
            print(f"[i] Retrieved context: {context[:100]}...") # Log a snippet of the context

        # Step 5: Construct the final prompt for the LLM
        prompt = (
            "Given the following context, please answer the question. "
            "If the answer is not present in the context, please state that "
            "and do not try to make up an answer.\n\n"
            f"Context:\n{context}\n\n"
            f"Question:\n{user_query}\n"
        )
        
        return prompt

    except Exception as e:
        print(f"An unexpected error occurred in the RAG core: {e}", file=sys.stderr)
        # Return an empty string or a specific error message
        return ""

def main():
    # --- RabbitMQ Connection with Retry Logic ---
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

    # --- Ensure Both Queues Exist ---
    channel.queue_declare(queue=CONSUME_QUEUE, durable=True)
    channel.queue_declare(queue=PUBLISH_QUEUE, durable=True) # Ensure the new publish queue exists

    def callback(ch, method, properties, body):
        try:
            user_query = body.decode()
            print(f"\n[x] Received from '{CONSUME_QUEUE}': '{user_query}'")

            # Run the RAG query to get the final prompt
            final_prompt = run_rag_query(user_query)

            if final_prompt:
                # Instead of printing, publish to the new queue
                channel.basic_publish(
                    exchange='',
                    routing_key=PUBLISH_QUEUE,
                    body=final_prompt.encode('utf-8'),
                    properties=pika.BasicProperties(
                        delivery_mode=2,  # make message persistent
                    ))
                print(f"[>] Sent final prompt to '{PUBLISH_QUEUE}'")
            else:
                print("[-] RAG query failed, not publishing message.")

            ch.basic_ack(delivery_tag=method.delivery_tag)

        except Exception as e:
            print(f"[-] An error occurred in the callback: {e}", file=sys.stderr)
            # Negative acknowledgement to re-queue the message if something goes wrong
            ch.basic_nack(delivery_tag=method.delivery_tag)

    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(queue=CONSUME_QUEUE, on_message_callback=callback)

    print(f"\n[*] rag-core service is waiting for messages. To exit press CTRL+C\n")
    channel.start_consuming()

if __name__ == '__main__':
    try:
        # Wait for ChromaDB to be ready before starting
        for i in range(10):
            try:
                print(f"[*] Attempting to connect to ChromaDB (attempt {i+1}/10)...")
                client = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)
                client.heartbeat() # This will raise an exception if it can't connect
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