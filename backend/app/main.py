from fastapi import FastAPI

app = FastAPI(
    title="AI CFO",
    version="0.1.0"
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