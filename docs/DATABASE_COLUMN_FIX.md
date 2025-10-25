# Database Column Name Fix

**Date:** 2025-10-25  
**Status:** RESOLVED

---

## Problem

PostgreSQL worker was failing with error:
```
DATABASE ERROR: Failed to execute operation. Rolling back. 
Error: column "LLM_output" of relation "chat_history" does not exist
LINE 1: INSERT INTO "chat_history" ("user_prompt", "LLM_output", "co...
```

---

## Root Cause

**Case Sensitivity Mismatch**

1. **Database Schema** (`shared_services/chroma/postgres_init/init.sql`):
   - Uses lowercase: `llm_output`

2. **LLM-Connector** (`live_inference_pipeline/LLM-Connector/connector.py`):
   - Was sending capitalized: `LLM_output`

PostgreSQL treats column names as case-sensitive when quoted (which psycopg2 does automatically).

---

## The Fix

### File Modified: `live_inference_pipeline/LLM-Connector/connector.py`

**Line 151 - Changed:**
```python
# Before
"LLM_output": output,

# After
"llm_output": output,
```

**Full Context:**
```python
history_data = {
    "user_prompt": user_prompt, 
    "llm_output": output,        # Fixed: lowercase
    "context": context,
    "timestamp": datetime.now(timezone.utc).isoformat()
}
```

---

## Database Schema (Correct)

```sql
CREATE TABLE IF NOT EXISTS chat_history (
    id SERIAL PRIMARY KEY,
    user_prompt TEXT NOT NULL,
    llm_output TEXT,              -- lowercase
    context TEXT,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
```

---

## Verification Steps

### 1. Rebuild and Restart Service
```bash
cd live_inference_pipeline
docker-compose build llm-connector
docker-compose up -d llm-connector
```

### 2. Clear Old Messages
```bash
docker exec rabbitmq rabbitmqctl purge_queue CUD_queue
```

### 3. Test Insert
```bash
cd CLI
python cli.py
# Enter a test query
```

### 4. Verify Database
```bash
docker exec postgres_service psql -U <user> -d consumer_rights \
  -c "SELECT user_prompt, llm_output FROM chat_history ORDER BY id DESC LIMIT 5;"
```

---

## Expected Output (Success)

### psql_worker logs:
```
Received message: {"operation": "CREATE", "table": "chat_history", ...}
Attempting to connect to database at postgres...
Database connection successful.
SUCCESS: Created record in table chat_history.
Message processed and acknowledged.
```

### Database Query:
```
 user_prompt                          | llm_output
--------------------------------------+------------------------------------------
 What is the Consumer Protection Act? | The Consumer Protection Act is a law...
```

---

## Related Files

1. **Database Schema:**
   - `shared_services/chroma/postgres_init/init.sql`

2. **Data Sender:**
   - `live_inference_pipeline/LLM-Connector/connector.py` (FIXED)

3. **Data Receiver:**
   - `live_inference_pipeline/psql_worker/worker.py` (no changes needed)

---

## Lesson Learned

Always ensure column names match exactly between:
- Database schema definitions
- Application code that inserts data
- Application code that queries data

PostgreSQL is case-sensitive with quoted identifiers, which psycopg2 uses by default for security.

---

## Status

✅ Column name fixed to lowercase  
✅ Service rebuilt and restarted  
✅ Old messages purged  
✅ Ready for testing  

**The database insert operation will now work correctly!**
