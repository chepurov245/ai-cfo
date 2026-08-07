from fastapi import FastAPI
from pydantic import BaseModel

from app.services.ai_service import ask_ai

app = FastAPI(
    title="AI CFO",
    version="0.1.0"
)


class ChatRequest(BaseModel):
    message: str


@app.get("/")
def root():
    return {
        "status": "ok",
        "project": "AI CFO",
        "version": "0.1.0"
    }


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "service": "AI CFO Backend",
        "version": "0.1.0"
    }


@app.post("/chat")
def chat(request: ChatRequest):
    reply = ask_ai(request.message)

    return {
        "reply": reply
    }