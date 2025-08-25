from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .api.routes import files

app = FastAPI(
    title="Scholar Backend API",
    description="AI-powered document processing and study tools",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],  # Add your frontend URLs
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(files.router)

@app.get("/")
async def root():
    return {"message": "Scholar Backend API", "version": "1.0.0"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "scholar-backend"}