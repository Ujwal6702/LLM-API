"""
FastAPI application entry point with MVC structure and LLM provider aggregation
"""
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.controllers import health_controller, llm_controller
from app.config.settings import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager
    """
    # Startup
    print("🚀 Starting LLM API Aggregator...")
    print(f"📡 Loaded {len(settings.LLM_PROVIDERS)} LLM providers")
    
    # Initialize providers and check connectivity
    try:
        from app.services.provider_clients import provider_manager
        available_providers = await provider_manager.get_available_providers()
        print(f"✅ {len(available_providers)} providers available")
        
        if available_providers:
            print(f"📋 Available providers: {', '.join(available_providers)}")
        else:
            print("⚠️  Warning: No providers available. Check API keys in .env file")
            
    except Exception as e:
        print(f"⚠️  Error initializing providers: {e}")
    
    yield
    
    # Shutdown
    print("🛑 Shutting down LLM API Aggregator...")
    try:
        from app.utils.rate_limiter import rate_limiter_manager
        await rate_limiter_manager.close()
        print("✅ Rate limiter closed")
    except Exception as e:
        print(f"⚠️  Error during shutdown: {e}")


def create_app() -> FastAPI:
    """
    Application factory pattern for creating FastAPI instance
    """
    app = FastAPI(
        title=settings.APP_NAME,
        description=settings.APP_DESCRIPTION,
        version=settings.APP_VERSION,
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan
    )
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Include routers
    app.include_router(health_controller.router, prefix="/api/v1", tags=["Health"])
    app.include_router(llm_controller.router, prefix="/api/v1", tags=["LLM"])
    
    # Add root endpoint
    @app.get("/", tags=["Root"])
    async def root():
        """
        Root endpoint with basic information
        """
        return {
            "name": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "description": settings.APP_DESCRIPTION,
            "docs": "/docs",
            "health": "/api/v1/health",
            "providers": "/api/v1/providers"
        }
    
    return app


# Create the FastAPI application instance
app = create_app()

if __name__ == "__main__":
    import uvicorn
    
    print(f"🌟 Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    print(f"🔗 API Documentation: http://{settings.HOST}:{settings.PORT}/docs")
    print(f"📚 ReDoc: http://{settings.HOST}:{settings.PORT}/redoc")
    
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="debug" if settings.DEBUG else "info"
    )
