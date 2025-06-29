"""
Rate Limit Monitoring and Analytics

This module provides comprehensive rate limit monitoring, analytics, and forecasting
to help users understand their API usage patterns and avoid hitting limits.
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import time

from app.utils.rate_limiter import rate_limiter_manager
from app.config.settings import settings


class RateLimitMonitor:
    """Advanced rate limit monitoring and analytics"""
    
    def __init__(self):
        self.usage_history: Dict[str, List[Dict]] = {}
        self.alerts: List[Dict] = []
    
    async def get_comprehensive_status(self, provider: Optional[str] = None) -> Dict[str, Any]:
        """Get comprehensive rate limit status with analytics"""
        try:
            if provider:
                return await self._get_provider_analytics(provider)
            else:
                return await self._get_all_providers_analytics()
        except Exception as e:
            return {"error": str(e)}
    
    async def _get_provider_analytics(self, provider: str) -> Dict[str, Any]:
        """Get detailed analytics for a specific provider"""
        # Get current configuration
        provider_config = settings.LLM_PROVIDERS.get(provider, {})
        rate_limits_config = provider_config.get("rate_limits", {})
        
        analytics = {
            "provider": provider,
            "timestamp": datetime.now().isoformat(),
            "configuration": rate_limits_config,
            "current_usage": {},
            "predictions": {},
            "recommendations": []
        }
        
        # Analyze each model/limit combination
        for model_key, limits in rate_limits_config.items():
            model_analytics = await self._analyze_model_usage(provider, model_key, limits)
            analytics["current_usage"][model_key] = model_analytics
            
            # Generate predictions
            predictions = self._predict_usage(provider, model_key, model_analytics)
            analytics["predictions"][model_key] = predictions
            
            # Generate recommendations
            recommendations = self._generate_recommendations(model_analytics, predictions)
            if recommendations:
                analytics["recommendations"].extend(recommendations)
        
        return analytics
    
    async def _get_all_providers_analytics(self) -> Dict[str, Any]:
        """Get analytics for all providers"""
        all_analytics = {
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total_providers": len(settings.LLM_PROVIDERS),
                "active_providers": 0,
                "rate_limited_providers": 0,
                "healthy_providers": 0
            },
            "providers": {},
            "global_recommendations": []
        }
        
        for provider_name in settings.LLM_PROVIDERS.keys():
            provider_analytics = await self._get_provider_analytics(provider_name)
            all_analytics["providers"][provider_name] = provider_analytics
            
            # Update summary
            if provider_analytics.get("current_usage"):
                all_analytics["summary"]["active_providers"] += 1
                
                # Check if any model is rate limited
                is_rate_limited = any(
                    usage.get("warnings", [])
                    for usage in provider_analytics["current_usage"].values()
                )
                
                if is_rate_limited:
                    all_analytics["summary"]["rate_limited_providers"] += 1
                else:
                    all_analytics["summary"]["healthy_providers"] += 1
        
        # Generate global recommendations
        all_analytics["global_recommendations"] = self._generate_global_recommendations(
            all_analytics["providers"]
        )
        
        return all_analytics
    
    async def _analyze_model_usage(self, provider: str, model: str, limits: Dict) -> Dict[str, Any]:
        """Analyze current usage for a specific model"""
        usage_key = f"{provider}:{model}"
        
        analysis = {
            "model": model,
            "configured_limits": limits,
            "current_usage": {},
            "utilization_percentage": {},
            "warnings": [],
            "status": "healthy"
        }
        
        # Analyze each type of limit
        limit_types = [
            ("requests_per_minute", "Request Rate"),
            ("requests_per_hour", "Hourly Requests"),
            ("requests_per_day", "Daily Requests"),
            ("requests_per_month", "Monthly Requests"),
            ("tokens_per_minute", "Token Rate"),
            ("tokens_per_hour", "Hourly Tokens"),
            ("tokens_per_day", "Daily Tokens"),
            ("tokens_per_month", "Monthly Tokens")
        ]
        
        for limit_key, limit_name in limit_types:
            if limit_key in limits:
                current = await self._get_current_usage(usage_key, limit_key)
                limit_value = limits[limit_key]
                utilization = (current / limit_value) * 100 if limit_value > 0 else 0
                
                analysis["current_usage"][limit_key] = {
                    "current": current,
                    "limit": limit_value,
                    "remaining": max(0, limit_value - current)
                }
                
                analysis["utilization_percentage"][limit_key] = utilization
                
                # Generate warnings based on utilization
                if utilization >= 90:
                    analysis["warnings"].append({
                        "type": "critical",
                        "limit_type": limit_name,
                        "message": f"{limit_name} usage at {utilization:.1f}% - imminent rate limit",
                        "utilization": utilization
                    })
                    analysis["status"] = "critical"
                elif utilization >= 75:
                    analysis["warnings"].append({
                        "type": "warning",
                        "limit_type": limit_name,
                        "message": f"{limit_name} usage at {utilization:.1f}% - approaching limit",
                        "utilization": utilization
                    })
                    if analysis["status"] == "healthy":
                        analysis["status"] = "warning"
                elif utilization >= 50:
                    analysis["warnings"].append({
                        "type": "info",
                        "limit_type": limit_name,
                        "message": f"{limit_name} usage at {utilization:.1f}% - moderate usage",
                        "utilization": utilization
                    })
        
        return analysis
    
    async def _get_current_usage(self, usage_key: str, limit_type: str) -> int:
        """Get current usage for a specific limit type"""
        # This would interface with the rate limiter to get actual usage
        # For now, return mock data
        return 0
    
    def _predict_usage(self, provider: str, model: str, current_analytics: Dict) -> Dict[str, Any]:
        """Predict future usage based on current trends"""
        predictions = {
            "next_hour": {},
            "next_day": {},
            "time_to_limit": {},
            "confidence": "low"  # low/medium/high
        }
        
        # Generate predictions for each limit type
        for limit_key, usage_data in current_analytics["current_usage"].items():
            current = usage_data["current"]
            limit_value = usage_data["limit"]
            
            # Simple linear prediction (in real implementation, use more sophisticated models)
            if current > 0:
                # Predict next hour usage (assuming current rate continues)
                hourly_rate = current  # Simplified
                predictions["next_hour"][limit_key] = min(hourly_rate * 2, limit_value)
                
                # Predict next day usage
                daily_rate = current * 24  # Simplified
                predictions["next_day"][limit_key] = min(daily_rate, limit_value)
                
                # Calculate time to limit
                if hourly_rate > 0:
                    remaining = limit_value - current
                    hours_to_limit = remaining / hourly_rate
                    predictions["time_to_limit"][limit_key] = {
                        "hours": hours_to_limit,
                        "timestamp": (datetime.now() + timedelta(hours=hours_to_limit)).isoformat()
                    }
        
        return predictions
    
    def _generate_recommendations(self, analytics: Dict, predictions: Dict) -> List[Dict]:
        """Generate optimization recommendations"""
        recommendations = []
        
        # Check for high utilization
        for limit_key, utilization in analytics["utilization_percentage"].items():
            if utilization >= 80:
                recommendations.append({
                    "type": "optimization",
                    "priority": "high" if utilization >= 90 else "medium",
                    "title": f"High {limit_key.replace('_', ' ').title()} Usage",
                    "description": f"Consider implementing request batching or using multiple providers",
                    "action": "distribute_load"
                })
        
        # Check for imbalanced usage
        token_utilization = analytics["utilization_percentage"].get("tokens_per_minute", 0)
        request_utilization = analytics["utilization_percentage"].get("requests_per_minute", 0)
        
        if token_utilization > request_utilization + 20:
            recommendations.append({
                "type": "efficiency",
                "priority": "medium",
                "title": "High Token-to-Request Ratio",
                "description": "Consider reducing prompt size or using more efficient prompting",
                "action": "optimize_prompts"
            })
        
        return recommendations
    
    def _generate_global_recommendations(self, providers_analytics: Dict) -> List[Dict]:
        """Generate system-wide recommendations"""
        recommendations = []
        
        # Count rate-limited providers
        rate_limited_count = sum(
            1 for provider_data in providers_analytics.values()
            if any(
                usage.get("status") in ["warning", "critical"]
                for usage in provider_data.get("current_usage", {}).values()
            )
        )
        
        if rate_limited_count > 1:
            recommendations.append({
                "type": "system",
                "priority": "high",
                "title": "Multiple Providers Under Pressure",
                "description": f"{rate_limited_count} providers experiencing high usage",
                "action": "implement_load_balancing"
            })
        
        return recommendations


# Global monitor instance
rate_limit_monitor = RateLimitMonitor()
