import os
from flask import Flask, jsonify

# This is the crucial import. It imports the specific strategy class
# from the strategy.py file. When a developer creates a new strategy,
# they will change this line to import their new class.
from strategy import NewRecursiveStrategy 

app = Flask(__name__)

@app.route('/start_evaluation', methods=['POST'])
def handle_evaluation():
    """
    This single endpoint triggers the entire evaluation process.
    It's designed to be simple and requires no input data.
    """
    try:
        # 1. Create an instance of the strategy class that was imported.
        # This class contains all the logic for fetching, parsing, and chunking.
        strategy = NewRecursiveStrategy()
        
        # 2. Call the .start() method. This is the main entry point that
        # orchestrates the work inside the strategy class.
        print("Starting the evaluation strategy...")
        chunks = strategy.start()
        print(f"Strategy finished. Returning {len(chunks)} chunks.")
        
        # 3. Return the final list of chunks as a JSON response.
        return jsonify({"chunks": chunks}), 200

    except Exception as e:
        # If anything goes wrong, return a server error with a message.
        print(f"An error occurred during evaluation: {e}")
        return jsonify({"error": str(e)}), 500
    
@app.route('/health', methods=['GET'])
def health_check():
    """A simple endpoint to confirm the service is running."""
    return jsonify({"status": "healthy"}), 200

if __name__ == "__main__":
    # This block is for local testing and is not used by Gunicorn in production.
    app.run(host='0.0.0.0', port=5001)