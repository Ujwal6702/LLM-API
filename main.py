from fastapi import FastAPI
from config import get_settings, get_logger
# Get configuration
settings = get_settings()

# Get centralized logger
app_logger = get_logger()

# Initialize FastAPI app
app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    debug=settings.debug,
    docs_url="/docs" if settings.is_development else None,
    redoc_url="/redoc" if settings.is_development else None
)

@app.on_event("startup")
async def startup_event():
    """Application startup event."""
    app_logger.info(f"Starting {settings.app_name}")
    app_logger.info(f"Project root: {settings.project_root_str}")
    app_logger.info(f"Environment: {settings.environment}")
    app_logger.info(f"Debug mode: {settings.debug}")

@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": f"Welcome to {settings.app_name}",
        "version": "0.1.0",
        "environment": settings.environment,
        "project_root": settings.project_root_str
    }

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "app_name": settings.app_name,
        "environment": settings.environment,
        "debug": settings.debug
    }

@app.get(f"{settings.api_base_url}/config")
async def get_config_info():
    """Get non-sensitive configuration information."""
    return {
        "app_name": settings.app_name,
        "api_version": settings.api_version,
        "environment": settings.environment,
        "project_root": settings.project_root_str,
        "cors_origins": settings.cors_origins_list,
        "log_level": settings.log_level
    }

if __name__ == "__main__":
    import uvicorn
    
    app_logger.info(f"Starting server on {settings.host}:{settings.port}")
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.is_development,
        log_level=settings.log_level.lower()
    )