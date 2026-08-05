# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Bot Factory** is a full-stack AI bot creation and management platform. Users can create custom AI chatbots with LLM backends, customize bot appearance via an avatar builder, manage knowledge bases with RAG (Retrieval-Augmented Generation), and track token consumption.

The codebase is split into two main components:
- **Client**: Angular 18 frontend (TypeScript, Bootstrap 5, RxJS)
- **Server**: Python Flask backend with SQLAlchemy ORM and LangChain integration

## Development Commands

### Quick Start (Docker Compose - Recommended)
```bash
# One-time setup
make setup

# Start all services
make dev

# View logs
make logs

# Run tests
make test

# Stop services
make down
```

### Using Make (All commands)
See output from `make help` for complete list. Key commands:
```bash
make setup           # Setup project (create .env, install deps)
make dev             # Start development with Docker
make dev-client      # Start only Angular dev server
make dev-server      # Start only Flask dev server (local)
make test            # Run all tests
make test-server     # Run backend tests
make test-client     # Run frontend tests
make migrate         # Run database migrations
make db-shell        # Connect to MySQL shell
make logs            # View Docker logs
make clean-docker    # Remove containers and volumes
```

### Client (Frontend)
```bash
cd client
npm start                    # Development server on localhost:4200 (local)
npm run build               # Production build
npm run build:prod          # Production build with optimization
npm run watch               # Build with watch mode
npm test                    # Run unit tests via Karma
```

### Server (Backend) - Local Setup
```bash
cd server
cp .env.example .env        # Fill in real values (DB, admin creds)
uv sync                     # Create .venv and install dependencies
./z-run.sh                  # Syncs deps, loads .env, starts Flask on port 444
uv run pytest test/         # Run unit tests
uv run pytest test/test_file.py::test_name  # Run specific test
```

### Database (Docker)
```bash
make migrate               # Run all migrations
make db-shell              # Connect to MySQL shell
docker-compose exec -w /app/db api alembic upgrade head    # Upgrade schema
docker-compose exec -w /app/db api alembic downgrade -1    # Revert last migration
```

## Architecture Overview

### Full-Stack Data Flow

1. **Frontend (Angular)** → HTTP requests via services
2. **JWT Interceptor** → Attaches authentication tokens
3. **Backend (Flask)** → REST API endpoints with role-based access control
4. **Database (MySQL)** → SQLAlchemy ORM models
5. **External Services** → ChromaDB, LLM providers

### Directory Structure

```
bot-factory/
├── client/                    # Angular 18 frontend
│   ├── src/app/
│   │   ├── components/        # Feature components (bot-list, chat, admin, etc.)
│   │   ├── services/          # API services and business logic
│   │   ├── models/            # TypeScript interfaces
│   │   ├── guards/            # Route protection
│   │   ├── interceptors/      # HTTP and JWT handling
│   │   └── styles/            # Theme system (dark/light)
│   └── CLAUDE.md              # Client-specific guidance
│
└── server/                    # Python Flask backend
    ├── ai_server/
    │   ├── api_controllers/   # REST endpoints organized by feature
    │   ├── services/          # Business logic (RAG, chat, etc.)
    │   ├── dao/               # SQLAlchemy models and database access
    │   ├── config/            # Configuration, validators, constants
    │   ├── decorators/        # Custom decorators (@role_required, @jwt_required)
    │   ├── dto/               # Data transfer objects for API requests/responses
    │   ├── log/               # Logging configuration
    │   └── main.py            # Flask app factory and blueprint registration
    ├── db/alembic/            # Database schema migrations
    ├── test/                  # Unit tests
    ├── doc/                   # Documentation and implementation guides
    └── pyproject.toml         # Python dependencies (managed with uv)
```

### Key Backend Services

These services implement core business logic and should be consulted when developing features:

- **`rag_svc.py`** - RAG pipeline (document ingestion, vector storage, semantic search)
- **`chat_svc.py`** - Chat message handling and history
- **`bot_svc.py`** - Bot CRUD and lifecycle management
- **`token_stats_svc.py`** - Token usage tracking and analytics
- **`knowledge_svc.py`** - Knowledge base document management
- **`avatar_svc.py`** - Avatar customization and storage
- **`user_svc.py`** - User management and authentication

### API Blueprint Organization

Backend endpoints are organized by feature using Flask blueprints:

- `/api/auth/*` - Authentication (login, register, refresh tokens)
- `/api/bot/*` - Bot CRUD operations
- `/api/bot-parameters/*` - Bot configuration (personality, behavior)
- `/api/bot-assignment/*` - User-bot relationships
- `/api/avatar/*` - Avatar builder and customization
- `/api/knowledge/*` - Knowledge base document upload/management
- `/api/rag/*` - RAG ask/answer endpoints for chat
- `/api/token-stats/*` - Token usage statistics and analytics
- `/api/users-admin/*` - User management (admin only)
- `/api/iframe-security/*` - Iframe embedding with frame tokens

### Database Models

All models are defined in `server/ai_server/dao/database.py`. Key models:

- **User** - User accounts with roles (Admin, User, Guest, Iframe)
- **Bot** - Bot definitions (one per user, contains personality/system prompts)
- **BotParameters** - Extended bot configuration (communication style, capabilities, etc.)
- **BotAvatar** - SVG-based avatar components (body, eyes, hat, mouth, colors)
- **BotAssignment** - Relationships between users and bots
- **Knowledge** - Documents in knowledge base (stored in ChromaDB)
- **Message** - Chat message history with token counts
- **TokenUsage** - Per-user, per-bot token consumption tracking

### Authentication & Authorization

- **JWT Tokens**: Used for all API authentication. Refresh tokens handled automatically by frontend interceptor.
- **Role-Based Access Control (RBAC)**: Roles defined in `config/constant.py` with `@role_required` decorator
- **Route Guards**: Frontend route guards in `app.routes.ts` (currently commented out for development)

### Integration Points

**LLM Providers** (via LangChain):
- Mistral AI, Ollama, Hugging Face, or custom models
- Token counting via LangChain callbacks (automatically tracked)
- Context window varies by provider

**ChromaDB**:
- Vector database for RAG knowledge storage
- Embedding generation with fastembed
- Persistence configurable via environment variables

## Configuration & Environment

### Required Environment Variables

```
# Database
DATABASE_URL=mysql+pymysql://user:password@host:3306/database_name

# JWT
JWT_SECRET_KEY=your-secret-key-here
JWT_ACCESS_TOKEN_EXPIRES=3600

# Logging
LOGGER_LVL=INFO
OPERATIONAL_LOG_FILE=ai-server-{}.log

# ChromaDB
CHROMA_CONTAINER=true
PERSIST=true
PERSIST_DIRECTORY=chroma_db_2

# Admin Defaults
SUPER_ADMIN_LOGIN=admin@example.com
SUPER_ADMIN_PASSWORD=password
```

### Flask Configuration

Main configuration is in `ai_server/config/config.py`. The app uses environment-based configs (development, testing, production).

## Key Development Patterns

### Backend Patterns

**Services Pattern**: Business logic lives in services, not controllers
```python
# controllers/rest_bot.py
bot_data = bot_svc.get_bot_by_id(bot_id)  # Call service

# services/bot_svc.py
def get_bot_by_id(bot_id):
    bot = Bot.query.get(bot_id)  # Database access via ORM
    return bot
```

**Decorators**: Use available decorators for common patterns
```python
@bp.route('/admin/users')
@role_required(['Admin'])           # Enforce role
@jwt_required()                     # Enforce authentication
def get_all_users():
    pass
```

**DTOs**: Use data transfer objects for request/response validation
```python
# dto/bot_dto.py
class BotCreateRequest:
    name: str
    description: str

# controller
request = BotCreateRequest(**request.json)  # Validation
```

**Validation**: Input validation via config/validator.py
```python
validator.validate_email(email)
validator.validate_password(password)
```

### Frontend Patterns

**Services**: API communication via typed services
```typescript
// services/bot.service.ts
getBotById(id: string): Observable<Bot> {
  return this.http.get<Bot>(`/api/bot/${id}`);
}

// components/bot-detail.component.ts
this.botService.getBotById(id).subscribe(bot => this.bot = bot);
```

**Async Pipe**: Use async pipe for automatic subscription management in templates
```html
<div>{{ (bot$ | async)?.name }}</div>
```

**RxJS Operators**: Leverage common RxJS patterns for data transformation
```typescript
this.botService.getAllBots().pipe(
  map(bots => bots.filter(b => b.active)),
  catchError(err => this.handleError(err))
).subscribe();
```

## Token Tracking System

Token usage is automatically tracked when using the RAG service:

1. When `rag_svc.ask()` is called, LangChain's `TokenCountingCallback` counts tokens
2. Tokens are stored in the `Message` table with the user ID and bot ID
3. `token_stats_svc` aggregates this data for analytics

**Important**: Do not manually create token records when using RAG. The system tracks automatically.

## Documentation

Detailed implementation guides are in `server/doc/`:

- **[server/db/README.md](server/db/README.md)** - Alembic setup and database migration commands
- **CALLBACK_IMPLEMENTATION.md** - Token counting with LangChain
- **IMPLEMENTATION_SUMMARY.md** - Token tracking system overview

For frontend-specific guidance, see `client/CLAUDE.md`.

## Common Development Tasks

### Adding a New Bot Feature

1. Add database model to `dao/database.py`
2. Create data access methods in the same model file
3. Add business logic to appropriate service in `services/`
4. Create REST endpoint in `api_controllers/`
5. Create frontend service in `client/src/app/services/`
6. Create/update components in `client/src/app/components/`
7. Update routing in `client/src/app/app.routes.ts`

### Adding RAG Functionality

1. Use `rag_svc` methods for document processing
2. Leverage LangChain's built-in callbacks for token counting
3. Store metadata in knowledge base via `knowledge_svc`
4. Test retrieval quality with sample queries

### Integrating New LLM Provider

1. Add LangChain wrapper to `services/rag_svc.py`
2. Configure model parameters in `config/config.py`
3. Update frontend model selection UI
4. Test token counting works correctly (system auto-tracks)

## Testing

### Running Tests

```bash
# Backend - run all tests
cd server && python -m pytest test/

# Backend - run specific test
python -m pytest test/test_file.py::test_name

# Frontend - run all tests
cd client && npm test

# Frontend - run specific test
npm test -- --include='**/auth.service.spec.ts'
```

### Writing Tests

**Backend**: Use pytest with fixtures in `conftest.py`
**Frontend**: Use Jasmine/Karma with TestBed for component testing

## Performance Considerations

1. **Token Counting**: Automatic via callbacks - no manual tracking needed
2. **ChromaDB**: Vector similarity search is efficient; configure persistence appropriately
3. **JWT Expiration**: Frontend handles refresh automatically via interceptor
4. **Message History**: Consider pagination for large conversation histories
5. **Database Indexes**: Ensure `User.id`, `Bot.id`, `Message.bot_id` are indexed

## Security Notes

1. **JWT Secrets**: Use strong secrets in production
2. **CORS**: Configured in `main.py` - update origins for production
3. **Frame Tokens**: Iframe embedding uses separate token validation
4. **Role Validation**: Always use `@role_required` on admin endpoints
5. **Input Validation**: Use validators from `config/validator.py`

## Debugging Tips

- **Frontend**: Angular DevTools extension for RxJS debugging
- **Backend**: Enable logging via `LOGGER_LVL=DEBUG` environment variable
- **Database**: Check `operational_log_*.log` for transaction issues
- **ChromaDB**: Vector similarity issues often indicate embedding mismatch

## Git Workflow

The main branch is `main`. When making changes:

1. Create a feature branch from `main`
2. Make commits with clear messages
3. Test locally before pushing
4. Create PR for review
5. Merge to `main` after approval

Recent commits reference core features like bot factory client/server setup.
