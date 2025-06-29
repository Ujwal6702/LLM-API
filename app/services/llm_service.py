"""
Enhanced LLM Service with intelligent routing and load balancing
"""
import asyncio
import time
import uuid
from typing import Dict, List, Optional, Any

from app.services.base_service import BaseService
from app.models.base_models import LLMRequest, LLMResponse, ProviderInfo, ProvidersResponse
from app.services.load_balancer import load_balancer
from app.services.provider_clients import provider_manager, ProviderStatus
from app.config.settings import settings


class LLMService(BaseService):
    """
    Enhanced service for handling LLM operations with intelligent routing
    """
    
    def __init__(self):
        super().__init__()
        self.provider_manager = provider_manager
        self.load_balancer = load_balancer
    
    async def execute(self, request: LLMRequest) -> LLMResponse:
        """
        Execute the service logic (implementation of abstract method)
        """
        return await self.generate_completion(request)
    
    async def generate_completion(self, request: LLMRequest) -> LLMResponse:
        """
        Generate completion using intelligent load balancing and failover
        """
        if not self._validate_request(request):
            raise ValueError("Invalid request parameters")
        
        # Generate unique request ID
        request_id = str(uuid.uuid4())
        
        try:
            # Route request through load balancer
            provider_response = await self.load_balancer.route_request(request)
            
            # Convert to LLMResponse
            return LLMResponse(
                response=provider_response.content,
                provider=provider_response.provider,
                model_used=provider_response.model,
                usage=provider_response.usage,
                latency=provider_response.latency,
                request_id=request_id,
                message=f"Request completed successfully using {provider_response.provider}"
            )
            
        except Exception as e:
            # Create error response
            return LLMResponse(
                success=False,
                response="",
                provider="none",
                model_used="none",
                usage={},
                latency=0.0,
                request_id=request_id,
                message=f"Request failed: {str(e)}"
            )
    
    async def get_available_providers(self) -> ProvidersResponse:
        """
        Get detailed information about all providers
        """
        try:
            providers_info = []
            total_providers = 0
            available_count = 0
            
            for provider_name, client in self.provider_manager.get_all_clients().items():
                total_providers += 1
                
                # Get availability
                is_available, availability_info = await client.check_availability()
                if is_available:
                    available_count += 1
                
                # Get statistics
                stats = client.get_stats()
                
                # Build provider info
                provider_info = ProviderInfo(
                    name=provider_name,
                    available=is_available,
                    models=client.models,
                    rate_limit=client.rate_limit.requests_per_minute,
                    daily_limit=client.rate_limit.requests_per_day,
                    features={
                        "temperature": client.supports_temperature,
                        "top_p": client.supports_top_p,
                        "top_k": client.supports_top_k,
                        "streaming": False  # TODO: Add streaming support
                    },
                    stats={
                        **stats,
                        "availability_info": availability_info
                    }
                )
                
                providers_info.append(provider_info)
            
            return ProvidersResponse(
                providers=providers_info,
                total_providers=total_providers,
                available_providers=available_count,
                message=f"Found {total_providers} providers, {available_count} available"
            )
            
        except Exception as e:
            return ProvidersResponse(
                success=False,
                providers=[],
                total_providers=0,
                available_providers=0,
                message=f"Failed to get provider information: {str(e)}"
            )
    
    async def get_provider_stats(self) -> Dict[str, Any]:
        """
        Get comprehensive statistics for all providers
        """
        try:
            stats = await self.provider_manager.get_provider_stats()
            lb_stats = await self.load_balancer.get_load_balancer_stats()
            
            return {
                "provider_stats": stats,
                "load_balancer_stats": lb_stats,
                "summary": {
                    "total_providers": len(stats),
                    "available_providers": sum(1 for p in stats.values() if p.get("available", False)),
                    "total_requests": sum(p.get("total_requests", 0) for p in stats.values()),
                    "successful_requests": sum(p.get("successful_requests", 0) for p in stats.values()),
                    "average_success_rate": self._calculate_average_success_rate(stats)
                }
            }
            
        except Exception as e:
            return {
                "error": f"Failed to get statistics: {str(e)}",
                "provider_stats": {},
                "load_balancer_stats": {},
                "summary": {}
            }
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform comprehensive health check
        """
        try:
            # Test each provider
            provider_health = {}
            available_providers = await self.provider_manager.get_available_providers()
            
            for provider_name, client in self.provider_manager.get_all_clients().items():
                is_available, info = await client.check_availability()
                
                provider_health[provider_name] = {
                    "available": is_available,
                    "info": info,
                    "has_api_key": bool(client.api_key),
                    "models_count": len(client.models)
                }
            
            # Overall health status
            total_providers = len(self.provider_manager.get_all_clients())
            available_count = len(available_providers)
            health_ratio = available_count / total_providers if total_providers > 0 else 0
            
            if health_ratio >= 0.7:
                overall_status = "healthy"
            elif health_ratio >= 0.3:
                overall_status = "degraded"
            else:
                overall_status = "unhealthy"
            
            return {
                "status": overall_status,
                "total_providers": total_providers,
                "available_providers": available_count,
                "health_ratio": health_ratio,
                "provider_health": provider_health,
                "load_balancer_strategy": self.load_balancer.strategy.value
            }
            
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "total_providers": 0,
                "available_providers": 0,
                "health_ratio": 0.0
            }
    
    async def test_provider(self, provider_name: str) -> Dict[str, Any]:
        """
        Test a specific provider with a simple request
        """
        try:
            client = self.provider_manager.get_client(provider_name)
            if not client:
                return {
                    "success": False,
                    "error": f"Provider '{provider_name}' not found"
                }
            
            # Check availability first
            is_available, availability_info = await client.check_availability()
            if not is_available:
                return {
                    "success": False,
                    "error": "Provider not available",
                    "details": availability_info
                }
            
            # Create test request
            test_request = LLMRequest(
                query="Say 'Hello, World!' in one sentence.",
                max_tokens=50,
                temperature=0.7
            )
            
            # Make test request
            start_time = time.time()
            response = await client.generate_completion(test_request)
            latency = time.time() - start_time
            
            return {
                "success": True,
                "provider": provider_name,
                "response": response.content[:100] + "..." if len(response.content) > 100 else response.content,
                "latency": latency,
                "model_used": response.model,
                "usage": response.usage
            }
            
        except Exception as e:
            return {
                "success": False,
                "provider": provider_name,
                "error": str(e)
            }
    
    async def get_rate_limit_status(self, provider_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Get current rate limit status for providers
        """
        try:
            if provider_name:
                # Get status for specific provider
                if provider_name not in self.provider_manager.get_all_clients():
                    raise ValueError(f"Provider '{provider_name}' not found")
                
                client = self.provider_manager.get_client(provider_name)
                status = {}
                
                # Get status for each model supported by the provider
                for model in client.models:
                    model_status = await client.get_rate_limit_status(model)
                    status[model] = model_status
                
                # Also get default status
                default_status = await client.get_rate_limit_status()
                status["default"] = default_status
                
                return {
                    "provider": provider_name,
                    "rate_limits": status,
                    "provider_stats": client.get_stats()
                }
            else:
                # Get status for all providers
                all_status = {}
                
                for provider_name, client in self.provider_manager.get_all_clients().items():
                    provider_status = {}
                    
                    # Get status for each model
                    for model in client.models:
                        model_status = await client.get_rate_limit_status(model)
                        provider_status[model] = model_status
                    
                    # Also get default status
                    default_status = await client.get_rate_limit_status()
                    provider_status["default"] = default_status
                    
                    all_status[provider_name] = {
                        "rate_limits": provider_status,
                        "provider_stats": client.get_stats()
                    }
                
                return {
                    "providers": all_status,
                    "summary": {
                        "total_providers": len(all_status),
                        "timestamp": time.time()
                    }
                }
                
        except Exception as e:
            return {
                "error": f"Failed to get rate limit status: {str(e)}",
                "providers": {},
                "summary": {
                    "total_providers": 0,
                    "timestamp": time.time()
                }
            }
    
    def _validate_request(self, request: LLMRequest) -> bool:
        """
        Validate LLM request parameters
        """
        if not request.query or len(request.query.strip()) == 0:
            return False
        
        if request.max_tokens and (request.max_tokens < 1 or request.max_tokens > 8192):
            return False
        
        if request.temperature and (request.temperature < 0.0 or request.temperature > 2.0):
            return False
        
        if request.top_p and (request.top_p < 0.0 or request.top_p > 1.0):
            return False
        
        if request.top_k and request.top_k < 1:
            return False
        
        return True
    
    def _calculate_average_success_rate(self, stats: Dict[str, Any]) -> float:
        """
        Calculate average success rate across all providers
        """
        total_requests = 0
        successful_requests = 0
        
        for provider_stats in stats.values():
            total_requests += provider_stats.get("total_requests", 0)
            successful_requests += provider_stats.get("successful_requests", 0)
        
        return successful_requests / total_requests if total_requests > 0 else 0.0
    
    def get_supported_models(self) -> List[str]:
        """
        Get list of all supported models across providers
        """
        all_models = set()
        
        for client in self.provider_manager.get_all_clients().values():
            all_models.update(client.models)
        
        return sorted(list(all_models))
    
    def get_provider_for_model(self, model: str) -> List[str]:
        """
        Get list of providers that support a specific model
        """
        supporting_providers = []
        
        for provider_name, client in self.provider_manager.get_all_clients().items():
            if model in client.models:
                supporting_providers.append(provider_name)
        
        return supporting_providers
        return self.available_providers
