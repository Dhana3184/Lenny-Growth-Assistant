# Architecture

## Request flow
1. React/Vite frontend submits a question and optional session ID.
2. FastAPI validates the request.
3. PostgreSQL stores conversation and message records.
4. The RAG layer embeds the question with Ollama and retrieves passages from
   the persistent Chroma index.
5. The Pi Coding Agent bridge sends the prompt and retrieved evidence to the
   configured model. Local Ollama is the default path.
6. The response and source metadata are returned to the frontend and stored.

## Components
- `frontend/`: React/Vite user interface.
- `backend/main.py`: HTTP routes, validation, persistence, error handling.
- `backend/database.py`, `backend/models.py`: database connection and models.
- `backend/rag.py`: embedding, retrieval, evidence construction, response.
- `backend/pi_agent.py`: Python-to-Node bridge.
- `pi_answer.mjs`: Pi agent session and model selection.
- `data/chroma_db/`: generated local transcript index; do not commit it.
- `data/raw/`: transcript source checkout; do not commit large raw data.

## Model configuration
Default: `LLM_PROVIDER=ollama`, `OLLAMA_BASE_URL=http://localhost:11434`,
`OLLAMA_CHAT_MODEL=qwen2.5:3b`, and
`OLLAMA_EMBED_MODEL=nomic-embed-text:latest`.

Optional cloud path: `LLM_PROVIDER=openai`, `OPENAI_API_KEY`, and
`OPENAI_MODEL`. Cloud execution must be tested with a valid key before claiming
it is verified. Embeddings currently remain dependent on the local Ollama
embedding model unless the implementation is deliberately extended.

## Operational limitations
The Node bridge requires Node.js and installed npm dependencies. PostgreSQL,
Ollama, the transcript index, and model availability are runtime dependencies.
Use `.env.example` as a template; never commit `.env` or API keys.
