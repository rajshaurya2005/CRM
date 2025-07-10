from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from routers import leads, document_upload
from database.database import init_database

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up Mini-CRM API...")
    init_database()
    logger.info("Database initialized")
    yield
    logger.info("Shutting down Mini-CRM API...")

app = FastAPI(
    title="Mini-CRM Backend",
    description="API for basic lead management, document processing, and LLM interaction.",
    version="0.1.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(leads.router)
app.include_router(document_upload.router)

@app.get("/")
async def root():
    return {"message": "Welcome to the Mini-CRM API!", "version": "0.1.0"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "Mini-CRM API"}