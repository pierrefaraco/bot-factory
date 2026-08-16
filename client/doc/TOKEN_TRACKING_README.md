# Token Counting System

This document explains how to use the new per-user token counting system.

## Overview

The token counting system enables:
- Tracking token consumption for each user
- Obtaining detailed statistics per user or per bot
- Inspecting request history and token usage
- Managing quotas and usage limits

## Architecture

### 1. Database table

A new `token_usage` table has been added in [ai_server/dao/database.py](ai_server/dao/database.py#L331-L360):

```python
class TokenUsage(db.Model):
    id: int                    # Unique ID
    user_id: int               # User ID
    bot_id: int                # Bot ID used
    session_id: int            # Session ID (optional)
    prompt_tokens: int         # Number of prompt tokens
    completion_tokens: int     # Number of completion tokens
    total_tokens: int          # Total tokens
    timestamp: datetime        # Timestamp of usage
    model_name: str            # Name of the model used (optional)
```

### 2. Tracking service

The service [token_tracking_svc.py](ai_server/services/token_tracking_svc.py) provides the following methods:

- `record_token_usage()` - Record a token usage entry
- `get_user_total_tokens()` - Retrieve the total tokens for a user
- `get_user_token_stats()` - Detailed statistics for a user
- `get_user_token_history()` - A user's request history
- `get_bot_token_stats()` - Statistics for a bot
- `get_all_users_token_stats()` - Statistics across all users

### 3. LLM callback

An automatic callback was added in [llm_svc.py](ai_server/services/llm_svc.py#L13-L48) that records token usage automatically after each LLM call.

### 4. Integration into the RAG service

The RAG service was updated in [rag_svc.py](ai_server/services/rag_svc.py) to automatically enable token tracking for requests.

## REST API

The following endpoints are available under `/api/token-stats`:

### For users

#### Get own statistics
```
GET /api/token-stats/self
```
Response:
```json
{
  "user_id": 1,
  "total_prompt_tokens": 1500,
  "total_completion_tokens": 2000,
  "total_tokens": 3500,
  "total_requests": 25
}
```

#### Get own history
```
GET /api/token-stats/history/self?limit=50
```
Response:
```json
{
  "history": [
    {
      "id": 123,
      "bot_id": 5,
      "session_id": 10,
      "prompt_tokens": 50,
      "completion_tokens": 80,
      "total_tokens": 130,
      "timestamp": "2025-11-28 14:30:00",
      "model_name": "mistral-medium"
    }
  ]
}
```

#### Get total tokens consumed
```
GET /api/token-stats/total/self
```
Response:
```json
{
  "user_id": 1,
  "total_tokens": 3500
}
```

### For users with guests

#### Guest statistics
```
GET /api/token-stats/guest/{guest_id}
```

#### Guest history
```
GET /api/token-stats/history/guest/{guest_id}?limit=50
```

#### Guest total tokens
```
GET /api/token-stats/total/guest/{guest_id}
```

### For administrators

#### Statistics for a specific user
```
GET /api/token-stats/user/{user_id}
```

#### History for a specific user
```
GET /api/token-stats/history/user/{user_id}?limit=100
```

#### Total tokens for a user
```
GET /api/token-stats/total/user/{user_id}
```

#### Bot statistics
```
GET /api/token-stats/bot/{bot_id}
```
Response:
```json
{
  "bot_id": 5,
  "total_prompt_tokens": 15000,
  "total_completion_tokens": 20000,
  "total_tokens": 35000,
  "total_requests": 250,
  "unique_users": 10
}
```

#### Statistics for all users
```
GET /api/token-stats/all-users
```
Response:
```json
{
  "users": [
    {
      "user_id": 1,
      "total_prompt_tokens": 1500,
      "total_completion_tokens": 2000,
      "total_tokens": 3500,
      "total_requests": 25
    },
    {
      "user_id": 2,
      "total_prompt_tokens": 800,
      "total_completion_tokens": 1200,
      "total_tokens": 2000,
      "total_requests": 15
    }
  ]
}
```

## Authentication

All endpoints require JWT authentication. Allowed roles:
- `ADMIN_ROLE`: Full access to all statistics
- `USER_ROLE`: Access to own stats and those of their guests
- `GUEST_ROLE`: Access only to their own statistics

## Database migration

After deploying these changes, create the new table:

```bash
# If using Flask-Migrate
flask db migrate -m "Add token_usage table"
flask db upgrade

# Or if using db.create_all()
# The table will be created automatically at application startup
```

## Usage example in Python

```python
from ai_server.services.token_tracking_svc import TokenTrackingService

# Create an instance of the service
token_svc = TokenTrackingService()

# Record token usage
token_svc.record_token_usage(
    user_id=1,
    bot_id=5,
    prompt_tokens=50,
    completion_tokens=80,
    total_tokens=130,
    session_id=10,
    model_name="mistral-medium"
)

# Get user stats
stats = token_svc.get_user_token_stats(user_id=1)
print(f"Total tokens: {stats['total_tokens']}")

# Get history
history = token_svc.get_user_token_history(user_id=1, limit=50)
for record in history:
    print(f"Request at {record['timestamp']}: {record['total_tokens']} tokens")
```

## Automatic operation

The system automatically records tokens consumed for each request made via the RAG service. No manual developer action is required.

When a user makes a request:
1. The RAG service creates an LLM with the tracking callback enabled
2. During the request, the callback collects token information
3. Data is automatically stored in the database
4. Statistics are immediately available via the API endpoints

## Limitations and considerations

- API request limits are enforced (max 1000 records for history)
- Timestamps are stored as strings for compatibility
- Tracking is enabled only when `user_id` and `bot_id` are provided
- Streaming tokens are also counted

## Support

For questions or issues, check the application logs or contact the development team.
