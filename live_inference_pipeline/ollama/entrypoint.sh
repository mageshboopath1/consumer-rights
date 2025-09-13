#!/bin/sh
# This script ensures the Ollama server is running before pulling the model.
set -e

ollama serve &
pid=$!

echo "Waiting for Ollama server to start..."
while ! ollama ps > /dev/null 2>&1; do
  sleep 1
done
echo "Ollama server started."

echo "Pulling gemma:2b-instruct model..."
ollama pull gemma:2b-instruct
echo "Model pull complete."

wait $pid