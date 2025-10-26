from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.database import init_db
from app.routes import auth_router, agent_router, call_router, webhook_router, settings_router
from app.services.settings_service import initialize_default_settings

# Create FastAPI app
app = FastAPI(
    title="Dispatch Voice AI Backend",
    description="AI Voice Agent Platform for Logistics Dispatch",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router, prefix=settings.API_PREFIX)
app.include_router(agent_router, prefix=settings.API_PREFIX)
app.include_router(call_router, prefix=settings.API_PREFIX)
app.include_router(webhook_router, prefix=settings.API_PREFIX)
app.include_router(settings_router, prefix=settings.API_PREFIX)


@app.on_event("startup")
async def startup_event():
    """Initialize database on startup"""
    print("Starting up...")
    print(f"Environment: {settings.ENVIRONMENT}")
    # Initialize database tables
    init_db()
    print("Database initialized")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    print("Shutting down...")


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Dispatch Voice AI Backend API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "environment": settings.ENVIRONMENT
    }