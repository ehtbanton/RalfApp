from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from .database import init_db
from .routers import auth, videos, upload, analysis
from .websocket import websocket_router
import os

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await init_db()
    # Create storage directory if it doesn't exist
    storage_path = os.getenv("VIDEO_STORAGE_PATH", "/app/storage")
    os.makedirs(storage_path, exist_ok=True)
    yield
    # Shutdown

app = FastAPI(
    title="Video Storage API",
    description="A scalable video storage and analysis platform",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(videos.router, prefix="/api/videos", tags=["Videos"])
app.include_router(upload.router, prefix="/api/upload", tags=["Upload"])
app.include_router(analysis.router, prefix="/api/analysis", tags=["Analysis"])
app.include_router(websocket_router, prefix="/ws")

# Serve static files (uploaded videos)
storage_path = os.getenv("VIDEO_STORAGE_PATH", "/app/storage")
app.mount("/static", StaticFiles(directory=storage_path), name="static")

@app.get("/")
async def root():
    return {"message": "Video Storage API", "version": "1.0.0"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}