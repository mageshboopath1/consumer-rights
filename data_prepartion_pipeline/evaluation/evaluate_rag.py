import json
import os
import sys

import mlflow
import pandas as pd
from datasets import Dataset
from ragas import evaluate
# --- MODIFIED: Using a non-LLM based metric ---
from ragas.metrics.context_precision import context_precision

# --- CONFIGURATION ---
MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5001")
GOLDEN_DATASET_PATH = "sample_golden_dataset.csv"
CHUNK_STRATEGY = os.getenv("CHUNK_STRATEGY", "basic")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
CONTEXT_SEPARATOR = "|||"


def load_golden_dataset(path: str) -> pd.DataFrame:
    """Loads the golden dataset from a CSV file into a pandas DataFrame."""
    print(f"[*] Loading golden dataset from {path}...")
    try:
        # We need to specify the dtype for the context column to handle potential empty values correctly
        return pd.read_csv(path, dtype={"ground_truth_context": "str"})
    except FileNotFoundError:
        print(f"\n Error: The file at '{path}' was not found.")
        sys.exit(1)


def get_retrieved_context(
    question: str, chunk_strategy: str, embedding_model: str
) -> list:
    """
    This is a placeholder for your actual retrieval logic.
    """
    print(f"[*] Retrieving context for question: '{question[:30]}...'")
    # --- SIMULATED RETRIEVAL ---
    return [
        "This is a simulated retrieved chunk based on the question.",
        "A trader cannot charge a price in excess of the price displayed on the goods.",
    ]


def main():
    """
    Main function to run the RAG evaluation and log results to MLflow.
    """
    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
    mlflow.set_experiment("RAG Model Evaluation")

    golden_df = load_golden_dataset(GOLDEN_DATASET_PATH)

    evaluation_data = {
        "question": [],
        "ground_truths": [],
        "contexts": [],
    }

    for index, row in golden_df.iterrows():
        ground_truth_str = row.get("ground_truth_context", "")
        if pd.notna(ground_truth_str) and ground_truth_str.strip():
            evaluation_data["question"].append(row["question"])
            ground_truth_chunks = [
                ctx.strip() for ctx in ground_truth_str.split(CONTEXT_SEPARATOR)
            ]
            evaluation_data["ground_truths"].append(ground_truth_chunks)
            retrieved_chunks = get_retrieved_context(
                question=row["question"],
                chunk_strategy=CHUNK_STRATEGY,
                embedding_model=EMBEDDING_MODEL,
            )
            evaluation_data["contexts"].append(retrieved_chunks)

    if not evaluation_data["question"]:
        print("\n Error: No valid data found to evaluate in the golden dataset.")
        sys.exit(1)

    dataset = Dataset.from_dict(evaluation_data)

    print("\n[*] Starting evaluation with Ragas...")
    # --- MODIFIED: Using only context_precision without an LLM ---
    # The default for context_precision uses a non-LLM approach (token overlap)
    metrics = [context_precision]

    result = evaluate(dataset, metrics=metrics)
    print("[+] Evaluation complete.")
    print(result)

    with mlflow.start_run(run_name=f"{CHUNK_STRATEGY}-{EMBEDDING_MODEL}-non_llm"):
        print("\n[*] Logging results to MLflow...")
        mlflow.log_param("chunk_strategy", CHUNK_STRATEGY)
        mlflow.log_param("embedding_model", EMBEDDING_MODEL)
        mlflow.log_metric("context_precision", result["context_precision"])

        with open("evaluation_results.json", "w") as f:
            json.dump(result.to_dict(), f)
        mlflow.log_artifact("evaluation_results.json")

    print(" Successfully logged experiment to MLflow.")


if __name__ == "__main__":
    main()
