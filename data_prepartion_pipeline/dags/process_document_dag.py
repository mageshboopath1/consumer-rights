import pendulum
import requests
import chromadb
import uuid
from airflow.decorators import dag, task


PDF_FILE_PATH = "/opt/airflow/data/sample.pdf"

CHROMA_HOST = "chroma_service"
CHROMA_PORT = 8000
COLLECTION_NAME = "document_embeddings"


@dag(
    dag_id="document_processing_pipeline",
    start_date=pendulum.datetime(2025, 1, 1, tz="UTC"),
    catchup=False,
    schedule=None,
    tags=["microservice_pipeline_final"],
)
def process_document_dag():
    """
    ### Full Document ETL Pipeline
    This DAG orchestrates three stages:
    1.  **Chunking**: Reads a PDF and calls a microservice to get text chunks.
    2.  **Embedding**: Calls a microservice to convert chunks into vector embeddings.
    3.  **Ingestion**: Connects to a shared ChromaDB and ingests the data.
    """

    @task
    def call_chunker_service() -> list:
        """Reads a PDF file and sends it to the chunker service."""
        print(f"Processing file: {PDF_FILE_PATH}")
        chunker_url = "http://chunker:5001/api/chunk"
        try:
            with open(PDF_FILE_PATH, "rb") as f:
                files = {"file": (PDF_FILE_PATH.split("/")[-1], f, "application/pdf")}
                response = requests.post(chunker_url, files=files)
                response.raise_for_status()
        except FileNotFoundError:
            raise FileNotFoundError(
                f"The file {PDF_FILE_PATH} was not found inside the Airflow container."
            )
        result = response.json()
        print(f"Received {len(result['chunks'])} chunks from the chunker service.")
        return result["chunks"]

    @task
    def call_embedder_service(chunks: list) -> dict:
        """
        Takes chunks, gets embeddings in batches, and returns BOTH for the next task.
        """
        if not chunks:
            print("No chunks to process. Skipping embedding.")
            return {"chunks": [], "embeddings": []}

        all_embeddings = []
        BATCH_SIZE = 50

        print(f"Starting to embed {len(chunks)} chunks in batches of {BATCH_SIZE}...")
        embedder_url = "http://embedder:5002/api/embed"

        for i in range(0, len(chunks), BATCH_SIZE):
            chunk_batch = chunks[i : i + BATCH_SIZE]
            payload = {"chunks": chunk_batch}
            response = requests.post(embedder_url, json=payload)
            response.raise_for_status()
            result = response.json()
            batch_embeddings = result.get("embeddings", [])

            all_embeddings.extend(batch_embeddings)
            print(
                f"Processed batch {i//BATCH_SIZE + 1}, got {len(batch_embeddings)} embeddings."
            )

        print(f"Finished embedding. Total embeddings created: {len(all_embeddings)}")
        return {"chunks": chunks, "embeddings": all_embeddings}

    @task
    def ingest_into_chroma(data: dict):
        """
        Connects to ChromaDB and ingests the documents and their embeddings.
        """
        chunks = data.get("chunks", [])
        embeddings = data.get("embeddings", [])

        if not chunks or not embeddings:
            print("No data to ingest. Skipping.")
            return

        print(f"Connecting to ChromaDB at {CHROMA_HOST}:{CHROMA_PORT}...")
        client = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)
        collection = client.get_or_create_collection(name=COLLECTION_NAME)

        ids = [str(uuid.uuid4()) for _ in chunks]

        print(
            f"Ingesting {len(chunks)} documents into the '{COLLECTION_NAME}' collection..."
        )
        collection.add(embeddings=embeddings, documents=chunks, ids=ids)
        print("Ingestion successful!")
        return {"ingested_count": len(chunks)}

    chunk_list = call_chunker_service()
    embedding_data = call_embedder_service(chunks=chunk_list)
    ingest_into_chroma(data=embedding_data)


process_document_dag()
