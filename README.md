# Bot Factory

An AI bot creation and management platform built around a production-style FastAPI backend and a containerized deployment: users create, customize, and chat with their own bots, with knowledge base management (RAG) and token tracking.

![Bot Factory](https://img.shields.io/badge/Angular-18-red) ![FastAPI](https://img.shields.io/badge/FastAPI-0.115-teal) ![Python](https://img.shields.io/badge/Python-3.12+-blue) ![Docker](https://img.shields.io/badge/Docker-Compose-blue) ![License](https://img.shields.io/badge/License-AGPL--3.0-green)

🔗 **Live demo:** [bot-factory.fr](https://bot-factory.fr)

> 💼 **Portfolio project** — built solo by [Pierre Faraco](https://github.com/pierrefaraco) to showcase backend and DevOps skills (FastAPI, layered architecture, MySQL + Alembic migrations, LLM/RAG integration, Docker Compose, Nginx and automated HTTPS deployment), with an Angular front end. Not maintained as a commercial product.

---

## 🌟 Features

### Core Capabilities
- **Bot Creation & Management** - Create and customize AI bots with personalized parameters
- **Knowledge Base Management** - Upload and manage documents with RAG (Retrieval-Augmented Generation)
- **Real-time Chat** - Interactive conversations with bots powered by LLM providers
- **Token Tracking** - Automatic token usage tracking and analytics
- **Avatar Builder** - SVG-based customizable bot avatars (body, eyes, hat, mouth, colors)

### Advanced Features
- **LLM Support** - Integration with Mistral AI
- **Vector Search** - ChromaDB-powered semantic search for knowledge retrieval
- **JWT Authentication** - Secure token-based authentication with refresh tokens
- **Role-Based Access Control** - Admin, User, Guest, and Iframe roles
 
---

## 🏗️ Architecture

### Tech Stack

**Frontend**
- Angular 18 with TypeScript
- Bootstrap 5 + Custom SCSS themes (dark/light modes)
- RxJS for reactive programming
- JWT handling with interceptors

**Backend**
- Python FastAPI 0.115
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

### System Architecture

```
┌────────────────────────────────────────────────────┐
│                   Frontend (Angular 18)            │
│              Bootstrap 5 + Dark/Light Themes       │
└────────────────────┬───────────────────────────────┘
                     │ HTTP/REST + JWT
                     │
┌────────────────────▼──────────────────────────────┐
│              Nginx (Reverse Proxy)                │
│         - API routing to FastAPI backend          │
│         - Static file serving                     │
│         - Security headers                        │
└────────────────────┬──────────────────────────────┘
                     │
┌────────────────────▼──────────────────────────────┐
│         FastAPI Backend (Python 3.12+)            │
│  ┌───────────────────────────────────────────┐    │
│  │                 REST API                  │    │
│  └───────────────────────────────────────────┘    │
│                       │                           │
│  ┌──────▼─────┬───────▼──────┬────────▼────┐      │
│  │  Services  │  Database   │  External    │      │
│  │  Layer     │   (ORM)     │  Services    │      │
│  └────────────┴─────────────┴──────────────┘      │
└──────────────────┬────────────────────────────────┘
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

##################### Only if you run the project for the first time, follow these 3 steps  #####################
# run only mysql container 
make db-only
# init the database
make db-upgrade
# onece db is created remove all containers
make down
###############################################################################################

# Start all services
make setup
make up

# Services are now running:
# - Frontend: http://localhost:8080
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
npm start          # Starts on port 8080
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
make db-only        # docker compose up -d db
# ✓ MySQL running on localhost:3306, data persisted in the `mysql_data` volume
```

### Initialize Database
```bash
make migrate       # Run all pending migrations (inside the `api` Docker container)
make db-upgrade     # Run all pending migrations locally via uv (DATABASE_URL built from the root .env's MYSQL_* vars)
```

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
4. Configure secret management 
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
│   └── nginx.conf
│
├── server/                       # Python FastAPI Backend
│   ├── ai_server/
│   │   ├── routers/             # REST endpoints
│   │   ├── services/            # Business logic
│   │   ├── models/              # SQLAlchemy ORM models (one module per aggregate)
│   │   ├── database/            # DB engines + per-request session scoping
│   │   ├── config/              # Configuration
│   │   ├── decorators/          # Custom decorators
│   │   ├── dto/                 # Data transfer objects
│   │   ├── log/                 # Logging
│   │   └── asgi.py              # FastAPI app factory
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
├── DEVELOPMENT.md               # Setup and workflow guide
└── README.md                    # This file
```


## 📄 License

This project is licensed under the GNU Affero General Public License v3.0 (AGPL-3.0) - see the LICENSE file for details. This means any modified version deployed as a network service (e.g. a SaaS fork) must also make its source code available to its users.
---

## 🙏 Acknowledgments

- Built with [Angular](https://angular.io)
- Powered by [FastAPI](https://fastapi.tiangolo.com/)
- LLM integration via [LangChain](https://python.langchain.com/)
- Vector storage with [ChromaDB](https://www.trychromadb.com/)

---


