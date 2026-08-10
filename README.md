# Bot Factory

A full-stack AI bot creation and management platform that empowers users to create, customize, and deploy intelligent chatbots with advanced features like knowledge base management and token tracking.

![Bot Factory](https://img.shields.io/badge/Angular-18-red) ![Flask](https://img.shields.io/badge/Flask-2.3-green) ![Python](https://img.shields.io/badge/Python-3.12+-blue) ![Docker](https://img.shields.io/badge/Docker-Compose-blue) ![License](https://img.shields.io/badge/License-MIT-green)

---

## 🌟 Features

### Core Capabilities
- **Bot Creation & Management** - Create and customize AI bots with personalized parameters
- **Avatar Builder** - SVG-based customizable bot avatars (body, eyes, hat, mouth, colors)
- **Knowledge Base Management** - Upload and manage documents with RAG (Retrieval-Augmented Generation)
- **Real-time Chat** - Interactive conversations with bots powered by LLM providers
- **Token Tracking** - Automatic token usage tracking and analytics

### Advanced Features
- **Multiple LLM Support** - Integration with Mistral AI, Ollama, Hugging Face, and more
- **Vector Search** - ChromaDB-powered semantic search for knowledge retrieval
- **JWT Authentication** - Secure token-based authentication with refresh tokens
- **Role-Based Access Control** - Admin, User, Guest, and Iframe roles
- **Iframe Embedding** - Deploy bots on external websites with security tokens

---

## 🏗️ Architecture

### Tech Stack

**Frontend**
- Angular 18 with TypeScript
- Bootstrap 5 + Custom SCSS themes (dark/light modes)
- RxJS for reactive programming
- JWT handling with interceptors

**Backend**
- Python Flask 2.3
- SQLAlchemy 2.0 ORM
- LangChain ecosystem for LLM integration
- ChromaDB for vector storage (dedicated container)
- MySQL for persistence
- uv for dependency management

**Infrastructure**
- Docker & Docker Compose
- Nginx as reverse proxy
- Alembic for database migrations
- pytest for backend testing
- Karma/Jasmine for frontend testing

### System Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   Frontend (Angular 18)                 │
│              Bootstrap 5 + Dark/Light Themes            │
└────────────────────┬────────────────────────────────────┘
                     │ HTTP/REST + JWT
                     │
┌────────────────────▼────────────────────────────────────┐
│              Nginx (Reverse Proxy)                      │
│         - API routing to Flask backend                  │
│         - Static file serving                           │
│         - Security headers                              │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│          Flask Backend (Python 3.12+)                   │
│  ┌─────────────┬──────────────┬──────────────┐          │
│  │   REST API  │  Middleware  │  Decorators  │          │
│  └──────┬──────┴──────┬───────┴────────┬─────┘          │
│         │             │                │                │
│  ┌──────▼─────┬──────▼──────┬────────▼────┐            │
│  │  Services  │  Database   │  External   │            │
│  │  Layer     │   (ORM)     │  Services   │            │
│  └────────────┴─────────────┴─────────────┘            │
└──────────────────┬──────────────────────────────────────┘
                   │
    ┌──────────────┴──────────────┐
    │                             │
┌───▼────┐                  ┌─────▼────┐
│ MySQL  │                  │ChromaDB  │
│        │                  │  Vector  │
└────────┘                  └──────────┘
```

---

## 🚀 Quick Start

### Prerequisites
- **Docker & Docker Compose** (recommended)
- OR **Python 3.12+** with [uv](https://docs.astral.sh/uv/) and **Node.js 18+** (local development)
- **MySQL 8.0+** and **ChromaDB** (if running locally without Docker)

### Setup with Docker (Recommended)

```bash
# Clone the repository
git clone https://github.com/your-org/bot-factory.git
cd bot-factory

# Create environment file
cp .env.example .env

# Edit .env and configure (optional for development)
nano .env  # or use your editor

# Start all services
make setup
make dev

# Services are now running:
# - Frontend: http://localhost:4200
# - Backend API: http://localhost:444
# - MySQL: localhost:3306
```

### Quick Commands

```bash
make help              # Show all available commands
make dev               # Start development environment
make db-only           # Start only the MySQL container
make chromadb-only     # Start only the ChromaDB container
make test              # Run all tests
make logs              # View service logs
make migrate           # Run database migrations
make db-shell          # Connect to database
make clean-docker      # Clean up Docker resources
```

For detailed setup instructions, see [DEVELOPMENT.md](DEVELOPMENT.md).

---

## 📖 Documentation

- **[DEVELOPMENT.md](DEVELOPMENT.md)** - Complete development setup and workflow guide
- **[CLAUDE.md](CLAUDE.md)** - Architecture overview and development patterns (for AI assistants)
- **[client/CLAUDE.md](client/CLAUDE.md)** - Frontend-specific guidance
- **[server/doc/](server/doc/)** - Detailed implementation guides

### Server Documentation
- `ALEMBIC_SETUP.md` - Database migration commands
- `CALLBACK_IMPLEMENTATION.md` - LLM token counting with LangChain
- `IMPLEMENTATION_SUMMARY.md` - Token tracking system overview

---

## 🏃 Running the Project

### Option 1: Docker Compose (Easiest)

```bash
# Initial setup
make setup

# Start services
make dev

# Stop services
make down

# View logs
make logs
make logs-api        # Backend only
make logs-db         # Database only
make logs-chromadb   # ChromaDB only
```

### Option 2: Local Development

**Backend:**
```bash
cd server
cp .env.example .env   # Fill in real values
uv sync                # Creates .venv and installs dependencies
./z-run.sh             # Syncs deps, loads .env, starts on port 444
```

**Frontend (separate terminal):**
```bash
cd client
npm install
npm start          # Starts on port 4200
```

### Option 3: Development Mode (Individual Services)

```bash
# Start only MySQL container
make db-only

# Start only ChromaDB container
make chromadb-only

# Start only frontend dev server
make dev-client

# Start only backend (requires local setup)
make dev-server

# Run in separate terminals
```

---

## 🧪 Testing

```bash
# Run all tests
make test

# Backend tests only
make test-server
make test-server-single TEST=test/test_file.py::test_name

# Frontend tests only
make test-client
make test-client-watch    # Watch mode

# With coverage
cd server && uv run --extra test pytest test/ --cov=ai_server
```

---

## 🗄️ Database

### Configure the MySQL Container

MySQL runs as its own service (`db`) in `docker-compose.yml`, using `mysql:8.0` with a healthcheck (`mysqladmin ping`) that the `api` service waits on before starting.

Credentials come from `.env` at the repo root (defaults shown, override as needed):
```bash
MYSQL_ROOT_PASSWORD=root
MYSQL_DATABASE=botcraft
MYSQL_USER=botcraft_user
MYSQL_PASSWORD=123456789
```

Start just the database container:
```bash
make db-only        # docker-compose up -d db
# ✓ MySQL running on localhost:3306, data persisted in the `mysql_data` volume
```

Point the backend at it via `server/.env`:
```bash
# Running the api inside docker-compose (same network, resolves the service by name):
DATABASE_URL=mysql+pymysql://botcraft_user:123456789@db:3306/botcraft?charset=utf8mb4

# Running the api locally with `./z-run.sh` / `uv run`, from the host or a container
# that shares the host's Docker networking (port 3306 is published to the host):
DATABASE_URL=mysql+pymysql://botcraft_user:123456789@127.0.0.1:3306/botcraft?charset=utf8mb4
```
> If you're working from a separate dev/devcontainer (not the host, not part of
> `docker-compose`), see [Database Connection Error](#database-connection-error) below —
> `127.0.0.1` won't resolve to `botfactory-db` in that case.

### Initialize Database
```bash
make migrate       # Run all pending migrations (inside the `api` Docker container)
make db-upgrade     # Run all pending migrations locally via uv (uses DATABASE_URL from server/.env)
```

### Database Operations
```bash
# Connect to MySQL shell
make db-shell

# Create new migration
docker-compose exec -w /app/db api alembic revision --autogenerate -m "Description"

# Revert last migration
docker-compose exec -w /app/db api alembic downgrade -1

# View migration history
docker-compose exec -w /app/db api alembic current
```

---

## 🔧 Configuration

### Environment Variables

Copy `.env.example` to `.env` and configure:

```bash
# Database
MYSQL_ROOT_PASSWORD=root
MYSQL_DATABASE=botcraft
MYSQL_USER=botcraft_user
MYSQL_PASSWORD=123456789

# JWT
JWT_SECRET_KEY=your-secret-key-change-in-production

# LLM/RAG
CHROMA_CONTAINER=true
CHROMA_HOST=chromadb
CHROMA_PORT=8000
PERSIST=true
PERSIST_DIRECTORY=chroma_db_2

# See .env.example for all available options
```

### For Production

1. Use strong, random `JWT_SECRET_KEY`
2. Configure proper SSL/TLS certificates
3. Use environment-specific `.env.production`
4. Configure secret management (GitHub Secrets, AWS Secrets Manager, etc.)
5. Enable logging and monitoring
6. Review CORS settings in `server/ai_server/main.py`

---

## 📁 Project Structure

```
bot-factory/
├── client/                       # Angular 18 Frontend
│   ├── src/
│   │   ├── app/
│   │   │   ├── components/      # Feature components
│   │   │   ├── services/        # API services
│   │   │   ├── models/          # TypeScript interfaces
│   │   │   ├── guards/          # Route protection
│   │   │   ├── interceptors/    # HTTP interceptors
│   │   │   └── styles/          # Theme system
│   │   └── index.html
│   ├── package.json
│   ├── angular.json
│   ├── Dockerfile
│   ├── nginx.conf
│   └── CLAUDE.md
│
├── server/                       # Python Flask Backend
│   ├── ai_server/
│   │   ├── api_controllers/     # REST endpoints
│   │   ├── services/            # Business logic
│   │   ├── dao/                 # Database models
│   │   ├── config/              # Configuration
│   │   ├── decorators/          # Custom decorators
│   │   ├── dto/                 # Data transfer objects
│   │   ├── log/                 # Logging
│   │   └── main.py              # Flask app factory
│   ├── db/alembic/              # Database migrations
│   ├── test/                    # Unit tests
│   ├── pyproject.toml           # Python dependencies (managed with uv)
│   ├── uv.lock                  # Locked dependency versions
│   ├── Dockerfile
│   └── doc/                     # Implementation guides
│
├── docker-compose.yml           # Multi-container orchestration
├── .env.example                 # Environment template
├── .gitignore                   # Git ignore rules
├── .dockerignore                # Docker build ignore rules
├── Makefile                     # Development commands
├── CLAUDE.md                    # Architecture guide
├── DEVELOPMENT.md               # Setup and workflow guide
└── README.md                    # This file
```

---

## 🔐 Security Features

- **JWT Authentication** - Token-based auth with refresh tokens
- **Role-Based Access Control** - Admin, User, Guest, Iframe roles
- **CORS Configuration** - Restricted origin access
- **Input Validation** - Validators for all user inputs
- **Password Hashing** - Secure password storage
- **Frame Token Validation** - Secure iframe embedding

---

## 🚢 Deployment

### Docker Production Build

```bash
# Build images
docker-compose build

# Run with production compose file (if available)
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

### Manual Deployment

See [DEVELOPMENT.md](DEVELOPMENT.md) - "Deployment Readiness" section.

---

## 🐛 Troubleshooting

### Port Already in Use
```bash
# Find process using port
lsof -i :4200   # Frontend
lsof -i :444    # Backend
lsof -i :3306   # Database
lsof -i :8000   # ChromaDB

# Kill process
kill -9 <PID>
```

### Database Connection Error
```bash
# Check database logs
make logs-db

# Verify DATABASE_URL in .env
# For Docker: mysql+pymysql://user:pass@db:3306/botcraft
# For local (host or a container sharing the host's Docker networking):
#   mysql+pymysql://user:pass@127.0.0.1:3306/botcraft
```

**Working from a separate dev container** (e.g. a devcontainer/SSH box that is not
the Docker host and not part of `docker-compose`)? `127.0.0.1` and `db` won't
resolve to `botfactory-db` by default — it lives on the `bot-factory_botfactory-network`
Docker network, which your dev container isn't attached to.

```bash
# 1. Attach your dev container to the project's Docker network
docker network connect bot-factory_botfactory-network <your-dev-container-name>

# 2. Point DATABASE_URL at the service name (now resolvable) instead of 127.0.0.1
#    server/.env:
#    DATABASE_URL=mysql+pymysql://botcraft_user:123456789@db:3306/botcraft?charset=utf8mb4
```
This has to be redone if the dev container is recreated (it's not persisted in `docker-compose.yml`).

### ChromaDB Connection Error
```bash
# Check ChromaDB logs
make logs-chromadb

# Verify CHROMA_HOST/CHROMA_PORT in .env
# For Docker: CHROMA_HOST=chromadb (the service name, not localhost)
# For local dev: CHROMA_HOST=localhost (with `make chromadb-only` running)
```

### Frontend Can't Connect to API
```bash
# Frontend calls a relative /api path, proxied to the backend:
# - Docker: nginx.conf proxies /api/ -> http://api:444
# - Local dev (ng serve): client/proxy.conf.json proxies /api -> http://127.0.0.1:444
# Check the relevant proxy config and:
make logs-api
```

### Docker Build Issues
```bash
# Rebuild without cache
docker-compose build --no-cache

# Full reset
docker system prune -a
docker-compose up --build
```

For more troubleshooting, see [DEVELOPMENT.md](DEVELOPMENT.md#troubleshooting).

---

## 📦 Key Dependencies

### Frontend
- `@angular/core@18` - Frontend framework
- `@angular/common` - Common utilities
- `bootstrap@5` - UI framework
- `jwt-decode` - JWT token handling
- `ng-bootstrap` - Bootstrap components

### Backend
- `Flask==2.3.3` - Web framework
- `SQLAlchemy==2.0.40` - ORM
- `langchain-*` - LLM integration
- `chromadb>=1.3.0` - Vector database client
- `python-jose==3.3.0` - JWT handling

See `pyproject.toml` for the full dependency list.

---

## 🤝 Contributing

1. Create a feature branch from `main`
2. Make your changes with clear commit messages
3. Run tests locally: `make test`
4. Push and create a pull request
5. Ensure CI/CD checks pass

### Development Workflow
```bash
# Update code
git checkout -b feature/your-feature

# Test locally
make test

# Commit and push
git add .
git commit -m "feat: Add your feature description"
git push origin feature/your-feature

# Create PR on GitHub
```

---

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

---

## 📞 Support

- **Issues**: Report bugs on [GitHub Issues](https://github.com/your-org/bot-factory/issues)
- **Documentation**: Check [DEVELOPMENT.md](DEVELOPMENT.md) and [CLAUDE.md](CLAUDE.md)
- **Architecture**: See [CLAUDE.md](CLAUDE.md) for system architecture

---

## 🎯 Roadmap

### Completed ✅
- [x] Core bot creation and management
- [x] Avatar builder
- [x] Knowledge base with RAG
- [x] Token tracking and analytics
- [x] Multiple LLM provider support
- [x] Docker containerization

### In Progress 🔄
- [ ] GitHub Actions CI/CD pipeline
- [ ] Enhanced analytics dashboard
- [ ] Multi-language support

### Planned 📋
- [ ] GraphQL API option
- [ ] WebSocket for real-time features
- [ ] Advanced prompt engineering UI
- [ ] Bot marketplace

---

## 👥 Authors

- **Bot Factory Team** - Initial development and maintenance

---

## 🙏 Acknowledgments

- Built with [Angular](https://angular.io)
- Powered by [Flask](https://flask.palletsprojects.com/)
- LLM integration via [LangChain](https://python.langchain.com/)
- Vector storage with [ChromaDB](https://www.trychromadb.com/)

---

**Happy coding! 🚀**

Last Updated: 2026-08-03
