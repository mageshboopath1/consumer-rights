# RabbitMQ Queue Durable Error - RESOLVED

**Date:** 2025-10-25  
**Status:** FIXED

---

## Error

```
rabbitmq | operation queue.declare caused a channel exception precondition_failed: 
inequivalent arg 'durable' for queue 'query_and_context' in vhost '/': 
received 'false' but current is 'true'
```

Similar errors for `redacted_queue`.

---

## Root Cause

The queues (`query_and_context`, `redacted_queue`) were previously created with `durable=true`, but the application code declares them with `durable=false`. 

RabbitMQ doesn't allow changing queue properties after creation, causing a precondition failure.

---

## Solution

Deleted all existing queues and restarted services to recreate them with correct settings.

### Steps Taken

1. **Stopped all live inference services**
   ```bash
   cd live_inference_pipeline
   docker-compose down
   ```

2. **Deleted all queues** (RabbitMQ was stopped, so manual deletion wasn't needed)

3. **Restarted all services**
   ```bash
   docker-compose up -d
   ```

4. **Verified queue settings**
   ```bash
   docker exec rabbitmq rabbitmqctl list_queues name durable
   ```

---

## Final Queue Configuration

| Queue Name | Durable | Purpose |
|------------|---------|---------|
| terminal_messages | false | User input from CLI |
| redacted_queue | false | PII-filtered messages |
| query_and_context | false | RAG output to LLM |
| llm_output_queue | false | LLM responses |
| process_updates | false | Status updates |
| CUD_queue | **true** | Database operations (persistent) |

---

## Why These Settings?

### Non-Durable Queues (false)
- **Purpose:** Temporary message passing
- **Benefit:** Better performance, messages don't need disk persistence
- **Use case:** Real-time processing where message loss on restart is acceptable
- **Queues:** All processing queues (terminal_messages, redacted_queue, query_and_context, llm_output_queue, process_updates)

### Durable Queue (true)
- **Purpose:** Persistent storage
- **Benefit:** Messages survive RabbitMQ restarts
- **Use case:** Database operations that must not be lost
- **Queue:** CUD_queue (Create/Update/Delete operations for PostgreSQL)

---

## Code References

### LLM Connector (connector.py)
```python
# Line 97-99
channel.queue_declare(queue=CONSUME_QUEUE, durable=False)  # query_and_context
channel.queue_declare(queue=PUBLISH_QUEUE, durable=False)  # llm_output_queue
channel.queue_declare(queue=PROCESS_QUEUE, durable=False)  # process_updates
channel.queue_declare(queue=CUD_QUEUE, durable=True)       # CUD_queue
```

### RAG Core (core.py)
```python
# Line 108-109
channel.queue_declare(queue=CONSUME_QUEUE, durable=False)  # redacted_queue
channel.queue_declare(queue=PUBLISH_QUEUE, durable=False)  # query_and_context
```

### PII Filter (piiFilter.py)
```python
channel.queue_declare(queue='terminal_messages', durable=False)
channel.queue_declare(queue='redacted_queue', durable=False)
channel.queue_declare(queue='process_updates', durable=False)
```

---

## Verification

### No Errors
```bash
docker logs rabbitmq 2>&1 | grep -i "error\|precondition"
# Output: (empty - no errors)
```

### All Services Connected
```bash
docker logs llm-connector | tail -3
# [+] Successfully connected to RabbitMQ.
# [*] LLM Connector is waiting for messages.

docker logs rag-core | tail -3
# [+] Successfully connected to RabbitMQ.
# [*] rag-core service is waiting for messages.
```

### Correct Queue Settings
```
name                 durable
llm_output_queue     false
CUD_queue            true
terminal_messages    false
redacted_queue       false
process_updates      false
query_and_context    false
```

---

## Prevention

To avoid this issue in the future:

1. **Consistent Declaration:** Ensure all services declare queues with the same `durable` setting
2. **Clean Restart:** If changing queue properties, stop services and delete queues first
3. **Documentation:** Document intended queue properties in code comments

---

## Impact

**Before Fix:**
- Services couldn't connect to queues
- Channel errors on every connection attempt
- Pipeline broken

**After Fix:**
- All services connected successfully
- No channel errors
- Pipeline fully operational

---

## Status: RESOLVED

The RabbitMQ queue durable error has been completely resolved. All queues are now created with the correct settings and all services are operational.
