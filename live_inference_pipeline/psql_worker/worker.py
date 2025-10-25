# psql_worker/worker.py
import os
import time
import json
import pika
import psycopg2

# --- Configuration from Environment Variables ---
RABBITMQ_HOST = os.getenv('RABBITMQ_HOST', 'rabbitmq')
RABBITMQ_QUEUE = os.getenv('RABBITMQ_QUEUE', 'CUD_queue')

DB_HOST = os.getenv('DB_HOST', 'postgres')
DB_USER = os.getenv('DB_USER', 'myuser')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'mypass')
DB_NAME = os.getenv('DB_NAME', 'consumer_rights')

# --- Database Connection ---
def get_db_connection():
    """Attempts to connect to the PostgreSQL database."""
    max_retries = 10
    retry_delay = 5
    for i in range(max_retries):
        try:
            print(f"Attempting to connect to database at {DB_HOST}...")
            conn = psycopg2.connect(
                host=DB_HOST,
                database=DB_NAME,
                user=DB_USER,
                password=DB_PASSWORD
            )
            print("Database connection successful.")
            return conn
        except psycopg2.OperationalError as e:
            print(f"Database connection failed (Attempt {i+1}/{max_retries}): {e}")
            time.sleep(retry_delay)
    raise Exception("Failed to connect to the database after multiple retries.")

# --- RabbitMQ Connection ---
def get_rabbitmq_channel():
    """Attempts to connect to RabbitMQ and establish a channel."""
    max_retries = 10
    retry_delay = 5
    for i in range(max_retries):
        try:
            print(f"Attempting to connect to RabbitMQ at {RABBITMQ_HOST}...")
            connection = pika.BlockingConnection(
                pika.ConnectionParameters(host=RABBITMQ_HOST)
            )
            channel = connection.channel()
            # Ensure the queue exists
            channel.queue_declare(queue=RABBITMQ_QUEUE, durable=True)
            print("RabbitMQ connection and queue declaration successful.")
            return channel
        except pika.exceptions.AMQPConnectionError as e:
            print(f"RabbitMQ connection failed (Attempt {i+1}/{max_retries}): {e}")
            time.sleep(retry_delay)
    raise Exception("Failed to connect to RabbitMQ after multiple retries.")

# --- CUD Operation Logic ---
def execute_cud_operation(db_conn, operation_data):
    """Executes the CUD operation based on the message data."""
    from psycopg2 import sql
    cursor = db_conn.cursor()
    
    op = operation_data.get('operation', '').upper()
    table = operation_data.get('table')
    data = operation_data.get('data')
    condition = operation_data.get('condition') # Used for UPDATE/DELETE
    
    # Whitelist of allowed tables to prevent SQL injection
    # Based on actual database schema in shared_services/chroma/postgres_init/init.sql
    ALLOWED_TABLES = ['chat_history']
    
    if not table or not op:
        print("ERROR: Missing 'table' or 'operation' in message.")
        return False
    
    if table not in ALLOWED_TABLES:
        print(f"ERROR: Table '{table}' is not in the allowed list.")
        return False
        
    try:
        if op == 'CREATE' and data:
            columns = [sql.Identifier(col) for col in data.keys()]
            placeholders = [sql.Placeholder()] * len(data)
            values = tuple(data.values())
            
            query = sql.SQL("INSERT INTO {} ({}) VALUES ({})").format(
                sql.Identifier(table),
                sql.SQL(', ').join(columns),
                sql.SQL(', ').join(placeholders)
            )
            cursor.execute(query, values)
            print(f"SUCCESS: Created record in table {table}.")
            
        elif op == 'UPDATE' and data and condition:
            # Parse condition safely - expecting format: {"column": "value"}
            if not isinstance(condition, dict) or len(condition) != 1:
                print("ERROR: Condition must be a dict with exactly one key-value pair.")
                return False
            
            condition_col = list(condition.keys())[0]
            condition_val = list(condition.values())[0]
            
            set_clauses = [sql.SQL("{} = {}").format(sql.Identifier(col), sql.Placeholder()) 
                          for col in data.keys()]
            values = tuple(data.values()) + (condition_val,)
            
            query = sql.SQL("UPDATE {} SET {} WHERE {} = {}").format(
                sql.Identifier(table),
                sql.SQL(', ').join(set_clauses),
                sql.Identifier(condition_col),
                sql.Placeholder()
            )
            cursor.execute(query, values)
            print(f"SUCCESS: Updated {cursor.rowcount} records in table {table}.")

        elif op == 'DELETE' and condition:
            # Parse condition safely - expecting format: {"column": "value"}
            if not isinstance(condition, dict) or len(condition) != 1:
                print("ERROR: Condition must be a dict with exactly one key-value pair.")
                return False
            
            condition_col = list(condition.keys())[0]
            condition_val = list(condition.values())[0]
            
            query = sql.SQL("DELETE FROM {} WHERE {} = {}").format(
                sql.Identifier(table),
                sql.Identifier(condition_col),
                sql.Placeholder()
            )
            cursor.execute(query, (condition_val,))
            print(f"SUCCESS: Deleted {cursor.rowcount} records from table {table}.")

        else:
            print(f"WARNING: Unknown or incomplete operation: {op}. Skipping.")
            return False

        # Commit the transaction
        db_conn.commit()
        return True

    except psycopg2.Error as db_error:
        print(f"DATABASE ERROR: Failed to execute operation. Rolling back. Error: {db_error}")
        db_conn.rollback()
        return False
    except Exception as e:
        print(f"GENERIC ERROR: An unexpected error occurred: {e}")
        db_conn.rollback()
        return False
    finally:
        cursor.close()

# --- RabbitMQ Message Callback ---
def callback(ch, method, properties, body):
    """Callback function for consuming messages from RabbitMQ."""
    db_conn = None
    try:
        message_body = body.decode('utf-8')
        print(f"Received message: {message_body}")
        
        # 1. Parse Message
        try:
            operation_data = json.loads(message_body)
        except json.JSONDecodeError:
            print("ERROR: Invalid JSON format. Rejecting message.")
            ch.basic_reject(delivery_tag=method.delivery_tag, requeue=False) # Dead-letter or discard
            return
            
        # 2. Get DB Connection (or reuse if available, but for simple workers, reconnecting/getting new one can be simpler)
        # For a robust, long-running worker, connection pooling/reuse is better.
        db_conn = get_db_connection()
        
        # 3. Execute CUD
        success = execute_cud_operation(db_conn, operation_data)
        
        # 4. Acknowledge/Reject
        if success:
            ch.basic_ack(delivery_tag=method.delivery_tag)
            print("Message processed and acknowledged.")
        else:
            # Requeue=True will put the message back on the queue. Use False for bad data to prevent loops.
            ch.basic_reject(delivery_tag=method.delivery_tag, requeue=False) 
            print("Message failed processing and rejected (not requeued).")
            
    except Exception as e:
        print(f"CRITICAL ERROR in callback: {e}. Rejecting message.")
        # Rejects the message if any critical failure happens outside the CUD logic (e.g., DB connection fails)
        ch.basic_reject(delivery_tag=method.delivery_tag, requeue=True) # Requeue if critical
    finally:
        if db_conn:
            db_conn.close()


# --- Main Runner ---
def main():
    """Main function to start the worker."""
    try:
        channel = get_rabbitmq_channel()
        
        channel.basic_consume(
            queue=RABBITMQ_QUEUE,
            on_message_callback=callback,
            auto_ack=False  # Crucial: We manually acknowledge/reject messages
        )
        
        print(' [*] Waiting for messages. To exit press CTRL+C')
        channel.start_consuming()

    except Exception as e:
        print(f"Worker failed to start or encountered a critical error: {e}")
        # Exit the container if critical error prevents consumption
        exit(1)

if __name__ == '__main__':
    main()