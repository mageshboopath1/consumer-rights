import json
import os
import re
import sys
import time
from datetime import datetime, timezone

import pika

# Import security modules
try:
    from security.cost_limiter import cost_limiter
    from security.ddos_protection import ddos_protection
    from security.rate_limiter import rate_limiter

    SECURITY_ENABLED = True
    print("[i] Security modules loaded successfully")
except ImportError as e:
    print(f"[!] Warning: Security modules not available: {e}")
    SECURITY_ENABLED = False

    # Create dummy objects if security not available
    class DummyLimiter:
        def is_allowed(self, ip):
            return True, 0, "OK"

        def check_burst_attack(self, ip):
            return False, "OK"

        def check_distributed_attack(self, ip):
            return False, "OK"

        def can_process_query(self):
            return True, "OK", {}

        def record_query(self):
            pass

    rate_limiter = DummyLimiter()
    ddos_protection = DummyLimiter()
    cost_limiter = DummyLimiter()

connection = None
for i in range(10):
    try:
        connection_params = pika.ConnectionParameters("rabbitmq", heartbeat=600)
        connection = pika.BlockingConnection(connection_params)
        print("pii-filter successfully connected to RabbitMQ.")
        break
    except pika.exceptions.AMQPConnectionError:
        print(f"Connection attempt {i+1}/10 failed. Retrying in 5 seconds...")
        time.sleep(5)

if not connection:
    print("Error: Could not connect to RabbitMQ after multiple attempts.")
    sys.exit(1)

channel = connection.channel()

channel.queue_declare(queue="terminal_messages", durable=False)
channel.queue_declare(queue="redacted_queue", durable=False)
channel.queue_declare(queue="process_updates", durable=False)

channel.basic_qos(prefetch_count=1)
print(" [*] pii-filter service is waiting for messages...")


def process_message(body, client_ip="127.0.0.1"):
    text = body.decode()
    print(f" [x] Received from 'terminal_messages': '{text}'")

    # SECURITY CHECKS
    if SECURITY_ENABLED:
        # 1. Rate Limiting
        allowed, retry_after, reason = rate_limiter.is_allowed(client_ip)
        if not allowed:
            error_msg = f"Rate limit exceeded. Try again in {retry_after}s."
            if "BLOCKED" in reason:
                error_msg = "IP blocked due to excessive requests."

            print(f"[!] {reason}: IP {client_ip[:8]}... blocked for {retry_after}s")
            return (
                json.dumps(
                    {"error": error_msg, "blocked": True, "retry_after": retry_after}
                ),
                True,
            )

        # 2. DDoS Detection
        is_burst, burst_reason = ddos_protection.check_burst_attack(client_ip)
        if is_burst:
            print(f"[!] BURST ATTACK: {burst_reason}")
            return (
                json.dumps(
                    {"error": "Too many requests too quickly.", "blocked": True}
                ),
                True,
            )

        is_ddos, ddos_reason = ddos_protection.check_distributed_attack(client_ip)
        if is_ddos:
            print(f"[!] DDOS DETECTED: {ddos_reason}")

        # 3. Cost Limiting
        can_process, cost_reason, cost_stats = cost_limiter.can_process_query()
        if not can_process:
            print(f"[!] BUDGET EXCEEDED: {cost_reason}")
            print(
                f"    Daily: {cost_stats['daily']['cost']}/{cost_stats['daily']['budget']}"
            )
            print(
                f"    Monthly: {cost_stats['monthly']['cost']}/{cost_stats['monthly']['budget']}"
            )

            return (
                json.dumps(
                    {
                        "error": "Service temporarily unavailable (budget limit). Try tomorrow.",
                        "blocked": True,
                        "stats": cost_stats,
                    }
                ),
                True,
            )

        # Record query for cost tracking
        cost_limiter.record_query()
        print(
            f"[i] Budget: Daily {cost_stats['daily']['percentage']}, Monthly {cost_stats['monthly']['percentage']}"
        )

    # PII FILTERING
    name_regex = (
        r"\b(?!Mr\.|Ms\.|Dr\.|Mrs\.|Mr|Ms|Dr|and)\b([A-Z][a-z]+)\s+([A-Z][a-z]+)\b"
    )
    email_regex = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
    phone_regex = r"(\(\d{3}\)\s*\d{3}-\d{4}|\d{3}-\d{3}-\d{4})"

    redacted_text = re.sub(email_regex, "[EMAIL]", text)
    redacted_text = re.sub(phone_regex, "[PHONE]", redacted_text)
    redacted_text = re.sub(name_regex, "[NAME]", redacted_text)

    status_payload = {
        "type": "stage_complete",
        "stage": "pii_filter",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    channel.basic_publish(
        exchange="", routing_key="process_updates", body=json.dumps(status_payload)
    )
    print(f" [>] Sent status update to 'process_updates'")

    return redacted_text, False


def callback(ch, method, properties, body):
    # Extract client IP from headers (if available)
    client_ip = "127.0.0.1"
    if properties.headers and "client_ip" in properties.headers:
        client_ip = properties.headers["client_ip"]

    result, is_blocked = process_message(body, client_ip)

    # Send result to next queue
    ch.basic_publish(
        exchange="",
        routing_key="redacted_queue",
        body=result.encode("utf-8") if isinstance(result, str) else result,
    )
    print(f" [>] Sent to 'redacted_queue': '{result[:100]}...'")

    ch.basic_ack(delivery_tag=method.delivery_tag)


channel.basic_consume(queue="terminal_messages", on_message_callback=callback)

try:
    channel.start_consuming()
except KeyboardInterrupt:
    print("\nInterrupted.")
finally:
    if connection.is_open:
        connection.close()
