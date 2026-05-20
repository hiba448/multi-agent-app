# Lecture Companion
### A Multi-Agent System for Enhanced Student Support

> Built at ENSIAS — Mohammed V University, Rabat  
> Program: Business Intelligence & Analytics (BI&A)  
> Academic Year: 2025–2026

---

## Overview

Lecture Companion is an intelligent, fully local study assistant built on a multi-agent architecture. Students upload their lecture materials (PDF or PowerPoint), and the system provides summaries, answers questions, generates quizzes, evaluates answers, and tracks learning progress — all without sending any data to external cloud services.

The system is composed of four specialized agents coordinated by an orchestrator:

| Agent | Responsibility |
|---|---|
| **Scribe Agent** | Extracts summaries, key concepts, and definitions from lecture content |
| **Research Agent** | Answers student questions grounded in the uploaded document |
| **Tutor Agent** | Generates quizzes, evaluates answers, and explains difficult concepts |
| **Orchestrator Agent** | Classifies intent and routes every request to the correct agent |

---

## Technology Stack

| Layer | Tool |
|---|---|
| Frontend | Streamlit |
| Backend | FastAPI |
| Agents | LangChain + LangGraph |
| LLM (generation) | Ollama — gemma3:4b |
| LLM (embeddings) | Ollama — nomic-embed-text |
| Database | PostgreSQL + pgvector |
| ORM | SQLAlchemy + Alembic |
| Document parsing | PyMuPDF + python-pptx |
| Containerization | Docker + Docker Compose |

---

## Project Structure

```
lecture-companion/
├── backend/
│   ├── main.py                  # FastAPI app and router registration
│   ├── Dockerfile
│   ├── routes/
│   │   ├── chat.py              # POST /chat
│   │   ├── upload.py            # POST /upload
│   │   ├── session.py           # Session and history routes
│   │   └── student.py           # Weak topics, quiz results, documents
│   └── agents/
│       ├── orchestrator.py      # LangGraph orchestration logic
│       ├── scribe.py            # Scribe Agent
│       ├── research.py          # Research Agent
│       └── tutor.py             # Tutor Agent
├── db/
│   ├── models.py                # SQLAlchemy models
│   └── vector_store.py          # Embedding generation and retrieval
├── parsing/
│   └── document_parser.py       # PDF and PPTX text extraction
├── frontend/
│   ├── app.py                   # Streamlit interface
│   └── Dockerfile
├── alembic/                     # Database migrations
├── docker-compose.yml
├── requirements.txt
├── .env                         # Environment variables (not committed)
└── .gitignore
```

---

## Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop) installed and running
- At least **8 GB of RAM** available for Docker
- At least **10 GB of free disk space** (for models and database volumes)

---

## Installation and Setup

### 1. Clone the repository

```bash
git clone https://github.com/your-org/lecture-companion.git
cd lecture-companion
```

### 2. Create the `.env` file

Create a `.env` file at the root of the project with the following content:

```env
# PostgreSQL
POSTGRES_USER=admin
POSTGRES_PASSWORD=admin123
POSTGRES_DB=lecture_companion
DATABASE_URL=postgresql://admin:admin123@db:5432/lecture_companion

# Ollama
OLLAMA_BASE_URL=http://ollama:11434
OLLAMA_MODEL=gemma3:4b
OLLAMA_EMBED_MODEL=nomic-embed-text

# API
API_URL=http://backend:8000
```

> The `.env` file is listed in `.gitignore` and must never be committed to the repository.

### 3. Build and start all containers

```bash
docker compose up -d --build
```

This starts four containers: `lecture_db`, `lecture_ollama`, `lecture_backend`, and `lecture_frontend`.

### 4. Pull the required models

Run the following commands once after the first startup:

```bash
docker exec lecture_ollama ollama pull gemma3:4b
docker exec lecture_ollama ollama pull nomic-embed-text
```

Model downloads may take several minutes depending on your connection.

### 5. Enable the pgvector extension

```bash
docker exec -it lecture_db psql -U admin -d lecture_companion -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

### 6. Apply database migrations

```bash
docker exec -it lecture_backend alembic upgrade head
```

---

## Running the Application

Once setup is complete, the application is accessible at:

| Service | URL |
|---|---|
| Frontend (Streamlit) | http://localhost:8501 |
| Backend API | http://localhost:8000 |
| API Documentation (Swagger) | http://localhost:8000/docs |

---

## Usage

1. **Login** — Enter your name. Returning users will see their previous sessions.
2. **Upload** — Upload a lecture PDF or PPTX file. The system parses, chunks, and indexes it automatically.
3. **Chat** — Interact with your lecture:
   - *"Give me a summary of the lecture"* → Scribe Agent
   - *"What is gradient descent?"* → Research Agent
   - *"Give me a quiz"* → Tutor Agent
   - *"Explain backpropagation in simple terms"* → Tutor Agent
4. **Quiz** — Answer generated questions in the Quiz tab. Wrong answers are tracked automatically.
5. **My Progress** — View detected weak topics and your quiz score history.

> The system will decline to answer questions unrelated to the uploaded document and will suggest opening a new session instead.

---

## API Endpoints

| Method | Route | Description |
|---|---|---|
| GET | `/` | Health check |
| POST | `/session/` | Create or retrieve a student session |
| GET | `/session/{id}/history` | Get message history for a session |
| GET | `/session/{id}/document` | Get the document linked to a session |
| GET | `/session/student/{id}` | Get all sessions for a student |
| POST | `/session/student/{id}/new` | Create a new session for a student |
| POST | `/upload/` | Upload and process a lecture file |
| POST | `/chat/` | Send a message through the orchestrator |
| GET | `/student/{id}/weak-topics` | Get detected weak topics |
| GET | `/student/{id}/quiz-results` | Get quiz result history |
| GET | `/student/{id}/documents` | Get uploaded documents |

---

## Common Docker Commands

```bash
# Start all services in the background
docker compose up -d

# View logs for a specific service
docker compose logs -f backend

# Restart a single service after a code change
docker compose restart backend

# Stop all services
docker compose down

# Stop and delete all data (resets database and models)
docker compose down -v

# Rebuild after changing requirements.txt
docker compose up -d --build
```

---

## Development Notes

- Code changes to Python files are reflected immediately without rebuilding, since the project folder is mounted as a volume inside the containers.
- Rebuilding is only required when `requirements.txt` changes.
- All work should be done on feature branches merged into `dev`. The `main` branch receives merges only at the end of each phase.
- Database schema changes must always be accompanied by an Alembic migration:

```bash
docker exec -it lecture_backend alembic revision --autogenerate -m "description"
docker exec -it lecture_backend alembic upgrade head
```

---

## Authors

| Name | Program |
|---|---|
| BITAR Aicha | BI&A — ENSIAS |
| EDDIAL Ghita | BI&A — ENSIAS |
| LHICHOU Hiba | BI&A — ENSIAS |

Supervised by **Pr. BENBRAHIM Houda** — Mohammed V University, Rabat.