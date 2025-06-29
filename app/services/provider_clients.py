"""
LLM Provider Client implementations for various APIs
"""
import asyncio
import json
import time
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from enum import Enum

import httpx

try:
    import aiohttp
    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False

try:
    from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
    TENACITY_AVAILABLE = True
except ImportError:
    TENACITY_AVAILABLE = False
    # Create dummy decorators
    def retry(*args, **kwargs):
        def decorator(func):
            return func
        return decorator
    
    stop_after_attempt = lambda x: None
    wait_exponential = lambda **kwargs: None
    retry_if_exception_type = lambda x: None

from app.config.settings import settings
from app.models.base_models import LLMRequest, LLMResponse
from app.utils.rate_limiter import RateLimit, rate_limiter_manager


class ProviderStatus(Enum):
    """Provider availability status"""
    AVAILABLE = "available"
    RATE_LIMITED = "rate_limited"
    ERROR = "error"
    UNAVAILABLE = "unavailable"


@dataclass
class ProviderResponse:
    """Response from a provider"""
    content: str
    provider: str
    model: str
    usage: Dict[str, Any]
    latency: float
    status: ProviderStatus


class BaseProviderClient(ABC):
    """Abstract base class for LLM provider clients"""
    
    def __init__(self, provider_name: str, config: Dict[str, Any]):
        self.provider_name = provider_name
        self.config = config
        self.base_url = config["base_url"]
        self.api_key = self._get_api_key(config["api_key_env"])
        
        # Enhanced rate limits configuration
        self.rate_limits = self._build_rate_limits(config)
        self.models = config["models"]
        self.supports_temperature = config.get("supports_temperature", True)
        self.supports_top_p = config.get("supports_top_p", True)
        self.supports_top_k = config.get("supports_top_k", False)
        
        # Statistics
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        self.last_request_time = 0
        self.average_latency = 0.0
        self.total_tokens_used = 0
    
    def _get_api_key(self, env_var: str) -> str:
        """Get API key from environment variable"""
        import os
        return os.getenv(env_var, "")
    
    def _build_rate_limits(self, config: Dict[str, Any]) -> Dict[str, RateLimit]:
        """Build rate limit configurations for different models"""
        rate_limits = {}
        
        # Get rate limits configuration
        rate_limits_config = config.get("rate_limits", {})
        
        # Handle old format (backward compatibility)
        if "rate_limit" in config:
            default_limit = RateLimit(
                requests_per_minute=config["rate_limit"],
                tokens_per_minute=config.get("token_limit"),
                requests_per_day=config.get("daily_limit"),
                tokens_per_day=config.get("daily_token_limit")
            )
            rate_limits["default"] = default_limit
            return rate_limits
        
        # Build rate limits for each model/configuration
        for key, limits in rate_limits_config.items():
            rate_limits[key] = RateLimit(
                requests_per_minute=limits.get("requests_per_minute"),
                requests_per_hour=limits.get("requests_per_hour"),
                requests_per_day=limits.get("requests_per_day"),
                requests_per_month=limits.get("requests_per_month"),
                tokens_per_minute=limits.get("tokens_per_minute"),
                tokens_per_hour=limits.get("tokens_per_hour"),
                tokens_per_day=limits.get("tokens_per_day"),
                tokens_per_month=limits.get("tokens_per_month")
            )
        
        return rate_limits
    
    def _get_rate_limit_for_model(self, model: str) -> RateLimit:
        """Get appropriate rate limit for a specific model"""
        if model in self.rate_limits:
            return self.rate_limits[model]
        elif "default" in self.rate_limits:
            return self.rate_limits["default"]
        else:
            # Fallback to a basic rate limit
            return RateLimit(requests_per_minute=10, tokens_per_minute=10000)
    
    @abstractmethod
    async def generate_completion(self, request: LLMRequest) -> ProviderResponse:
        """Generate completion using the provider"""
        pass
    
    async def check_availability(self, model: str = None) -> Tuple[bool, Dict[str, Any]]:
        """Check if provider is available for a specific model"""
        if not self.api_key:
            return False, {"error": "API key not configured"}
        
        # Get appropriate rate limit
        rate_limit = self._get_rate_limit_for_model(model or "default")
        
        # Check rate limits
        allowed, rate_info = await rate_limiter_manager.check_rate_limit(
            f"{self.provider_name}:{model or 'default'}", rate_limit
        )
        
        if not allowed:
            return False, {
                "error": "Rate limit exceeded",
                "rate_info": rate_info
            }
        
        return True, {"status": "available"}
    
    async def record_token_usage(self, model: str, tokens_used: int):
        """Record token usage for rate limiting"""
        self.total_tokens_used += tokens_used
        await rate_limiter_manager.record_token_usage(
            f"{self.provider_name}:{model}", tokens_used
        )
    
    async def get_rate_limit_status(self, model: str = None) -> Dict[str, Any]:
        """Get current rate limit status"""
        rate_limit = self._get_rate_limit_for_model(model or "default")
        return await rate_limiter_manager.get_rate_limit_status(
            f"{self.provider_name}:{model or 'default'}", rate_limit
        )
    
    def _build_parameters(self, request: LLMRequest) -> Dict[str, Any]:
        """Build parameters for the API request"""
        params = {
            "max_tokens": request.max_tokens or settings.DEFAULT_MAX_TOKENS,
        }
        
        if self.supports_temperature and request.temperature is not None:
            params["temperature"] = request.temperature
        
        if self.supports_top_p and request.top_p is not None:
            params["top_p"] = request.top_p
        
        if self.supports_top_k and request.top_k is not None:
            params["top_k"] = request.top_k
        
        return params
    
    def _update_stats(self, success: bool, latency: float):
        """Update provider statistics"""
        self.total_requests += 1
        self.last_request_time = time.time()
        
        if success:
            self.successful_requests += 1
        else:
            self.failed_requests += 1
        
        # Update average latency
        if self.total_requests == 1:
            self.average_latency = latency
        else:
            self.average_latency = (
                (self.average_latency * (self.total_requests - 1) + latency) 
                / self.total_requests
            )
    
    def get_stats(self) -> Dict[str, Any]:
        """Get provider statistics"""
        success_rate = (
            self.successful_requests / self.total_requests 
            if self.total_requests > 0 else 0
        )
        
        return {
            "provider": self.provider_name,
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "success_rate": success_rate,
            "average_latency": self.average_latency,
            "last_request_time": self.last_request_time,
            "total_tokens_used": self.total_tokens_used,
            "models": self.models,
            "available": success_rate > 0.5 if self.total_requests > 0 else True
        }


class OpenAICompatibleClient(BaseProviderClient):
    """Client for OpenAI-compatible APIs (Groq, Cerebras, SambaNova, etc.)"""
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.ConnectError))
    )
    async def generate_completion(self, request: LLMRequest) -> ProviderResponse:
        """Generate completion using OpenAI-compatible API"""
        start_time = time.time()
        model = request.model if request.model in self.models else self.models[0]
        
        try:
            # Check availability for specific model
            available, availability_info = await self.check_availability(model)
            if not available:
                raise Exception(f"Provider unavailable: {availability_info}")
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            # Add provider-specific headers
            if self.provider_name == "openrouter":
                headers["HTTP-Referer"] = "https://your-app.com"
                headers["X-Title"] = "LLM API Aggregator"
            
            payload = {
                "model": model,
                "messages": [{"role": "user", "content": request.query}],
                **self._build_parameters(request)
            }
            
            # Make API request
            async with httpx.AsyncClient(timeout=settings.REQUEST_TIMEOUT) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    json=payload,
                    headers=headers
                )
                
                latency = time.time() - start_time
                
                if response.status_code == 429:
                    self._update_stats(False, latency)
                    raise Exception(f"Rate limit exceeded: {response.text}")
                
                response.raise_for_status()
                result = response.json()
                
                # Extract response content
                content = result["choices"][0]["message"]["content"]
                usage = result.get("usage", {})
                
                # Record token usage for rate limiting
                if "total_tokens" in usage:
                    await self.record_token_usage(model, usage["total_tokens"])
                elif "prompt_tokens" in usage and "completion_tokens" in usage:
                    total_tokens = usage["prompt_tokens"] + usage["completion_tokens"]
                    await self.record_token_usage(model, total_tokens)
                
                self._update_stats(True, latency)
                
                return ProviderResponse(
                    content=content,
                    provider=self.provider_name,
                    model=model,
                    usage=usage,
                    latency=latency,
                    status=ProviderStatus.AVAILABLE
                )
                
        except Exception as e:
            latency = time.time() - start_time
            self._update_stats(False, latency)
            
            # Determine status based on error
            status = ProviderStatus.ERROR
            if "rate limit" in str(e).lower() or "429" in str(e):
                status = ProviderStatus.RATE_LIMITED
            elif "timeout" in str(e).lower():
                status = ProviderStatus.UNAVAILABLE
            
            raise Exception(f"{self.provider_name} error: {str(e)}")


class GeminiClient(BaseProviderClient):
    """Client for Google Gemini API"""
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    async def generate_completion(self, request: LLMRequest) -> ProviderResponse:
        """Generate completion using Google Gemini API"""
        start_time = time.time()
        model = request.model if request.model in self.models else self.models[0]
        
        try:
            # Check availability for specific model
            available, availability_info = await self.check_availability(model)
            if not available:
                raise Exception(f"Provider unavailable: {availability_info}")
            
            headers = {
                "Content-Type": "application/json"
            }
            
            # Build generation config
            generation_config = {}
            if self.supports_temperature and request.temperature is not None:
                generation_config["temperature"] = request.temperature
            if self.supports_top_p and request.top_p is not None:
                generation_config["topP"] = request.top_p
            if self.supports_top_k and request.top_k is not None:
                generation_config["topK"] = request.top_k
            if request.max_tokens:
                generation_config["maxOutputTokens"] = request.max_tokens or settings.DEFAULT_MAX_TOKENS
            
            payload = {
                "contents": [
                    {
                        "parts": [{"text": request.query}]
                    }
                ]
            }
            
            if generation_config:
                payload["generationConfig"] = generation_config
            
            # Make API request
            url = f"{self.base_url}/models/{model}:generateContent?key={self.api_key}"
            
            async with httpx.AsyncClient(timeout=settings.REQUEST_TIMEOUT) as client:
                response = await client.post(url, json=payload, headers=headers)
                
                latency = time.time() - start_time
                
                if response.status_code == 429:
                    self._update_stats(False, latency)
                    raise Exception(f"Rate limit exceeded: {response.text}")
                
                response.raise_for_status()
                result = response.json()
                
                # Extract content from Gemini response format
                if "candidates" in result and result["candidates"]:
                    candidate = result["candidates"][0]
                    content = candidate["content"]["parts"][0]["text"]
                else:
                    raise Exception("No valid response from Gemini")
                
                # Extract usage information
                usage = {}
                if "usageMetadata" in result:
                    metadata = result["usageMetadata"]
                    usage = {
                        "prompt_tokens": metadata.get("promptTokenCount", 0),
                        "completion_tokens": metadata.get("candidatesTokenCount", 0),
                        "total_tokens": metadata.get("totalTokenCount", 0)
                    }
                
                # Record token usage for rate limiting
                if usage.get("total_tokens"):
                    await self.record_token_usage(model, usage["total_tokens"])
                
                self._update_stats(True, latency)
                
                return ProviderResponse(
                    content=content,
                    provider=self.provider_name,
                    model=model,
                    usage=usage,
                    latency=latency,
                    status=ProviderStatus.AVAILABLE
                )
                
        except Exception as e:
            latency = time.time() - start_time
            self._update_stats(False, latency)
            
            # Determine status based on error
            status = ProviderStatus.ERROR
            if "rate limit" in str(e).lower() or "quota" in str(e).lower() or "429" in str(e):
                status = ProviderStatus.RATE_LIMITED
            elif "timeout" in str(e).lower():
                status = ProviderStatus.UNAVAILABLE
            
            raise Exception(f"{self.provider_name} error: {str(e)}")


class ProviderClientFactory:
    """Factory for creating provider clients"""
    
    @staticmethod
    def create_client(provider_name: str, config: Dict[str, Any]) -> BaseProviderClient:
        """Create appropriate client for provider"""
        if provider_name == "gemini":
            return GeminiClient(provider_name, config)
        else:
            # Most providers use OpenAI-compatible API
            return OpenAICompatibleClient(provider_name, config)


class ProviderManager:
    """Manages all LLM provider clients"""
    
    def __init__(self):
        self.clients: Dict[str, BaseProviderClient] = {}
        self._initialize_clients()
    
    def _initialize_clients(self):
        """Initialize all provider clients"""
        for provider_name, config in settings.LLM_PROVIDERS.items():
            self.clients[provider_name] = ProviderClientFactory.create_client(
                provider_name, config
            )
    
    async def get_available_providers(self) -> List[str]:
        """Get list of currently available providers"""
        available = []
        
        for provider_name, client in self.clients.items():
            is_available, _ = await client.check_availability()
            if is_available:
                available.append(provider_name)
        
        return available
    
    async def get_provider_stats(self) -> Dict[str, Any]:
        """Get statistics for all providers"""
        stats = {}
        
        for provider_name, client in self.clients.items():
            stats[provider_name] = client.get_stats()
            
            # Add availability info
            is_available, availability_info = await client.check_availability()
            stats[provider_name]["available"] = is_available
            stats[provider_name]["availability_info"] = availability_info
        
        return stats
    
    def get_client(self, provider_name: str) -> Optional[BaseProviderClient]:
        """Get client for specific provider"""
        return self.clients.get(provider_name)
    
    def get_all_clients(self) -> Dict[str, BaseProviderClient]:
        """Get all clients"""
        return self.clients.copy()


# Global provider manager instance
provider_manager = ProviderManager()