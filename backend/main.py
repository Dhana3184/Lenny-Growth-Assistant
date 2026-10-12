import logging
from datetime import datetime, timezone
from typing import Optional

import requests
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from backend.database import SessionLocal
from backend.models import Conversation, Message
from backend.rag import answer_question as generate_rag_answer


logger = logging.getLogger(__name__)

app = FastAPI(title="Lenny Growth Assistant")


# --------------------------------------------------
# CORS configuration
# --------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --------------------------------------------------
# Request models
# --------------------------------------------------

class QuestionRequest(BaseModel):
    question: str = Field(min_length=1, max_length=12000)
    session_id: Optional[str] = None
    provider: str = "ollama"


# --------------------------------------------------
# Database dependency
# --------------------------------------------------

def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()


# --------------------------------------------------
# Home and health endpoints
# --------------------------------------------------

@app.get("/")
def home():
    return {
        "message": "Welcome to Lenny Growth Assistant!",
        "status": "Backend is running",
    }


@app.get("/config")
def app_config():
    import os

    provider = os.getenv("LLM_PROVIDER", "ollama").lower()
    if provider not in ("ollama", "openai"):
        provider = "ollama"

    if provider == "openai":
        model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    else:
        model = os.getenv("OLLAMA_CHAT_MODEL", "qwen2.5:3b")

    return {
        "provider": provider,
        "model": model,
        "provider_configured": (
            bool(os.getenv("OPENAI_API_KEY")) if provider == "openai"
            else True
        ),
    }


@app.get("/health")
def health(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))

        return {
            "status": "healthy",
            "database": "connected",
        }

    except SQLAlchemyError:
        logger.exception("Database health check failed")

        raise HTTPException(
            status_code=503,
            detail="Database connection unavailable",
        )


# --------------------------------------------------
# Conversation endpoints
# --------------------------------------------------

@app.post("/sessions")
def create_session(db: Session = Depends(get_db)):
    try:
        conversation = Conversation(
            title="New conversation"
        )

        db.add(conversation)
        db.commit()
        db.refresh(conversation)

        return {
            "session_id": conversation.session_id,
            "title": conversation.title,
            "created_at": conversation.created_at,
        }

    except SQLAlchemyError:
        db.rollback()
        logger.exception("Could not create conversation")

        raise HTTPException(
            status_code=503,
            detail="Could not create conversation",
        )


@app.get("/sessions")
def list_sessions(db: Session = Depends(get_db)):
    try:
        conversations = (
            db.query(Conversation)
            .order_by(Conversation.updated_at.desc())
            .limit(100)
            .all()
        )

        return [
            {
                "session_id": item.session_id,
                "title": item.title,
                "created_at": item.created_at,
                "updated_at": item.updated_at,
            }
            for item in conversations
        ]

    except SQLAlchemyError:
        logger.exception("Could not retrieve conversations")

        raise HTTPException(
            status_code=503,
            detail="Could not retrieve conversations",
        )


@app.get("/sessions/{session_id}/messages")
def get_messages(
    session_id: str,
    db: Session = Depends(get_db),
):
    try:
        conversation = db.get(
            Conversation,
            session_id,
        )

        if conversation is None:
            raise HTTPException(
                status_code=404,
                detail="Conversation not found",
            )

        messages = (
            db.query(Message)
            .filter(Message.session_id == session_id)
            .order_by(Message.id.asc())
            .all()
        )

        return {
            "session_id": session_id,
            "messages": [
                {
                    "id": item.id,
                    "role": item.role,
                    "content": item.content,
                    "sources": item.sources,
                    "created_at": item.created_at,
                }
                for item in messages
            ],
        }

    except SQLAlchemyError:
        logger.exception("Could not retrieve messages")

        raise HTTPException(
            status_code=503,
            detail="Could not retrieve messages",
        )


# --------------------------------------------------
# Ask endpoint: RAG + Ollama + PostgreSQL
# --------------------------------------------------

@app.post("/ask")
def ask_question(
    request: QuestionRequest,
    db: Session = Depends(get_db),
):
    if request.provider not in ("ollama", "openai"):
        raise HTTPException(
            status_code=422,
            detail="Provider must be 'ollama' or 'openai'.",
        )

    question = request.question.strip()

    if not question:
        raise HTTPException(
            status_code=422,
            detail="Please enter a question.",
        )

    # Step 1: Find or create the conversation and save
    # the user's message before calling the AI.
    try:
        if request.session_id:
            conversation = db.get(
                Conversation,
                request.session_id,
            )

            if conversation is None:
                raise HTTPException(
                    status_code=404,
                    detail=(
                        "Conversation not found. "
                        "Create a new session."
                    ),
                )

        else:
            conversation = Conversation(
                title=question[:80],
            )

            db.add(conversation)
            db.flush()

        session_id = conversation.session_id

        if conversation.title == "New conversation":
            conversation.title = question[:80]
	
        # Load the previous messages before adding this question.
        previous_messages = (
            db.query(Message)
            .filter(Message.session_id == session_id)
            .order_by(Message.id.desc())
            .limit(8)
            .all()
        )

        history = [
            {
                "role": message.role,
                "content": message.content,
            }
            for message in reversed(previous_messages)
        ]

        db.add(
            Message(
                session_id=session_id,
                role="user",
                content=question,
                sources=[],
            )
        )

        conversation.updated_at = datetime.now(
            timezone.utc
        )

        db.commit()

    except SQLAlchemyError:
        db.rollback()
        logger.exception("Could not save user message")

        raise HTTPException(
            status_code=503,
            detail="Could not save the question to the database",
        )

    # Step 2: Retrieve relevant transcript passages and
    # generate an answer using the local Ollama model.
    try:
        rag_result = generate_rag_answer(
            question,
            history=history,
            provider=request.provider,
        )

        answer = rag_result["answer"]
        raw_sources = rag_result.get("sources", [])

        # Preserve citation metadata for the API and database.
        sources = [
            {
                key: source[key]
                for key in (
                    "citation_id",
                    "title",
                    "guest",
                    "youtube_url",
                    "source_file",
                    "distance",
                )
                if key in source
            }
            for source in raw_sources
        ]

    except Exception:
        logger.exception("RAG/Pi answer generation failed")
        db.rollback()
        raise HTTPException(
            status_code=503,
            detail=(
                "The AI service could not generate an answer. "
                "Check the selected provider, model availability, "
                "Node.js, and the transcript index."
            ),
        )

    # Step 3: Save the assistant's answer exactly once.
    try:
        db.add(
            Message(
                session_id=session_id,
                role="assistant",
                content=answer,
                sources=sources,
            )
        )

        conversation.updated_at = datetime.now(
            timezone.utc
        )

        db.commit()

    except SQLAlchemyError:
        db.rollback()
        logger.exception("Could not save assistant response")

        raise HTTPException(
            status_code=503,
            detail="The answer was generated but could not be saved",
        )

    # Step 4: Return the answer and its source references.
    return {
        "session_id": session_id,
        "answer": answer,
        "sources": sources,
    }