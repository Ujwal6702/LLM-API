"""
Health check controller
"""
import time
from fastapi import APIRouter
from app.controllers.base_controller import BaseController
from app.models.base_models import HealthResponse
from app.config.settings import settings

# Create router instance
router = APIRouter()

class HealthController(BaseController):
    """
    Controller for health check endpoints
    """
    
    def __init__(self):
        super().__init__()
        self.start_time = time.time()
    
    async def health_check(self) -> HealthResponse:
        """
        Basic health check endpoint
        """
        uptime = time.time() - self.start_time
        
        return HealthResponse(
            status="healthy",
            version=settings.APP_VERSION,
            uptime=uptime,
            message="Service is running"
        )
    
    async def detailed_health_check(self) -> dict:
        """
        Detailed health check with system information
        """
        import platform
        
        uptime = time.time() - self.start_time
        
        health_data = {
            "status": "healthy",
            "version": settings.APP_VERSION,
            "uptime": uptime,
            "system": {
                "platform": platform.system(),
                "python_version": platform.python_version(),
            },
            "services": {
                "api": "healthy",
                "llm_service": "healthy"
            }
        }
        
        # Try to add system metrics if psutil is available
        try:
            import psutil
            health_data["system"].update({
                "cpu_usage": psutil.cpu_percent(),
                "memory_usage": psutil.virtual_memory().percent,
                "disk_usage": psutil.disk_usage('/').percent
            })
        except ImportError:
            health_data["system"]["note"] = "Install psutil for detailed system metrics"
        
        return self.handle_success(health_data, "Detailed health check completed")

# Create controller instance
health_controller = HealthController()

# Define routes
@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Basic health check endpoint"""
    return await health_controller.health_check()

@router.get("/health/detailed")
async def detailed_health_check():
    """Detailed health check endpoint"""
    return await health_controller.detailed_health_check()
