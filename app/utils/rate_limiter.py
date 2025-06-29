"""
Memory-based Rate Limiter with sliding window strategy
"""
import asyncio
import time
from collections import defaultdict, deque
from enum import Enum
from typing import Dict, Optional, Tuple
from dataclasses import dataclass
from abc import ABC, abstractmethod


class RateLimitStrategy(Enum):
    """Rate limiting strategies"""
    TOKEN_BUCKET = "token_bucket"
    SLIDING_WINDOW = "sliding_window"
    FIXED_WINDOW = "fixed_window"
    LEAKY_BUCKET = "leaky_bucket"


@dataclass
class RateLimit:
    """Rate limit configuration"""
    requests_per_minute: int
    requests_per_hour: Optional[int] = None
    requests_per_day: Optional[int] = None
    burst_limit: Optional[int] = None
    token_refill_rate: float = 1.0  # tokens per second


class BaseRateLimiter(ABC):
    """Abstract base class for rate limiters"""
    
    @abstractmethod
    async def is_allowed(self, key: str, limit: RateLimit) -> Tuple[bool, Dict]:
        """Check if request is allowed and return status info"""
        pass
    
    @abstractmethod
    async def reset_limit(self, key: str) -> bool:
        """Reset rate limit for a key"""
        pass


class MemoryRateLimiter(BaseRateLimiter):
    """In-memory rate limiter using sliding window"""
    
    def __init__(self):
        self.windows: Dict[str, deque] = defaultdict(deque)
        self.buckets: Dict[str, Dict] = defaultdict(dict)
        self._lock = asyncio.Lock()
    
    async def is_allowed(self, key: str, limit: RateLimit) -> Tuple[bool, Dict]:
        """Check if request is allowed using sliding window"""
        async with self._lock:
            now = time.time()
            window = self.windows[key]
            
            # Remove expired entries
            cutoff = now - 60  # 1 minute window
            while window and window[0] < cutoff:
                window.popleft()
            
            # Check current count
            current_count = len(window)
            
            if current_count >= limit.requests_per_minute:
                return False, {
                    "allowed": False,
                    "current_count": current_count,
                    "limit": limit.requests_per_minute,
                    "reset_time": cutoff + 60,
                    "retry_after": int(window[0] + 60 - now) if window else 1
                }
            
            # Add current request
            window.append(now)
            
            return True, {
                "allowed": True,
                "current_count": current_count + 1,
                "limit": limit.requests_per_minute,
                "remaining": limit.requests_per_minute - current_count - 1
            }
    
    async def reset_limit(self, key: str) -> bool:
        """Reset rate limit for a key"""
        async with self._lock:
            if key in self.windows:
                self.windows[key].clear()
            if key in self.buckets:
                del self.buckets[key]
            return True


class TokenBucketRateLimiter(BaseRateLimiter):
    """Token bucket rate limiter (memory-based)"""
    
    def __init__(self):
        self.memory_buckets: Dict[str, Dict] = defaultdict(dict)
        self._lock = asyncio.Lock()
    
    async def is_allowed(self, key: str, limit: RateLimit) -> Tuple[bool, Dict]:
        """Check if request is allowed using token bucket algorithm"""
        return await self._memory_token_bucket(key, limit)
    
    async def _memory_token_bucket(self, key: str, limit: RateLimit) -> Tuple[bool, Dict]:
        """Memory-based token bucket"""
        async with self._lock:
            now = time.time()
            bucket = self.memory_buckets[key]
            
            # Initialize bucket if new
            if 'tokens' not in bucket:
                bucket['tokens'] = limit.requests_per_minute
                bucket['last_refill'] = now
            
            # Refill tokens
            time_passed = now - bucket['last_refill']
            refill_rate = limit.requests_per_minute / 60.0  # tokens per second
            new_tokens = time_passed * refill_rate
            bucket['tokens'] = min(limit.requests_per_minute, bucket['tokens'] + new_tokens)
            bucket['last_refill'] = now
            
            # Check if token available
            if bucket['tokens'] >= 1:
                bucket['tokens'] -= 1
                return True, {
                    "allowed": True,
                    "tokens_remaining": int(bucket['tokens']),
                    "refill_rate": refill_rate
                }
            else:
                return False, {
                    "allowed": False,
                    "tokens_remaining": 0,
                    "retry_after": int((1 - bucket['tokens']) / refill_rate)
                }
    
    async def reset_limit(self, key: str) -> bool:
        """Reset rate limit for a key"""
        async with self._lock:
            if key in self.memory_buckets:
                del self.memory_buckets[key]
        return True


class FixedWindowRateLimiter(BaseRateLimiter):
    """Fixed window rate limiter"""
    
    def __init__(self):
        self.windows: Dict[str, Dict] = defaultdict(dict)
        self._lock = asyncio.Lock()
    
    async def is_allowed(self, key: str, limit: RateLimit) -> Tuple[bool, Dict]:
        """Check if request is allowed using fixed window"""
        async with self._lock:
            now = time.time()
            window_start = int(now // 60) * 60  # Start of current minute
            
            if key not in self.windows:
                self.windows[key] = {}
            
            window_data = self.windows[key]
            
            # Reset window if it's a new minute
            if window_data.get('window_start', 0) != window_start:
                window_data['window_start'] = window_start
                window_data['count'] = 0
            
            current_count = window_data['count']
            
            if current_count >= limit.requests_per_minute:
                return False, {
                    "allowed": False,
                    "current_count": current_count,
                    "limit": limit.requests_per_minute,
                    "reset_time": window_start + 60,
                    "retry_after": int(window_start + 60 - now)
                }
            
            # Increment count
            window_data['count'] = current_count + 1
            
            return True, {
                "allowed": True,
                "current_count": current_count + 1,
                "limit": limit.requests_per_minute,
                "remaining": limit.requests_per_minute - current_count - 1
            }
    
    async def reset_limit(self, key: str) -> bool:
        """Reset rate limit for a key"""
        async with self._lock:
            if key in self.windows:
                del self.windows[key]
        return True


class LeakyBucketRateLimiter(BaseRateLimiter):
    """Leaky bucket rate limiter"""
    
    def __init__(self):
        self.buckets: Dict[str, Dict] = defaultdict(dict)
        self._lock = asyncio.Lock()
    
    async def is_allowed(self, key: str, limit: RateLimit) -> Tuple[bool, Dict]:
        """Check if request is allowed using leaky bucket"""
        async with self._lock:
            now = time.time()
            bucket = self.buckets[key]
            
            # Initialize bucket if new
            if 'level' not in bucket:
                bucket['level'] = 0
                bucket['last_leak'] = now
            
            # Leak tokens
            time_passed = now - bucket['last_leak']
            leak_rate = limit.requests_per_minute / 60.0  # tokens per second
            leaked = time_passed * leak_rate
            bucket['level'] = max(0, bucket['level'] - leaked)
            bucket['last_leak'] = now
            
            # Check if bucket can accommodate new request
            if bucket['level'] >= limit.requests_per_minute:
                return False, {
                    "allowed": False,
                    "bucket_level": bucket['level'],
                    "capacity": limit.requests_per_minute,
                    "retry_after": int((bucket['level'] - limit.requests_per_minute + 1) / leak_rate)
                }
            
            # Add request to bucket
            bucket['level'] += 1
            
            return True, {
                "allowed": True,
                "bucket_level": bucket['level'],
                "capacity": limit.requests_per_minute,
                "remaining": int(limit.requests_per_minute - bucket['level'])
            }
    
    async def reset_limit(self, key: str) -> bool:
        """Reset rate limit for a key"""
        async with self._lock:
            if key in self.buckets:
                del self.buckets[key]
        return True


class RateLimiterManager:
    """Manages rate limiters with different strategies"""
    
    def __init__(self, strategy: RateLimitStrategy = RateLimitStrategy.SLIDING_WINDOW):
        self.strategy = strategy
        
        # Create appropriate limiter based on strategy
        if strategy == RateLimitStrategy.TOKEN_BUCKET:
            self.limiter = TokenBucketRateLimiter()
        elif strategy == RateLimitStrategy.SLIDING_WINDOW:
            self.limiter = MemoryRateLimiter()
        elif strategy == RateLimitStrategy.FIXED_WINDOW:
            self.limiter = FixedWindowRateLimiter()
        elif strategy == RateLimitStrategy.LEAKY_BUCKET:
            self.limiter = LeakyBucketRateLimiter()
        else:
            # Default to sliding window
            self.limiter = MemoryRateLimiter()
    
    async def check_rate_limit(self, provider: str, limit: RateLimit) -> Tuple[bool, Dict]:
        """Check rate limit for a provider"""
        return await self.limiter.is_allowed(provider, limit)
    
    async def reset_provider_limit(self, provider: str) -> bool:
        """Reset rate limit for a provider"""
        return await self.limiter.reset_limit(provider)
    
    async def close(self):
        """Close rate limiter resources (no-op for memory limiter)"""
        pass


# Global rate limiter instance
rate_limiter_manager = RateLimiterManager(RateLimitStrategy.SLIDING_WINDOW)