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
    """Comprehensive rate limit configuration"""
    # Request limits
    requests_per_minute: int
    requests_per_hour: Optional[int] = None
    requests_per_day: Optional[int] = None
    requests_per_month: Optional[int] = None
    
    # Token limits
    tokens_per_minute: Optional[int] = None
    tokens_per_hour: Optional[int] = None
    tokens_per_day: Optional[int] = None
    tokens_per_month: Optional[int] = None
    
    # Burst handling
    burst_limit: Optional[int] = None
    token_refill_rate: float = 1.0  # tokens per second
    
    # Tracking windows
    window_size: int = 60  # seconds
    
    def __post_init__(self):
        """Validate rate limit configuration"""
        if self.requests_per_minute <= 0:
            raise ValueError("requests_per_minute must be positive")
        
        if self.burst_limit and self.burst_limit < self.requests_per_minute:
            self.burst_limit = self.requests_per_minute * 2  # Default burst to 2x normal rate


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


class EnhancedRateLimiter(BaseRateLimiter):
    """Enhanced rate limiter with multi-dimensional tracking (requests, tokens, daily/monthly limits)"""
    
    def __init__(self):
        self.request_windows: Dict[str, Dict[str, deque]] = defaultdict(lambda: defaultdict(deque))
        self.token_windows: Dict[str, Dict[str, deque]] = defaultdict(lambda: defaultdict(deque))
        self.daily_counters: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        self.monthly_counters: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        self.last_reset: Dict[str, Dict[str, float]] = defaultdict(lambda: defaultdict(float))
        self._lock = asyncio.Lock()
    
    async def is_allowed(self, key: str, limit: RateLimit) -> Tuple[bool, Dict]:
        """Check if request is allowed across all dimensions"""
        async with self._lock:
            now = time.time()
            
            # Check and update daily/monthly counters
            await self._update_periodic_counters(key, now)
            
            # Check all rate limits
            checks = []
            
            # 1. Requests per minute
            rpm_allowed, rpm_info = await self._check_requests_per_minute(key, limit, now)
            checks.append(("requests_per_minute", rpm_allowed, rpm_info))
            
            # 2. Requests per hour
            if limit.requests_per_hour:
                rph_allowed, rph_info = await self._check_requests_per_hour(key, limit, now)
                checks.append(("requests_per_hour", rph_allowed, rph_info))
            
            # 3. Requests per day
            if limit.requests_per_day:
                rpd_allowed, rpd_info = await self._check_requests_per_day(key, limit, now)
                checks.append(("requests_per_day", rpd_allowed, rpd_info))
            
            # 4. Requests per month
            if limit.requests_per_month:
                rpmth_allowed, rpmth_info = await self._check_requests_per_month(key, limit, now)
                checks.append(("requests_per_month", rpmth_allowed, rpmth_info))
            
            # 5. Tokens per minute
            if limit.tokens_per_minute:
                tpm_allowed, tpm_info = await self._check_tokens_per_minute(key, limit, now)
                checks.append(("tokens_per_minute", tpm_allowed, tpm_info))
            
            # 6. Tokens per hour
            if limit.tokens_per_hour:
                tph_allowed, tph_info = await self._check_tokens_per_hour(key, limit, now)
                checks.append(("tokens_per_hour", tph_allowed, tph_info))
            
            # 7. Tokens per day
            if limit.tokens_per_day:
                tpd_allowed, tpd_info = await self._check_tokens_per_day(key, limit, now)
                checks.append(("tokens_per_day", tpd_allowed, tpd_info))
            
            # 8. Tokens per month
            if limit.tokens_per_month:
                tpmth_allowed, tpmth_info = await self._check_tokens_per_month(key, limit, now)
                checks.append(("tokens_per_month", tpmth_allowed, tpmth_info))
            
            # Determine overall result
            failed_checks = [name for name, allowed, _ in checks if not allowed]
            
            if failed_checks:
                # Find the most restrictive limit that was hit
                failed_info = next(info for name, allowed, info in checks if not allowed)
                return False, {
                    "allowed": False,
                    "failed_checks": failed_checks,
                    "reason": f"Rate limit exceeded: {failed_checks[0]}",
                    **failed_info
                }
            
            # All checks passed, record the usage
            await self._record_usage(key, limit, now)
            
            return True, {
                "allowed": True,
                "rate_limit_status": {name: info for name, allowed, info in checks}
            }
    
    async def _update_periodic_counters(self, key: str, now: float):
        """Update daily and monthly counters, resetting as needed"""
        current_day = int(now // 86400)  # seconds per day
        current_month = time.gmtime(now).tm_year * 12 + time.gmtime(now).tm_mon
        
        # Reset daily counter if needed
        if self.last_reset[key].get("daily", 0) != current_day:
            self.daily_counters[key] = defaultdict(int)
            self.last_reset[key]["daily"] = current_day
        
        # Reset monthly counter if needed
        if self.last_reset[key].get("monthly", 0) != current_month:
            self.monthly_counters[key] = defaultdict(int)
            self.last_reset[key]["monthly"] = current_month
    
    async def _check_requests_per_minute(self, key: str, limit: RateLimit, now: float) -> Tuple[bool, Dict]:
        """Check requests per minute limit"""
        window = self.request_windows[key]["minute"]
        cutoff = now - 60
        
        # Remove expired entries
        while window and window[0]["timestamp"] < cutoff:
            window.popleft()
        
        current_count = len(window)
        
        if current_count >= limit.requests_per_minute:
            return False, {
                "current_count": current_count,
                "limit": limit.requests_per_minute,
                "reset_time": cutoff + 60,
                "retry_after": int(window[0]["timestamp"] + 60 - now) if window else 1
            }
        
        return True, {
            "current_count": current_count,
            "limit": limit.requests_per_minute,
            "remaining": limit.requests_per_minute - current_count
        }
    
    async def _check_requests_per_hour(self, key: str, limit: RateLimit, now: float) -> Tuple[bool, Dict]:
        """Check requests per hour limit"""
        window = self.request_windows[key]["hour"]
        cutoff = now - 3600  # 1 hour
        
        # Remove expired entries
        while window and window[0]["timestamp"] < cutoff:
            window.popleft()
        
        current_count = len(window)
        
        if current_count >= limit.requests_per_hour:
            return False, {
                "current_count": current_count,
                "limit": limit.requests_per_hour,
                "reset_time": cutoff + 3600,
                "retry_after": int(window[0]["timestamp"] + 3600 - now) if window else 60
            }
        
        return True, {
            "current_count": current_count,
            "limit": limit.requests_per_hour,
            "remaining": limit.requests_per_hour - current_count
        }
    
    async def _check_requests_per_day(self, key: str, limit: RateLimit, now: float) -> Tuple[bool, Dict]:
        """Check requests per day limit"""
        current_count = self.daily_counters[key]["requests"]
        
        if current_count >= limit.requests_per_day:
            # Calculate time until next day
            next_day = (int(now // 86400) + 1) * 86400
            return False, {
                "current_count": current_count,
                "limit": limit.requests_per_day,
                "reset_time": next_day,
                "retry_after": int(next_day - now)
            }
        
        return True, {
            "current_count": current_count,
            "limit": limit.requests_per_day,
            "remaining": limit.requests_per_day - current_count
        }
    
    async def _check_requests_per_month(self, key: str, limit: RateLimit, now: float) -> Tuple[bool, Dict]:
        """Check requests per month limit"""
        current_count = self.monthly_counters[key]["requests"]
        
        if current_count >= limit.requests_per_month:
            # Calculate time until next month
            next_month_time = time.mktime((time.gmtime(now).tm_year, time.gmtime(now).tm_mon + 1, 1, 0, 0, 0, 0, 0, 0))
            return False, {
                "current_count": current_count,
                "limit": limit.requests_per_month,
                "reset_time": next_month_time,
                "retry_after": int(next_month_time - now)
            }
        
        return True, {
            "current_count": current_count,
            "limit": limit.requests_per_month,
            "remaining": limit.requests_per_month - current_count
        }
    
    async def _check_tokens_per_minute(self, key: str, limit: RateLimit, now: float, tokens_used: int = 0) -> Tuple[bool, Dict]:
        """Check tokens per minute limit"""
        window = self.token_windows[key]["minute"]
        cutoff = now - 60
        
        # Remove expired entries and sum tokens
        while window and window[0]["timestamp"] < cutoff:
            window.popleft()
        
        current_tokens = sum(entry["tokens"] for entry in window)
        
        if current_tokens + tokens_used > limit.tokens_per_minute:
            return False, {
                "current_tokens": current_tokens,
                "limit": limit.tokens_per_minute,
                "reset_time": cutoff + 60,
                "retry_after": int(window[0]["timestamp"] + 60 - now) if window else 1
            }
        
        return True, {
            "current_tokens": current_tokens,
            "limit": limit.tokens_per_minute,
            "remaining": limit.tokens_per_minute - current_tokens
        }
    
    async def _check_tokens_per_hour(self, key: str, limit: RateLimit, now: float, tokens_used: int = 0) -> Tuple[bool, Dict]:
        """Check tokens per hour limit"""
        window = self.token_windows[key]["hour"]
        cutoff = now - 3600
        
        # Remove expired entries and sum tokens
        while window and window[0]["timestamp"] < cutoff:
            window.popleft()
        
        current_tokens = sum(entry["tokens"] for entry in window)
        
        if current_tokens + tokens_used > limit.tokens_per_hour:
            return False, {
                "current_tokens": current_tokens,
                "limit": limit.tokens_per_hour,
                "reset_time": cutoff + 3600,
                "retry_after": int(window[0]["timestamp"] + 3600 - now) if window else 60
            }
        
        return True, {
            "current_tokens": current_tokens,
            "limit": limit.tokens_per_hour,
            "remaining": limit.tokens_per_hour - current_tokens
        }
    
    async def _check_tokens_per_day(self, key: str, limit: RateLimit, now: float, tokens_used: int = 0) -> Tuple[bool, Dict]:
        """Check tokens per day limit"""
        current_tokens = self.daily_counters[key]["tokens"]
        
        if current_tokens + tokens_used > limit.tokens_per_day:
            next_day = (int(now // 86400) + 1) * 86400
            return False, {
                "current_tokens": current_tokens,
                "limit": limit.tokens_per_day,
                "reset_time": next_day,
                "retry_after": int(next_day - now)
            }
        
        return True, {
            "current_tokens": current_tokens,
            "limit": limit.tokens_per_day,
            "remaining": limit.tokens_per_day - current_tokens
        }
    
    async def _check_tokens_per_month(self, key: str, limit: RateLimit, now: float, tokens_used: int = 0) -> Tuple[bool, Dict]:
        """Check tokens per month limit"""
        current_tokens = self.monthly_counters[key]["tokens"]
        
        if current_tokens + tokens_used > limit.tokens_per_month:
            next_month_time = time.mktime((time.gmtime(now).tm_year, time.gmtime(now).tm_mon + 1, 1, 0, 0, 0, 0, 0, 0))
            return False, {
                "current_tokens": current_tokens,
                "limit": limit.tokens_per_month,
                "reset_time": next_month_time,
                "retry_after": int(next_month_time - now)
            }
        
        return True, {
            "current_tokens": current_tokens,
            "limit": limit.tokens_per_month,
            "remaining": limit.tokens_per_month - current_tokens
        }
    
    async def _record_usage(self, key: str, limit: RateLimit, now: float, tokens_used: int = 0):
        """Record successful request usage"""
        request_entry = {"timestamp": now, "tokens": tokens_used}
        
        # Record in time windows
        self.request_windows[key]["minute"].append(request_entry)
        self.request_windows[key]["hour"].append(request_entry)
        
        if tokens_used > 0:
            token_entry = {"timestamp": now, "tokens": tokens_used}
            self.token_windows[key]["minute"].append(token_entry)
            self.token_windows[key]["hour"].append(token_entry)
        
        # Update daily and monthly counters
        self.daily_counters[key]["requests"] += 1
        self.daily_counters[key]["tokens"] += tokens_used
        self.monthly_counters[key]["requests"] += 1
        self.monthly_counters[key]["tokens"] += tokens_used
    
    async def record_token_usage(self, key: str, tokens_used: int):
        """Record token usage after request completion"""
        async with self._lock:
            now = time.time()
            
            # Update token windows
            token_entry = {"timestamp": now, "tokens": tokens_used}
            self.token_windows[key]["minute"].append(token_entry)
            self.token_windows[key]["hour"].append(token_entry)
            
            # Update daily and monthly counters
            self.daily_counters[key]["tokens"] += tokens_used
            self.monthly_counters[key]["tokens"] += tokens_used
    
    async def get_rate_limit_status(self, key: str, limit: RateLimit) -> Dict:
        """Get current rate limit status without checking limits"""
        async with self._lock:
            now = time.time()
            await self._update_periodic_counters(key, now)
            
            status = {}
            
            # Requests per minute
            rpm_window = self.request_windows[key]["minute"]
            cutoff = now - 60
            while rpm_window and rpm_window[0]["timestamp"] < cutoff:
                rpm_window.popleft()
            
            status["requests_per_minute"] = {
                "current": len(rpm_window),
                "limit": limit.requests_per_minute,
                "remaining": limit.requests_per_minute - len(rpm_window)
            }
            
            # Requests per day
            if limit.requests_per_day:
                daily_requests = self.daily_counters[key]["requests"]
                status["requests_per_day"] = {
                    "current": daily_requests,
                    "limit": limit.requests_per_day,
                    "remaining": limit.requests_per_day - daily_requests
                }
            
            # Tokens per minute
            if limit.tokens_per_minute:
                tpm_window = self.token_windows[key]["minute"]
                cutoff = now - 60
                while tpm_window and tpm_window[0]["timestamp"] < cutoff:
                    tpm_window.popleft()
                
                current_tokens = sum(entry["tokens"] for entry in tpm_window)
                status["tokens_per_minute"] = {
                    "current": current_tokens,
                    "limit": limit.tokens_per_minute,
                    "remaining": limit.tokens_per_minute - current_tokens
                }
            
            return status
    
    async def reset_limit(self, key: str) -> bool:
        """Reset all rate limits for a key"""
        async with self._lock:
            if key in self.request_windows:
                del self.request_windows[key]
            if key in self.token_windows:
                del self.token_windows[key]
            if key in self.daily_counters:
                del self.daily_counters[key]
            if key in self.monthly_counters:
                del self.monthly_counters[key]
            if key in self.last_reset:
                del self.last_reset[key]
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
            self.limiter = EnhancedRateLimiter()  # Use enhanced rate limiter
        elif strategy == RateLimitStrategy.FIXED_WINDOW:
            self.limiter = FixedWindowRateLimiter()
        elif strategy == RateLimitStrategy.LEAKY_BUCKET:
            self.limiter = LeakyBucketRateLimiter()
        else:
            # Default to enhanced sliding window
            self.limiter = EnhancedRateLimiter()
    
    async def check_rate_limit(self, provider: str, limit: RateLimit) -> Tuple[bool, Dict]:
        """Check rate limit for a provider"""
        return await self.limiter.is_allowed(provider, limit)
    
    async def record_token_usage(self, provider: str, tokens_used: int):
        """Record token usage after request completion"""
        if hasattr(self.limiter, 'record_token_usage'):
            await self.limiter.record_token_usage(provider, tokens_used)
    
    async def get_rate_limit_status(self, provider: str, limit: RateLimit) -> Dict:
        """Get current rate limit status"""
        if hasattr(self.limiter, 'get_rate_limit_status'):
            return await self.limiter.get_rate_limit_status(provider, limit)
        return {}
    
    async def reset_provider_limit(self, provider: str) -> bool:
        """Reset rate limit for a provider"""
        return await self.limiter.reset_limit(provider)
    
    async def close(self):
        """Close rate limiter resources"""
        if hasattr(self.limiter, 'close'):
            await self.limiter.close()


# Global rate limiter instance
rate_limiter_manager = RateLimiterManager(RateLimitStrategy.SLIDING_WINDOW)