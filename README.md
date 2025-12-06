# KengU

Your study partner at the University of Hong Kong.

![Backend](https://img.shields.io/badge/backend-FastAPI%20%2B%20RAG-green)
![Frontend](https://img.shields.io/badge/frontend-Vue%203-42b883)
![Database](https://img.shields.io/badge/database-MySQL-blue)

KengU is an intelligent study assistant for students at the University of Hong Kong.  
It combines multi-agent orchestration with retrieval-augmented generation (RAG) to help you:

- Keep your course materials in sync (Moodle + Exambase)
- Organize assignments and study plans
- Ask course-aware questions based on your actual materials
- Manage everything through a single chat interface

## Table of Contents

- [Features](#features)
- [Architecture](#architecture)
- [Getting Started](#getting-started)
- [Project Structure](#project-structure)
- [APIs](#apis)
- [RAG Pipeline](#rag-pipeline)
- [Notes](#notes)

> Looking for Chinese documentation? See the [Chinese README](README_zh.md).

## Features

- Course-aware chat assistant: uses your enrolled courses, materials and history to answer
- HKU login and verification: authenticate via HKU Portal (connect.hku.hk / hku.hk) and persist users locally
- Moodle & Exambase scraping: automatically download course files and past exam papers into `knowledge_base/`
- RAG-based Q&A: retrieve from a vector store (Chroma) and generate answers with an LLM
- Study planning & assignment management: pull assignments from Moodle calendar into the database and expose APIs
- Long-running task tracking: background jobs for knowledge-base updates and calendar scraping with progress polling

## Architecture

The system is roughly split into three layers:

- Backend (Python / FastAPI)
  - `services/serve.py` exposes the main REST API and SSE streaming endpoints
  - MySQL stores users, courses, assignments and study sessions (`dao/`)
  - Selenium + WebDriver scrape HKU Moodle / Exambase (`rag_scraper/`, `planner_scraper/`)

- Agents & LLM
  - `agents/` implements multiple agents:
    - `PlannerAgent`: study planning and time management
    - `RAGAgent`: course content retrieval and question answering
    - Scraper agent: orchestrates knowledge-base updates
  - `agents/llm.py` and `core/config.py` talk to an OpenAI-compatible endpoint (e.g. Qwen)

- Frontend (Vue 3)
  - Located in `kengu-fronted/`, built with Vue 3 + Element Plus + Pinia
  - Provides UI for login, course list, knowledge-base updates, chat and assignment management

## Getting Started

### 1. Prerequisites

- Python 3.10+
- Node.js 16+ and npm
- MySQL 8.x
- Google Chrome (used by Selenium scrapers)

### 2. Backend Setup

1. Clone the repository and enter the project directory:

   ```bash
   git clone <this-repo-url>
   cd kengu
   ```

2. Create and activate a virtual environment (recommended):

   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. Install backend dependencies (example, adjust to your environment as needed):

   ```bash
   pip install fastapi uvicorn "pydantic>=2" pymysql selenium webdriver-manager \
              chromadb requests openai dspy-ai python-multipart
   ```

4. Configure the database:

   - Create the database:

     ```sql
     CREATE DATABASE kengu CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
     ```

   - Initialize tables using `sql/create_table.sql`:

     ```bash
     mysql -u root -p kengu < sql/create_table.sql
     ```

   - Adjust to your local environment:
     - Update `DatabaseConfig` in `dao/config.py`, or
     - Override `DB_*` values via environment variables used in `core/config.py`

5. Configure the LLM and embeddings/RAG (minimal setup):

   - Set `LLM_API_KEY`, `LLM_API_ENDPOINT` and `LLM_MODEL_NAME` in `core/config.py`
   - Optionally, set embedding-related environment variables:
     - `EMBEDDING_API_KEY`
     - `EMBEDDING_API_URL`
     - `EMBEDDING_MODEL`
     - `INDEX_DIR` (vector index directory, default `./vectorbase`)

6. Run the backend (development mode):

   ```bash
   python -m services.serve
   ```

   By default this listens on `http://127.0.0.1:8009` and mounts:

   - API prefix: `/api`
   - Static course materials: `/knowledge_base` → local `knowledge_base/` directory

### 3. Frontend Setup

1. Install frontend dependencies:

   ```bash
   cd kengu-fronted
   npm install
   ```

2. Start both frontend and backend (recommended dev script):

   ```bash
   npm run start
   ```

   This is equivalent to running the following in parallel:

   - `npm run backend` → `python -m services.serve`
   - `npm run serve -- --host 0.0.0.0` → Vue dev server

   Make sure that:

   - Python dependencies are installed as described above
   - Your working directory is the repo root (so `npm run backend` can find `services/serve.py`)

## Project Structure

Core project layout (simplified):

```bash
.
├── agents/                # Multi-agent system: planner, RAG, scraper, etc.
├── api/                   # Legacy API (prefer services/api in new code)
├── auth/                  # HKU Portal authentication (Selenium)
├── core/                  # Global configuration (LLM / DB)
├── dao/                   # Data access layer (users, courses, assignments, ...)
├── docs/                  # Diagrams and design docs (Mermaid)
├── knowledge_base/        # Downloaded course files (Moodle / Exambase)
├── rag/                   # RAG core: chunking, embedding, vector store, retrieval
├── rag_scraper/           # Moodle / Exambase scrapers
├── planner_scraper/       # Moodle calendar scraper (assignments)
├── services/              # FastAPI app and REST APIs
├── kengu-fronted/         # Vue 3 frontend
├── sql/create_table.sql   # MySQL schema
├── vectorbase/            # Chroma persistence (can be initialized from vectorbase.zip)
└── main.py                # Early entrypoint (prefer services/serve.py)
```

## APIs

This section lists a few commonly used endpoints.  
See `services/api/` for full definitions.

- Auth (`services/api/auth_api.py`)
  - `POST /api/hku-auth`: authenticate with HKU account and create/update local user

- Course & Knowledge Base (`services/api/course_api.py`)
  - `POST /api/update-data`: background task, triggers Moodle + Exambase scraping and knowledge-base update
  - `POST /api/update-events`: scrape Moodle calendar events and insert into the `assignment` table
  - `POST /api/task-status`: check background task status and progress

- Chat & RAG (`services/api/chat_api.py`)
  - `POST /api/chat/stream`: SSE streaming chat endpoint, internally routes to Planner / RAG / Scraper agents

- Schedule & Assignments (`services/api/schedule_api.py`)
  - Endpoints for creating, querying and marking assignments as complete/pending

The frontend talks to these APIs through `http://127.0.0.1:8009/api/...`.

## RAG Pipeline

The RAG flow in KengU looks like this:

1. `rag_scraper/` and `agents/scraper_agent/` download course materials from Moodle / Exambase into `knowledge_base/`.
2. `VectorEmbeddingsGenerator` (`agents/scraper_agent/embeddings_generator.py`) processes downloaded files:
   - Calls `RagService.ingest_file()` to parse and chunk course files
   - Calls the embedding service (`rag/embedder.py`) to generate vectors
   - Writes vectors into the Chroma store (`rag/vector_store.py`)
3. At query time:
   - `RAGAgent` picks relevant courses based on the user question and enrollment
   - `RagService.retrieve()` fetches top-matching chunks from the vector store
   - `ChatAgent` sends the retrieved context and conversation history to the LLM and streams back the final answer

## Notes

- This project is still under active development; APIs and schemas may change
- Some secrets are currently hard-coded in the repo; before deploying anywhere:
  - Move secrets out of the codebase into environment variables or config files
  - Use separate databases and vector stores for production
- If you plan to run this project yourself:
  - Create your own LLM / embedding API keys
  - Use your own MySQL instance and test accounts

Contributions to improve docs and tooling (e.g. `requirements.txt`, Dockerfile, scripts) are very welcome.
