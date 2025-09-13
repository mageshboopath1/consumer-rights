import os
import sys
import json
import requests

# --- Configuration ---
# This URL is provided by the 'env' section of the GitHub Actions workflow
CHUNKER_URL = os.getenv("CHUNKER_URL")

def main():
    """
    Main function to trigger the evaluation service and print the result.
    """
    if not CHUNKER_URL:
        print("Error: CHUNKER_URL environment variable is not set.")
        sys.exit(1)

    print(f"Attempting to trigger evaluation service at: {CHUNKER_URL}")

    try:
        # Make a simple POST request to trigger the service
        # The service will do all the work internally (fetch, parse, chunk)
        response = requests.post(CHUNKER_URL, timeout=600)
        
        # Check if the request was successful
        response.raise_for_status()
        
        # Get the chunks from the JSON response
        data = response.json()
        chunks = data.get("chunks")
        
        print("\n--- Successfully received chunks from the service ---")
        # Pretty-print the JSON output so it's easy to read in the logs
        print(json.dumps(chunks, indent=2))
        print("\nIntegration test passed! The script successfully communicated with the service.")

    except requests.exceptions.RequestException as e:
        print(f"Error calling the evaluation service: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()