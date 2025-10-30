#!/usr/bin/env python3
"""Simple script to populate ChromaDB - run from rag-core container"""

import uuid
import chromadb

# Sample chunks from the Consumer Protection Act
chunks = [
    "The Consumer Protection Act, 2019 provides for protection of the interests of consumers.",
    "A consumer is defined as any person who buys goods or avails services for consideration.",
    "The Act establishes Consumer Disputes Redressal Commissions at District, State and National levels.",
    "Consumers can file complaints regarding defective goods, deficient services, or unfair trade practices.",
    "The District Commission has jurisdiction for complaints where the value does not exceed one crore rupees.",
    "The State Commission has jurisdiction for complaints exceeding one crore but not exceeding ten crore rupees.",
    "The National Commission has jurisdiction for complaints exceeding ten crore rupees.",
    "Product liability provisions hold manufacturers, service providers, and sellers accountable.",
    "The Central Consumer Protection Authority can take suo motu action against violations.",
    "Penalties are prescribed for false or misleading advertisements.",
    "E-commerce transactions are covered under the Act.",
    "Mediation is available as an alternative dispute resolution mechanism.",
    "The Act provides for penalties for manufacturing or selling spurious goods.",
    "Consumer rights include the right to be informed, right to choose, and right to be heard.",
    "The Act came into force on July 20, 2020.",
]

print(f"Populating ChromaDB with {len(chunks)} sample chunks...")

try:
    # Connect to ChromaDB
    client = chromadb.HttpClient(host="chroma_service", port=8000)
    collection = client.get_or_create_collection(name="document_embeddings")

    # Load embedding model
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer("all-MiniLM-L6-v2")

    # Generate embeddings
    print("Generating embeddings...")
    embeddings = model.encode(chunks, convert_to_tensor=False).tolist()

    # Generate IDs
    ids = [str(uuid.uuid4()) for _ in chunks]

    # Add to collection
    print("Adding to ChromaDB...")
    collection.add(embeddings=embeddings, documents=chunks, ids=ids)

    print(f"SUCCESS! Collection now has {collection.count()} documents")

except Exception as e:
    print(f"ERROR: {e}")
    import traceback

    traceback.print_exc()
