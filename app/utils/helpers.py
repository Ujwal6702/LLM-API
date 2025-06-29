"""
Common utility functions
"""
import re
import hashlib
from typing import Any, Dict, List
from datetime import datetime, timezone


def sanitize_string(text: str) -> str:
    """
    Sanitize a string by removing special characters
    """
    return re.sub(r'[^\w\s-]', '', text).strip()


def generate_hash(data: str) -> str:
    """
    Generate SHA256 hash of a string
    """
    return hashlib.sha256(data.encode()).hexdigest()


def get_current_timestamp() -> str:
    """
    Get current timestamp in ISO format
    """
    return datetime.now(timezone.utc).isoformat()


def validate_email(email: str) -> bool:
    """
    Validate email format
    """
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def truncate_text(text: str, max_length: int = 100) -> str:
    """
    Truncate text to specified length
    """
    if len(text) <= max_length:
        return text
    return text[:max_length-3] + "..."


def deep_merge_dicts(dict1: Dict[str, Any], dict2: Dict[str, Any]) -> Dict[str, Any]:
    """
    Deep merge two dictionaries
    """
    result = dict1.copy()
    
    for key, value in dict2.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge_dicts(result[key], value)
        else:
            result[key] = value
    
    return result


def flatten_list(nested_list: List[Any]) -> List[Any]:
    """
    Flatten a nested list
    """
    flattened = []
    for item in nested_list:
        if isinstance(item, list):
            flattened.extend(flatten_list(item))
        else:
            flattened.append(item)
    return flattened
