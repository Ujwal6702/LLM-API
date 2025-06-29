"""
Response formatters and view utilities
"""
from typing import Any, Dict, Optional
from datetime import datetime
from app.models.base_models import BaseResponse, ErrorResponse


class ResponseFormatter:
    """
    Utility class for formatting API responses
    """
    
    @staticmethod
    def success_response(
        data: Any = None,
        message: str = "Success",
        status_code: int = 200
    ) -> Dict[str, Any]:
        """
        Format a successful response
        """
        response = {
            "success": True,
            "message": message,
            "timestamp": datetime.now().isoformat(),
            "status_code": status_code
        }
        
        if data is not None:
            response["data"] = data
        
        return response
    
    @staticmethod
    def error_response(
        message: str,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        status_code: int = 400
    ) -> Dict[str, Any]:
        """
        Format an error response
        """
        response = {
            "success": False,
            "message": message,
            "timestamp": datetime.now().isoformat(),
            "status_code": status_code
        }
        
        if error_code:
            response["error_code"] = error_code
        
        if details:
            response["details"] = details
        
        return response
    
    @staticmethod
    def paginated_response(
        data: list,
        page: int,
        page_size: int,
        total: int,
        message: str = "Success"
    ) -> Dict[str, Any]:
        """
        Format a paginated response
        """
        return {
            "success": True,
            "message": message,
            "timestamp": datetime.now().isoformat(),
            "data": data,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total": total,
                "total_pages": (total + page_size - 1) // page_size
            }
        }
