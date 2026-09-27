from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env", override=True) 

from app.routers import ask, chat, complaint, healing, helplines, laws, rights, safety, translation

app = FastAPI(
    title="Nyaya Desk API",
    description=(
        "Backend for Nyaya Desk. Guest-first by design: no endpoint here "
        "requires authentication, and nothing is persisted to a database "
        "unless a future auth layer explicitly opts a signed-in user in."
    ),
    version="0.1.0",
)

# TODO before production: replace "*" with the actual frontend origin(s).
# Kept wide open here only so the scaffold is easy to run locally against
# the existing frontend file without extra config.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.include_router(ask.router)
app.include_router(chat.router)
app.include_router(complaint.router)
app.include_router(helplines.router)
app.include_router(rights.router)
app.include_router(healing.router)
app.include_router(laws.router)
app.include_router(safety.router)
app.include_router(translation.router)


@app.get("/", include_in_schema=False)
async def frontend() -> FileResponse:
    return FileResponse(Path(__file__).resolve().parent.parent / "index.html")


@app.get("/api/health", tags=["health"])
async def health() -> dict:
    return {"status": "ok"}
