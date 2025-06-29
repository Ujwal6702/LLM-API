"""
Intelligent Load Balancer for LLM Providers
"""
import asyncio
import random
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import List, Dict, Any, Optional, Tuple
from collections import defaultdict

from app.models.base_models import LLMRequest
from app.services.provider_clients import (
    BaseProviderClient, ProviderResponse, ProviderStatus, provider_manager
)


class LoadBalancingStrategy(Enum):
    """Load balancing strategies"""
    ROUND_ROBIN = "round_robin"
    WEIGHTED_ROUND_ROBIN = "weighted_round_robin"
    LEAST_CONNECTIONS = "least_connections"
    RESPONSE_TIME = "response_time"
    AVAILABILITY_WEIGHTED = "availability_weighted"
    SMART_ROUTING = "smart_routing"


@dataclass
class ProviderScore:
    """Provider scoring for load balancing"""
    provider: str
    score: float
    available: bool
    latency: float
    success_rate: float
    current_load: int


class BaseLoadBalancer(ABC):
    """Abstract base class for load balancers"""
    
    @abstractmethod
    async def select_provider(self, request: LLMRequest) -> Optional[str]:
        """Select the best provider for a request"""
        pass
    
    @abstractmethod
    def update_provider_stats(self, provider: str, success: bool, latency: float):
        """Update provider statistics"""
        pass


class RoundRobinBalancer(BaseLoadBalancer):
    """Simple round-robin load balancer"""
    
    def __init__(self):
        self.current_index = 0
    
    async def select_provider(self, request: LLMRequest) -> Optional[str]:
        """Select provider using round-robin"""
        available_providers = await provider_manager.get_available_providers()
        
        if not available_providers:
            return None
        
        provider = available_providers[self.current_index % len(available_providers)]
        self.current_index += 1
        
        return provider
    
    def update_provider_stats(self, provider: str, success: bool, latency: float):
        """No stats tracking for simple round-robin"""
        pass


class WeightedRoundRobinBalancer(BaseLoadBalancer):
    """Weighted round-robin based on provider performance"""
    
    def __init__(self):
        self.weights: Dict[str, float] = {}
        self.current_weights: Dict[str, float] = {}
    
    async def select_provider(self, request: LLMRequest) -> Optional[str]:
        """Select provider using weighted round-robin"""
        available_providers = await provider_manager.get_available_providers()
        
        if not available_providers:
            return None
        
        # Initialize weights if needed
        for provider in available_providers:
            if provider not in self.weights:
                self.weights[provider] = 1.0
                self.current_weights[provider] = 1.0
        
        # Find provider with highest current weight
        best_provider = max(
            available_providers,
            key=lambda p: self.current_weights.get(p, 0)
        )
        
        # Update current weights
        self.current_weights[best_provider] -= 1.0
        for provider in available_providers:
            self.current_weights[provider] += self.weights[provider]
        
        return best_provider
    
    def update_provider_stats(self, provider: str, success: bool, latency: float):
        """Update weights based on performance"""
        if provider not in self.weights:
            self.weights[provider] = 1.0
        
        # Adjust weight based on success and latency
        if success:
            # Reward fast responses
            if latency < 1.0:
                self.weights[provider] = min(5.0, self.weights[provider] * 1.1)
            elif latency > 5.0:
                self.weights[provider] = max(0.1, self.weights[provider] * 0.9)
        else:
            # Penalize failures
            self.weights[provider] = max(0.1, self.weights[provider] * 0.8)


class ResponseTimeBalancer(BaseLoadBalancer):
    """Load balancer based on response time"""
    
    def __init__(self):
        self.response_times: Dict[str, List[float]] = defaultdict(list)
        self.max_history = 10
    
    async def select_provider(self, request: LLMRequest) -> Optional[str]:
        """Select provider with best average response time"""
        available_providers = await provider_manager.get_available_providers()
        
        if not available_providers:
            return None
        
        # Calculate average response times
        provider_scores = []
        for provider in available_providers:
            times = self.response_times[provider]
            avg_time = sum(times) / len(times) if times else 1.0
            provider_scores.append((provider, avg_time))
        
        # Sort by response time (ascending)
        provider_scores.sort(key=lambda x: x[1])
        
        return provider_scores[0][0]
    
    def update_provider_stats(self, provider: str, success: bool, latency: float):
        """Update response time history"""
        if success:  # Only track successful responses
            times = self.response_times[provider]
            times.append(latency)
            
            # Keep only recent history
            if len(times) > self.max_history:
                times.pop(0)


class SmartLoadBalancer(BaseLoadBalancer):
    """Intelligent load balancer with multiple factors"""
    
    def __init__(self):
        self.provider_stats: Dict[str, Dict[str, Any]] = defaultdict(dict)
        self.current_loads: Dict[str, int] = defaultdict(int)
        self.last_selection_time: Dict[str, float] = {}
    
    async def select_provider(self, request: LLMRequest) -> Optional[str]:
        """Select provider using smart routing algorithm"""
        available_providers = await provider_manager.get_available_providers()
        
        if not available_providers:
            return None
        
        # Score each provider
        provider_scores = []
        current_time = time.time()
        
        for provider in available_providers:
            score = await self._calculate_provider_score(provider, current_time, request)
            provider_scores.append((provider, score))
        
        # Sort by score (descending)
        provider_scores.sort(key=lambda x: x[1], reverse=True)
        
        # Use weighted random selection from top providers
        top_providers = provider_scores[:min(3, len(provider_scores))]
        weights = [score for _, score in top_providers]
        total_weight = sum(weights)
        
        if total_weight == 0:
            return provider_scores[0][0]
        
        # Weighted random selection
        rand_val = random.uniform(0, total_weight)
        current_weight = 0
        
        for provider, weight in top_providers:
            current_weight += weight
            if rand_val <= current_weight:
                # Track selection
                self.current_loads[provider] += 1
                self.last_selection_time[provider] = current_time
                return provider
        
        return top_providers[0][0]
    
    async def _calculate_provider_score(self, provider: str, current_time: float, request: LLMRequest = None) -> float:
        """Calculate comprehensive score for provider"""
        client = provider_manager.get_client(provider)
        if not client:
            return 0.0
        
        stats = client.get_stats()
        
        # Base score factors
        success_rate = stats.get("success_rate", 0.0)
        avg_latency = stats.get("average_latency", 10.0)
        total_requests = stats.get("total_requests", 0)
        
        # Calculate individual factor scores (0-1 scale)
        
        # 1. Success rate score
        success_score = success_rate
        
        # 2. Latency score (inverse relationship)
        latency_score = max(0, 1 - (avg_latency / 10.0))  # Normalize to 10s max
        
        # 3. Load balancing score (prefer less loaded providers)
        current_load = self.current_loads.get(provider, 0)
        max_load = max(self.current_loads.values()) if self.current_loads else 1
        load_score = 1 - (current_load / max(max_load, 1))
        
        # 4. Recency score (avoid recently used providers for better distribution)
        last_used = self.last_selection_time.get(provider, 0)
        time_since_last = current_time - last_used
        recency_score = min(1.0, time_since_last / 60.0)  # 1 minute cooldown
        
        # 5. Experience score (prefer providers with more data)
        experience_score = min(1.0, total_requests / 100.0)  # Normalize to 100 requests
        
        # 6. Model compatibility score
        model_score = 1.0
        if hasattr(request, 'model') and request.model:
            if request.model in client.models:
                model_score = 1.0
            else:
                model_score = 0.5  # Partial score for fallback model
        
        # Weighted combination of factors
        weights = {
            'success': 0.30,
            'latency': 0.25,
            'load': 0.20,
            'recency': 0.10,
            'experience': 0.10,
            'model': 0.05
        }
        
        total_score = (
            weights['success'] * success_score +
            weights['latency'] * latency_score +
            weights['load'] * load_score +
            weights['recency'] * recency_score +
            weights['experience'] * experience_score +
            weights['model'] * model_score
        )
        
        return total_score
    
    def update_provider_stats(self, provider: str, success: bool, latency: float):
        """Update provider statistics"""
        # Decrease current load
        if provider in self.current_loads:
            self.current_loads[provider] = max(0, self.current_loads[provider] - 1)
        
        # Update stats
        if provider not in self.provider_stats:
            self.provider_stats[provider] = {
                'total_requests': 0,
                'successful_requests': 0,
                'failed_requests': 0,
                'total_latency': 0.0
            }
        
        stats = self.provider_stats[provider]
        stats['total_requests'] += 1
        stats['total_latency'] += latency
        
        if success:
            stats['successful_requests'] += 1
        else:
            stats['failed_requests'] += 1


class LoadBalancerManager:
    """Manages load balancing strategies and failover"""
    
    def __init__(self, strategy: LoadBalancingStrategy = LoadBalancingStrategy.SMART_ROUTING):
        self.strategy = strategy
        self.balancer = self._create_balancer(strategy)
        self.retry_attempts = 3
        self.circuit_breaker_threshold = 5  # failures before circuit break
        self.circuit_breaker_timeout = 300  # 5 minutes
        self.failed_providers: Dict[str, float] = {}
    
    def _create_balancer(self, strategy: LoadBalancingStrategy) -> BaseLoadBalancer:
        """Create appropriate load balancer"""
        if strategy == LoadBalancingStrategy.ROUND_ROBIN:
            return RoundRobinBalancer()
        elif strategy == LoadBalancingStrategy.WEIGHTED_ROUND_ROBIN:
            return WeightedRoundRobinBalancer()
        elif strategy == LoadBalancingStrategy.RESPONSE_TIME:
            return ResponseTimeBalancer()
        elif strategy == LoadBalancingStrategy.SMART_ROUTING:
            return SmartLoadBalancer()
        else:
            return SmartLoadBalancer()  # Default to smart routing
    
    async def route_request(self, request: LLMRequest) -> ProviderResponse:
        """Route request to best available provider with failover"""
        attempts = 0
        last_error = None
        
        while attempts < self.retry_attempts:
            attempts += 1
            
            # Select provider
            provider_name = await self.balancer.select_provider(request)
            
            if not provider_name:
                # No providers available, wait and retry
                if attempts < self.retry_attempts:
                    await asyncio.sleep(1)
                    continue
                else:
                    raise Exception("No providers available after retries")
            
            # Check circuit breaker
            if self._is_circuit_broken(provider_name):
                continue
            
            try:
                # Get provider client
                client = provider_manager.get_client(provider_name)
                if not client:
                    continue
                
                # Make request
                start_time = time.time()
                response = await client.generate_completion(request)
                latency = time.time() - start_time
                
                # Update balancer stats
                self.balancer.update_provider_stats(provider_name, True, latency)
                
                # Reset circuit breaker on success
                if provider_name in self.failed_providers:
                    del self.failed_providers[provider_name]
                
                return response
                
            except Exception as e:
                last_error = e
                latency = time.time() - start_time if 'start_time' in locals() else 1.0
                
                # Update balancer stats
                self.balancer.update_provider_stats(provider_name, False, latency)
                
                # Update circuit breaker
                self._update_circuit_breaker(provider_name)
                
                # If this was the last attempt, don't wait
                if attempts < self.retry_attempts:
                    await asyncio.sleep(min(attempts * 0.5, 2.0))  # Exponential backoff
        
        # All attempts failed
        raise Exception(f"All providers failed. Last error: {last_error}")
    
    def _is_circuit_broken(self, provider: str) -> bool:
        """Check if circuit breaker is active for provider"""
        if provider not in self.failed_providers:
            return False
        
        last_failure_time = self.failed_providers[provider]
        return time.time() - last_failure_time < self.circuit_breaker_timeout
    
    def _update_circuit_breaker(self, provider: str):
        """Update circuit breaker state"""
        self.failed_providers[provider] = time.time()
    
    async def get_load_balancer_stats(self) -> Dict[str, Any]:
        """Get load balancer statistics"""
        provider_stats = await provider_manager.get_provider_stats()
        
        return {
            "strategy": self.strategy.value,
            "total_providers": len(provider_manager.get_all_clients()),
            "available_providers": len(await provider_manager.get_available_providers()),
            "circuit_broken_providers": len(self.failed_providers),
            "provider_stats": provider_stats,
            "failed_providers": {
                provider: {
                    "last_failure": failure_time,
                    "time_until_retry": max(0, self.circuit_breaker_timeout - (time.time() - failure_time))
                }
                for provider, failure_time in self.failed_providers.items()
            }
        }


# Global load balancer instance
load_balancer = LoadBalancerManager(LoadBalancingStrategy.SMART_ROUTING)