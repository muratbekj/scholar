from .core.config import ConfigError, get_settings

try:
    # Validate configuration before any service is constructed (services build clients at import).
    settings = get_settings()
except ConfigError as exc:
    raise SystemExit(str(exc)) from None

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .api.routes import files, qa, quiz, flashcards
from .core.request_context import client_context

app = FastAPI(
    title="Scholar Backend API",
    description="AI-powered document processing and study tools",
    version="1.0.0"
)

# Add CORS middleware (origins from CORS_ORIGINS; '*' is rejected at startup)
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_origins),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers. Every data route binds the caller's client id (X-Client-Id in cloud mode);
# / and /health stay open for health checks.
for router in (files.router, qa.router, quiz.router, flashcards.router):
    app.include_router(router, dependencies=[Depends(client_context)])

@app.get("/")
async def root():
    return {"message": "Scholar Backend API", "version": "1.0.0"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "scholar-backend"}