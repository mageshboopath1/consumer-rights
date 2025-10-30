import json
import sys
import os
from typing import List, Dict, Any
from sentence_transformers import SentenceTransformer
from flask import Flask, request, jsonify

app = Flask(__name__)

try:
    model = SentenceTransformer("all-MiniLM-L6-v2")
    print("Model loaded successfully.", file=sys.stderr)
except Exception as e:
    print(f"Failed to load embedding model: {e}", file=sys.stderr)
    sys.exit(1)


@app.route("/api/embed", methods=["POST"])
def embed_endpoint():
    """
    API endpoint to generate embeddings for a list of text chunks.
    It expects a JSON payload with a 'chunks' field (a list of strings).
    """
    try:
        data = request.get_json()
        chunks = data.get("chunks")

        if not chunks or not isinstance(chunks, list):
            return (
                jsonify(
                    {"error": "A list of 'chunks' must be provided in the request body"}
                ),
                400,
            )

        embeddings = model.encode(chunks, convert_to_tensor=False).tolist()

        return jsonify({"embeddings": embeddings}), 200

    except Exception as e:
        return jsonify({"error": f"An unexpected error occurred: {e}"}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5002)
