# Token Stats Client API Specifications

Comprehensive documentation for integrating the Token Stats API on the client side.

## Table of contents

- Overview
- Authentication
- Available endpoints
- Data models
- Implementation examples
- Error handling
- Best practices

## Overview

The Token Stats API allows viewing and managing token consumption statistics for users of the AI Server.

**Base URL:** `https://your-server.com/api/token-stats`

**Response format:** JSON

**Authentication:** JWT

## Authentication

All endpoints require a JWT in the `Authorization` header:

```http
Authorization: Bearer <token>
```

The token is obtained through the login endpoint `/api/auth/login`.

### Roles and permissions

| Role | Permissions |
|------|-------------|
| `GUEST` | Read own statistics only |
| `USER` | Read own statistics and statistics of their guests |
| `ADMIN` | Full access to all statistics |

## Available endpoints

### 1. Personal statistics

#### GET /token-stats/self
Retrieves the token statistics for the authenticated user.

**Permissions:** GUEST, USER, ADMIN

**Response:**
```json
{
  "user_id": 1,
  "total_prompt_tokens": 1500,
  "total_completion_tokens": 2000,
  "total_tokens": 3500,
  "total_requests": 25
}
```

---

#### GET /token-stats/total/self
Retrieves only the total tokens consumed.

**Permissions:** GUEST, USER, ADMIN

**Response:**
```json
{
  "user_id": 1,
  "total_tokens": 3500
}
```

---

#### GET /token-stats/history/self?limit=100
Retrieves the detailed request history.

**Permissions:** GUEST, USER, ADMIN

**Query parameters:**
- `limit` (optional): Number of records (1-1000, default: 100)

**Response:**
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

---

### 2. Guest statistics

#### GET /token-stats/guest/{guest_id}
Retrieves statistics for a guest user.

**Permissions:** USER, ADMIN

**Path parameters:**
- `guest_id`: ID of the guest user

**Response:**
```json
{
  "user_id": 5,
  "total_prompt_tokens": 800,
  "total_completion_tokens": 1200,
  "total_tokens": 2000,
  "total_requests": 15
}
```

**Errors:**
- `404`: Guest not found
- `403`: The guest does not belong to you

---

#### GET /token-stats/total/guest/{guest_id}
Guest total tokens.

**Permissions:** USER, ADMIN

**Response:**
```json
{
  "user_id": 5,
  "total_tokens": 2000
}
```

---

#### GET /token-stats/history/guest/{guest_id}?limit=50
Guest history.

**Permissions:** USER, ADMIN

**Query parameters:**
- `limit` (optional): Number of records (1-1000, default: 100)

**Response:** Same as `/history/self`

---

### 3. User statistics (Admin)

#### GET /token-stats/user/{user_id}
Statistics for a specific user.

**Permissions:** ADMIN only

**Path parameters:**
- `user_id`: ID of the user

**Response:**
```json
{
  "user_id": 10,
  "total_prompt_tokens": 5000,
  "total_completion_tokens": 7000,
  "total_tokens": 12000,
  "total_requests": 100
}
```

---

#### GET /token-stats/total/user/{user_id}
Total tokens for a user.

**Permissions:** ADMIN only

**Response:**
```json
{
  "user_id": 10,
  "total_tokens": 12000
}
```

---

#### GET /token-stats/history/user/{user_id}?limit=100
User history.

**Permissions:** ADMIN only

**Query parameters:**
- `limit` (optional): Number of records (1-1000, default: 100)

**Response:** Same as `/history/self`

---

### 4. Bot statistics

#### GET /token-stats/bot/{bot_id}
Consumption statistics for a bot.

**Permissions:** USER, ADMIN

**Path parameters:**
- `bot_id`: ID of the bot

**Response:**
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

---

### 5. Global statistics (Admin)

#### GET /token-stats/all-users
Statistics across all users.

**Permissions:** ADMIN only

**Response:** Partial example documented in TOKEN_TRACKING_README.md

## Data models

Add TypeScript interfaces in client code to match API responses. Example types are provided in `client_examples/token-stats.types.ts`.

## Implementation examples

Includes examples for TypeScript, Angular, React, Vue and Python in the client_examples folder.

## Error handling

The API returns standard HTTP status codes. Clients should handle 401/403 for auth/permission issues, 404 for not found, and 400 for invalid parameters.

## Best practices

- Cache results for 5 minutes where appropriate
- Use pagination and `limit` parameter for history endpoints
- Respect rate limits

