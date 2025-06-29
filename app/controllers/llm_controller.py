"""
Enhanced LLM controller for handling LLM-related requests with intelligent routing
"""
from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from typing import Optional, Dict, Any

from app.controllers.base_controller import BaseController
from app.models.base_models import LLMRequest, LLMResponse, ProvidersResponse, LoadBalancerStats
from app.services.llm_service import LLMService

# Create router instance
router = APIRouter()

class LLMController(BaseController):
    """
    Enhanced controller for LLM-related endpoints
    """
    
    def __init__(self):
        super().__init__()
        self.llm_service = LLMService()
    
    async def generate_completion(self, query: str, model: Optional[str] = None, 
                                 max_tokens: Optional[int] = None, temperature: Optional[float] = None,
                                 top_p: Optional[float] = None, top_k: Optional[int] = None) -> LLMResponse:
        """
        Generate completion using intelligent provider selection
        """
        try:
            # Validate query
            if not query or len(query.strip()) == 0:
                raise HTTPException(
                    status_code=400,
                    detail="Query cannot be empty"
                )
            
            # Create LLMRequest object
            request = LLMRequest(
                query=query,
                model=model,
                max_tokens=max_tokens or 2048,
                temperature=temperature if temperature is not None else 0.7,
                top_p=top_p if top_p is not None else 0.9,
                top_k=top_k if top_k is not None else 40
            )
            
            # Generate completion
            result = await self.llm_service.generate_completion(request)
            
            return result
            
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
    
    async def get_providers(self) -> ProvidersResponse:
        """
        Get detailed information about all available providers
        """
        try:
            result = await self.llm_service.get_available_providers()
            return result
            
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to get provider information: {str(e)}"
            )
    
    async def get_provider_stats(self) -> Dict[str, Any]:
        """
        Get comprehensive provider and load balancer statistics
        """
        try:
            stats = await self.llm_service.get_provider_stats()
            return self.handle_success(
                data=stats,
                message="Successfully retrieved provider statistics"
            )
            
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to get provider statistics: {str(e)}"
            )
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform comprehensive health check of all providers
        """
        try:
            health_info = await self.llm_service.health_check()
            return self.handle_success(
                data=health_info,
                message="Health check completed"
            )
            
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Health check failed: {str(e)}"
            )
    
    async def test_provider(self, provider: str) -> Dict[str, Any]:
        """
        Test a specific provider with a simple request
        """
        try:
            result = await self.llm_service.test_provider(provider)
            
            if result["success"]:
                return self.handle_success(
                    data=result,
                    message=f"Provider '{provider}' test completed successfully"
                )
            else:
                return self.handle_error(
                    message=f"Provider '{provider}' test failed",
                    details=result
                )
                
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to test provider '{provider}': {str(e)}"
            )
    
    async def get_supported_models(self) -> Dict[str, Any]:
        """
        Get list of all supported models across all providers
        """
        try:
            models = self.llm_service.get_supported_models()
            
            return self.handle_success(
                data={
                    "models": models,
                    "total_models": len(models)
                },
                message=f"Found {len(models)} supported models"
            )
            
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to get supported models: {str(e)}"
            )
    
    async def get_providers_for_model(self, model: str) -> Dict[str, Any]:
        """
        Get list of providers that support a specific model
        """
        try:
            providers = self.llm_service.get_provider_for_model(model)
            
            return self.handle_success(
                data={
                    "model": model,
                    "providers": providers,
                    "total_providers": len(providers)
                },
                message=f"Found {len(providers)} providers supporting model '{model}'"
            )
            
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to get providers for model '{model}': {str(e)}"
            )


# Initialize controller
llm_controller = LLMController()

# Define routes
@router.post("/completions", response_model=LLMResponse, summary="Generate Completion")
async def generate_completion_endpoint(
    query: str = Query(..., description="The query/question to send to the LLM"),
    model: Optional[str] = Query(None, description="Preferred model to use"),
    max_tokens: Optional[int] = Query(2048, ge=1, le=8192, description="Maximum tokens to generate"),
    temperature: Optional[float] = Query(0.7, ge=0.0, le=2.0, description="Temperature for randomness (0.0-2.0)"),
    top_p: Optional[float] = Query(0.9, ge=0.0, le=1.0, description="Top-p sampling parameter (0.0-1.0)"),
    top_k: Optional[int] = Query(40, ge=1, description="Top-k sampling parameter")
):
    """
    Generate text completion using the best available LLM provider.
    
    This endpoint automatically selects the optimal provider based on:
    - Current availability and rate limits
    - Response time and reliability
    - Model compatibility
    - Load balancing strategy
    
    **Query Parameters:**
    - **query**: The question/prompt to send to the LLM
    - **model**: Preferred model (optional, will auto-select if not available)
    - **max_tokens**: Maximum tokens to generate (default: 2048)
    - **temperature**: Randomness control 0.0-2.0 (default: 0.7)
    - **top_p**: Nucleus sampling 0.0-1.0 (default: 0.9)
    - **top_k**: Top-k sampling (default: 40)
    """
    return await llm_controller.generate_completion(
        query=query,
        model=model,
        max_tokens=max_tokens,
        temperature=temperature,
        top_p=top_p,
        top_k=top_k
    )

@router.get("/providers", response_model=ProvidersResponse, summary="Get Provider Information")
async def get_providers_endpoint():
    """
    Get detailed information about all LLM providers.
    
    Returns information about:
    - Provider availability status
    - Supported models
    - Rate limits and features
    - Current statistics
    """
    return await llm_controller.get_providers()

@router.get("/stats", summary="Get System Statistics")
async def get_stats_endpoint():
    """
    Get comprehensive statistics about providers and load balancer.
    
    Includes:
    - Provider performance metrics
    - Load balancer statistics
    - Success rates and latencies
    - Circuit breaker status
    """
    return await llm_controller.get_provider_stats()

@router.get("/health", summary="System Health Check")
async def health_check_endpoint():
    """
    Perform comprehensive health check of all providers.
    
    Checks:
    - Provider availability
    - API key configuration
    - Rate limit status
    - Overall system health
    """
    return await llm_controller.health_check()

@router.post("/test/{provider}", summary="Test Specific Provider")
async def test_provider_endpoint(provider: str):
    """
    Test a specific provider with a simple request.
    
    Useful for:
    - Debugging provider issues
    - Verifying API key configuration
    - Checking provider responsiveness
    """
    return await llm_controller.test_provider(provider)

@router.get("/models", summary="Get Supported Models")
async def get_models_endpoint():
    """
    Get list of all supported models across all providers.
    """
    return await llm_controller.get_supported_models()

@router.get("/models/{model}/providers", summary="Get Providers for Model")
async def get_providers_for_model_endpoint(model: str):
    """
    Get list of providers that support a specific model.
    """
    return await llm_controller.get_providers_for_model(model)
