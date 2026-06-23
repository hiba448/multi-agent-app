# Lecture Companion
### A Multi-Agent System for Enhanced Student Support

> Built at ENSIAS — Mohammed V University, Rabat  
> Program: Business Intelligence & Analytics (BI&A)  
> Academic Year: 2025–2026  
> Supervised by **Pr. BENBRAHIM Houda**

---

## Overview

Lecture Companion is an intelligent, fully local academic study assistant built on a multi-agent architecture. Students organize their learning by subject, upload lecture materials, and interact with a system that provides summaries, answers questions, generates adaptive quizzes, evaluates answers, detects weak topics, and tracks progress over time — entirely without sending data to external cloud services.

---

## Architecture

```
Frontend (Streamlit)
    ↓ HTTP
Backend (FastAPI)
    ↓
Orchestrator Agent
    ↓
Scribe Agent · Research Agent · Tutor Agent
    ↓
PostgreSQL + pgvector · Ollama (Local LLM)
```

---

## Technology Stack

| Layer | Tool | Role |
|---|---|---|
| Frontend | Streamlit | User interface |
| Backend | FastAPI | REST API and request routing |
| Agent framework | LangChain + LangGraph | Agent logic and orchestration |
| LLM (generation) | Ollama — gemma3:4b | Text generation and reasoning |
| LLM (embeddings) | Ollama — nomic-embed-text | Semantic vector embeddings |
| Database | PostgreSQL + pgvector | Relational data and vector search |
| ORM | SQLAlchemy + Alembic | Database access and migrations |
| Document parsing | PyMuPDF + python-pptx | PDF and PowerPoint extraction |
| Containerization | Docker + Docker Compose | Reproducible deployment |

---

## Data Model

```
Student
  ├── Subject (one per academic field, e.g. Machine Learning, Data Warehousing)
  │     ├── Session / Discussion (one document per discussion)
  │     │     └── Message (full conversation history)
  │     ├── Document + DocumentChunks (parsed and embedded)
  │     ├── WeakTopic (detected per subject, with mastery status)
  │     ├── QuizResult (one record per completed quiz attempt)
  │     └── TopicProgress (score history per topic over time)
```

Key constraints:
- Subject names are unique per student.
- Weak topics are unique per student–subject–topic combination.
- One discussion is linked to exactly one document.
- Documents are validated against their subject before being accepted.

---

## Project Structure

```
lecture-companion/
├── backend/
│   ├── main.py                         # FastAPI app, router registration, CORS
│   ├── Dockerfile
│   ├── routes/
│   │   ├── auth.py                     # POST /auth/register, /auth/login
│   │   ├── subject.py                  # CRUD for subjects
│   │   ├── session.py                  # Discussion management and history
│   │   ├── upload.py                   # Document upload + subject validation
│   │   ├── chat.py                     # POST /chat — main agent entry point
│   │   └── student.py                  # Weak topics, quiz results, topic progress
│   └── agents/
│       ├── orchestrator.py             # Intent classification, quiz planning, routing
│       ├── scribe.py                   # Summary, key concepts, definitions
│       ├── research.py                 # Question answering, off-topic detection
│       └── tutor.py                    # Quiz generation, evaluation, full quiz analysis
├── db/
│   ├── models.py                       # All SQLAlchemy models
│   └── vector_store.py                 # Embedding generation and similarity search
├── parsing/
│   └── document_parser.py             # PDF (PyMuPDF) and PPTX (python-pptx) parsing
├── frontend/
│   ├── app.py                          # Streamlit interface
│   └── Dockerfile
├── alembic/
│   └── versions/                       # Database migration history
├── docker-compose.yaml
├── requirements.txt
├── .env                                # Environment variables (not committed)
└── .gitignore
```

---

## Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop) installed and running
- Minimum **8 GB of RAM** allocated to Docker
- Minimum **10 GB of free disk space** (models and database volumes)

---

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/your-org/lecture-companion.git
cd lecture-companion
```

### 2. Create the `.env` file

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

# Frontend
API_URL=http://backend:8000
```

> `.env` is listed in `.gitignore` and must never be committed.

### 3. Build and start all containers

```bash
docker compose up -d --build
```

### 4. Pull the required models (first run only)

```bash
docker exec lecture_ollama ollama pull gemma3:4b
docker exec lecture_ollama ollama pull nomic-embed-text
```

### 5. Enable pgvector (first run only)

```bash
docker exec -it lecture_db psql -U admin -d lecture_companion -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

### 6. Apply database migrations

```bash
docker exec -it lecture_backend alembic upgrade head
```

---

## Access

| Service | URL |
|---|---|
| Frontend | http://localhost:8501 |
| Backend API | http://localhost:8000 |
| API Documentation | http://localhost:8000/docs |

---

## Usage Flow

```
Register / Login
    → Dashboard: view or create subjects
        → Enter subject
            → Create a discussion
            → Upload a lecture document (validated against the subject)
            → Chat: ask questions, request summaries, explanations
            → Generate a quiz (quick / standard / full coverage / exam)
            → Complete quiz → system analyzes the full attempt
            → Weak topics detected and saved per subject
            → Practice weak topics with targeted quizzes
            → Track progress per topic over time
```

---

## Agent Responsibilities

### Orchestrator Agent
Classifies every student request into one of five intents: `SUMMARIZE`, `QUESTION`, `QUIZ`, `EVALUATE`, `EXPLAIN`. For quiz requests, a dedicated quiz planner determines the focus, style, and number of questions before routing to the Tutor Agent. The EVALUATE intent is forced automatically when quiz answer fields are present in the request payload, bypassing classification.

### Scribe Agent
Receives the top retrieved chunks from the lecture document and produces a structured output: a concise summary, a list of key concepts, and a dictionary of definitions.

### Research Agent
Retrieves the most semantically similar chunks from the vector store using cosine distance. Decides whether to answer from lecture content or enrich with web search based on the best chunk distance score. Detects off-topic questions and declines to answer them, directing the student to open a new discussion or subject.

### Tutor Agent
Handles three tasks: quiz generation (with adaptive focus and style), per-question answer evaluation, and full quiz attempt analysis. The full quiz analysis is the primary mechanism for weak topic detection — it evaluates the entire quiz at once, identifies patterns across correct and incorrect answers, and produces structured weak topics with evidence, recommendations, and mastery status.

---

## API Endpoints

### Authentication
| Method | Route | Description |
|---|---|---|
| POST | `/auth/register` | Create a new student account |
| POST | `/auth/login` | Authenticate with username or email |

### Subjects
| Method | Route | Description |
|---|---|---|
| GET | `/subject/student/{student_id}` | List all subjects for a student |
| POST | `/subject/` | Create a new subject |
| GET | `/subject/{subject_id}` | Get one subject |
| PUT | `/subject/{subject_id}` | Update subject name or description |
| DELETE | `/subject/{subject_id}` | Delete subject and all related data |

### Discussions (Sessions)
| Method | Route | Description |
|---|---|---|
| POST | `/session/` | Create a new discussion inside a subject |
| GET | `/session/{session_id}/history` | Get message history |
| GET | `/session/{session_id}/document` | Get the document linked to a discussion |
| GET | `/session/subject/{subject_id}` | List all discussions inside a subject |
| DELETE | `/session/{session_id}` | Delete a discussion and its messages |

### Upload
| Method | Route | Description |
|---|---|---|
| POST | `/upload/` | Upload and validate a document against its subject |

### Chat
| Method | Route | Description |
|---|---|---|
| POST | `/chat/` | Send a request through the orchestrator |

### Student Data
| Method | Route | Description |
|---|---|---|
| GET | `/student/{id}/subject/{sid}/weak-topics` | Weak topics per subject |
| GET | `/student/{id}/subject/{sid}/quiz-results` | Quiz results per subject |
| GET | `/student/{id}/subject/{sid}/topic-progress` | Topic progress history |
| GET | `/student/{id}/subject/{sid}/topic-progress/{topic}` | Progress for one topic |
| POST | `/student/{id}/subject/{sid}/quiz-attempt/analyze` | Analyze a completed quiz attempt |
| GET | `/student/{id}/subject/{sid}/documents` | Documents per subject |

---

## Document Validation

When a document is uploaded inside a subject, the system automatically checks its relevance before storing it. The validation process:

1. Extracts a text excerpt from the new document (first 8 chunks, up to 5 000 characters).
2. Retrieves short excerpts from already accepted documents in the subject for comparison context.
3. Asks the local LLM to decide whether the new document belongs to the same academic field.
4. Returns a structured result with a `relevant` boolean, a `confidence` score, and a plain-text reason.

Documents that do not pass validation are rejected with a descriptive error. The file is removed from disk. No database record is created.

---

## Quiz System

Quiz generation is adaptive. When a student requests a quiz, a dedicated planner analyses the request and decides:

- **Quiz focus** — the specific topic or scope.
- **Quiz style** — `quick` (3 questions), `standard` (5), `long` (8), `full_coverage` (10–12), `exam_preparation` (8–10), or `weak_topics`.
- **Number of questions** — inferred from the request or overridden by an explicit number (capped at 15).
- **Retrieval query** — the best semantic query to fetch relevant lecture chunks.

Once the student completes all questions, the full attempt is sent to `POST /student/{id}/subject/{sid}/quiz-attempt/analyze`. The Tutor Agent evaluates the attempt globally, detects weak and strong topics, updates mastery status, and saves a `TopicProgress` record and a final `QuizResult`.

---

## Weak Topic Tracking

Weak topics are detected exclusively through full quiz attempt analysis — not question by question. Each topic carries:

- `evidence` — which questions revealed the gap.
- `recommendation` — what the student should review.
- `mastery_status` — one of `needs_practice`, `improving`, or `mastered`.

Topics are scoped per student and per subject. Progress per topic is tracked over time through `TopicProgress` records, allowing the system to measure improvement across multiple quiz attempts.

---

## Common Docker Commands

```bash
# Start all services in the background
docker compose up -d

# View live logs for a specific service
docker compose logs -f backend

# Restart one service after a code change
docker compose restart backend

# Stop all services
docker compose down

# Stop and delete all volumes (resets database and models)
docker compose down -v

# Rebuild after changing requirements.txt
docker compose up -d --build

# Apply new migrations
docker exec -it lecture_backend alembic upgrade head
```

> Code changes to Python files are reflected immediately without rebuilding because the project folder is mounted as a volume inside the containers. Rebuilding is only required when `requirements.txt` changes.

---

## Development Notes

- All work should go through feature branches merged into `dev`. The `main` branch receives merges only at the end of each validated phase.
- Every database schema change must be accompanied by an Alembic migration:

```bash
docker exec -it lecture_backend alembic revision --autogenerate -m "description"
docker exec -it lecture_backend alembic upgrade head
```

- The `uploads/` folder is created automatically on startup at `/app/uploads` inside the backend container. Uploaded files are named using the pattern `student_{id}_subject_{id}_session_{id}_{filename}` to avoid collisions.

---

## Authors

| Name | Program |
|---|---|
| BITAR Aicha | BI&A — ENSIAS |
| EDDIAL Ghita | BI&A — ENSIAS |
| LHICHOU Hiba | BI&A — ENSIAS |

Supervised by **Pr. BENBRAHIM Houda** — Mohammed V University, Rabat.