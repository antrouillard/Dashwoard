from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.db import create_tables
# Importer tous les modèles avant create_tables() pour que SQLAlchemy
# résolve correctement toutes les relations (forward references).
import app.models  # noqa: F401
from app.api.routes import accounts, characters, todos, guilds, auth, sync, weekly, crafting


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup : crée les tables si elles n'existent pas
    create_tables()
    yield
    # Shutdown (rien à faire pour l'instant)


app = FastAPI(
    title="WoW Progress Hub API",
    version="0.1.0",
    description="Backend pour le dashboard WoW Progress Hub",
    lifespan=lifespan,
)

# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(accounts.router, prefix="/api")
app.include_router(characters.router, prefix="/api")
app.include_router(todos.router, prefix="/api")
app.include_router(guilds.router, prefix="/api")
# Auth OAuth2 — monté à la racine car le redirect_uri Blizzard est /auth/callback
app.include_router(auth.router)
# Sync — sous /api comme les autres routes
app.include_router(sync.router, prefix="/api")
app.include_router(weekly.router, prefix="/api")
app.include_router(crafting.router, prefix="/api")


@app.get("/health", tags=["health"])
def health():
    return {"status": "ok", "version": "0.1.0"}
