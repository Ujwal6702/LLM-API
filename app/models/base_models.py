"""
Base models and data structures
"""
from datetime import datetime
from typing import Optional, Any, Dict, List
from pydantic import BaseModel, Field


class BaseResponse(BaseModel):
    """
    Base response model for all API responses
    """
    success: bool = True
    message: str = "Success"
    timestamp: datetime = Field(default_factory=datetime.now)


class ErrorResponse(BaseResponse):
    """
    Error response model
    """
    success: bool = False
    error_code: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


class HealthResponse(BaseResponse):
    """
    Health check response model
    """
    status: str = "healthy"
    version: str
    uptime: Optional[float] = None


class LLMRequest(BaseModel):
    """
    Enhanced LLM request model with support for multiple parameters
    """
    query: str = Field(..., description="The query/question to send to the LLM")
    model: Optional[str] = Field(default=None, description="Preferred model to use")
    max_tokens: Optional[int] = Field(default=2048, description="Maximum tokens to generate")
    temperature: Optional[float] = Field(default=0.7, ge=0.0, le=2.0, description="Temperature for randomness (0.0-2.0)")
    top_p: Optional[float] = Field(default=0.9, ge=0.0, le=1.0, description="Top-p sampling parameter (0.0-1.0)")
    top_k: Optional[int] = Field(default=40, ge=1, description="Top-k sampling parameter")
    stream: Optional[bool] = Field(default=False, description="Whether to stream the response")
    stop: Optional[List[str]] = Field(default=None, description="Stop sequences")
    
    class Config:
        json_schema_extra = {
            "example": {
                "query": "Explain quantum computing in simple terms",
                "model": "llama-3.3-70b-versatile",
                "max_tokens": 500,
                "temperature": 0.7,
                "top_p": 0.9,
                "top_k": 40
            }
        }


class LLMResponse(BaseResponse):
    """
    Enhanced LLM response model with detailed information
    """
    response: str = Field(..., description="The LLM's response")
    provider: str = Field(..., description="Provider that handled the request")
    model_used: str = Field(..., description="Model that was actually used")
    usage: Dict[str, Any] = Field(default_factory=dict, description="Token usage information")
    latency: float = Field(..., description="Response latency in seconds")
    request_id: Optional[str] = Field(default=None, description="Unique request identifier")
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "Request completed successfully",
                "response": "Quantum computing is a revolutionary computing paradigm...",
                "provider": "groq",
                "model_used": "llama-3.3-70b-versatile",
                "usage": {
                    "prompt_tokens": 10,
                    "completion_tokens": 150,
                    "total_tokens": 160
                },
                "latency": 1.23,
                "timestamp": "2025-06-28T12:00:00Z"
            }
        }


class ProviderInfo(BaseModel):
    """
    Provider information model
    """
    name: str = Field(..., description="Provider name")
    available: bool = Field(..., description="Whether provider is currently available")
    models: List[str] = Field(..., description="List of available models")
    rate_limit: int = Field(..., description="Requests per minute limit")
    daily_limit: Optional[int] = Field(None, description="Daily request limit")
    features: Dict[str, bool] = Field(..., description="Supported features")
    stats: Dict[str, Any] = Field(default_factory=dict, description="Provider statistics")


class ProvidersResponse(BaseResponse):
    """
    Response model for providers endpoint
    """
    providers: List[ProviderInfo] = Field(..., description="List of provider information")
    total_providers: int = Field(..., description="Total number of providers")
    available_providers: int = Field(..., description="Number of available providers")


class LoadBalancerStats(BaseResponse):
    """
    Load balancer statistics response
    """
    strategy: str = Field(..., description="Current load balancing strategy")
    total_providers: int = Field(..., description="Total number of providers")
    available_providers: int = Field(..., description="Available providers count")
    circuit_broken_providers: int = Field(..., description="Providers with circuit breaker active")
    provider_stats: Dict[str, Any] = Field(..., description="Detailed provider statistics")


class RateLimitInfo(BaseModel):
    """
    Rate limit information model
    """
    allowed: bool = Field(..., description="Whether request was allowed")
    current_count: int = Field(..., description="Current request count")
    limit: int = Field(..., description="Rate limit threshold")
    remaining: Optional[int] = Field(None, description="Remaining requests")
    reset_time: Optional[float] = Field(None, description="When rate limit resets")
    retry_after: Optional[int] = Field(None, description="Seconds to wait before retry")
    model_used: str = Field(..., description="The model that was used")
    tokens_used: Optional[int] = Field(None, description="Number of tokens used")
    provider: str = Field(..., description="The LLM provider used")
