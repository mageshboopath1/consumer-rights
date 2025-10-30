import re
import os
import json
from typing import List
from flask import Flask, request, jsonify
import fitz

app = Flask(__name__)


def chunk_document(file_stream, chunk_size: int = 500, overlap: int = 50) -> List[str]:
    """
    Reads a PDF file from a stream, extracts text, and splits it into chunks.
    """
    doc = fitz.open(stream=file_stream.read(), filetype="pdf")
    full_text = ""
    for page in doc:
        full_text += page.get_text()

    full_text = re.sub(r"\s+", " ", full_text).strip()

    if not full_text:
        return []

    chunks: List[str] = []
    if len(full_text) <= chunk_size:
        return [full_text]

    start = 0
    while start < len(full_text):
        end = start + chunk_size
        chunks.append(full_text[start:end])
        start += chunk_size - overlap

    return chunks


@app.route("/api/chunk", methods=["POST"])
def chunk_endpoint():
    """
    API endpoint that accepts a PDF file upload and returns text chunks.
    """
    if "file" not in request.files:
        return jsonify({"error": "No file part in the request"}), 400

    file = request.files["file"]

    if file.filename == "":
        return jsonify({"error": "No selected file"}), 400

    if file and file.filename.endswith(".pdf"):
        try:
            chunks = chunk_document(file)
            return jsonify({"chunks": chunks}), 200
        except Exception as e:
            return jsonify({"error": f"An unexpected error occurred: {e}"}), 500
    else:
        return jsonify({"error": "Invalid file type, please upload a PDF"}), 400


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001)
