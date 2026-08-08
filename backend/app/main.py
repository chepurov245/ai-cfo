from fastapi import FastAPI

from app.api.chat import router as chat_router

app = FastAPI(
    title="AI CFO",
    version="0.1.0",
    description="AI CFO Backend API"
)


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


app.include_router(chat_router)