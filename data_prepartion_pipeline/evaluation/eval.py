import os
import sys
import json
import requests
import pandas as pd
from langchain.vectorstores import FAISS
from langchain.embeddings import HuggingFaceInstructEmbeddings

# --- Configuration ---
CHUNKER_URL = os.getenv("CHUNKER_URL")
GOLDEN_DATASET_PATH = "sample_golden_dataset.csv"

def main():
    """
    Main function to trigger the chunker, create a vector store,
    and evaluate retrieval based on a golden dataset.
    """
    if not CHUNKER_URL:
        print("Error: CHUNKER_URL environment variable is not set.")
        sys.exit(1)

    print(f"Attempting to trigger chunker service at: {CHUNKER_URL}")

    try:
        # --- 1. Get Chunks from the Service ---
        response = requests.post(CHUNKER_URL, timeout=600)
        response.raise_for_status()
        data = response.json()
        chunks = data.get("chunks")
        
        if not chunks:
            print("Error: Received no chunks from the service.")
            sys.exit(1)
        
        print(f"\n--- Successfully received {len(chunks)} chunks from the service ---")

        # --- 2. Initialize Embedding Model ---
        # Using a sentence-transformer model that runs locally.
        # 'instructor-large' is a powerful model for this task.
        print("\nInitializing embedding model...")
        embeddings = HuggingFaceInstructEmbeddings(
            model_name="hkunlp/instructor-large",
            model_kwargs={"device": "cpu"} # Use CPU for broad compatibility
        )
        
        # --- 3. Create a Temporary Vector Store (In-Memory) ---
        # FAISS is a highly efficient library for similarity search.
        # We create the vector store from the text chunks and their embeddings.
        print("Creating in-memory FAISS vector store from chunks...")
        vector_store = FAISS.from_texts(texts=chunks, embedding=embeddings)
        print("Vector store created successfully.")

        # --- 4. Load Golden Dataset and Perform Retrieval ---
        print("\nLoading golden dataset and performing retrieval for each question...")
        golden_df = pd.read_csv(GOLDEN_DATASET_PATH)
        
        # Create a retriever from the vector store
        retriever = vector_store.as_retriever()

        for index, row in golden_df.iterrows():
            question = row['question']
            
            # Retrieve the most relevant documents (chunks) for the question
            retrieved_docs = retriever.get_relevant_documents(question)
            
            print(f"\n--- Question {index+1}: {question} ---")
            print("Retrieved Content:")
            for i, doc in enumerate(retrieved_docs):
                # doc.page_content contains the text of the chunk
                print(f"  {i+1}. {doc.page_content[:250]}...") # Print a preview
        
        print("\n\nEvaluation script finished successfully!")

    except requests.exceptions.RequestException as e:
        print(f"Error calling the chunker service: {e}")
        sys.exit(1)
    except FileNotFoundError:
        print(f"Error: The golden dataset was not found at '{GOLDEN_DATASET_PATH}'")
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()