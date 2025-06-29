"""
Base controller class for handling HTTP requests
"""
from fastapi import HTTPException
from typing import Any, Dict
from app.views.response_formatter import ResponseFormatter


class BaseController:
    """
    Base controller class with common functionality
    """
    
    def __init__(self):
        self.response_formatter = ResponseFormatter()
    
    def handle_success(self, data: Any = None, message: str = "Success") -> Dict[str, Any]:
        """
        Handle successful responses
        """
        return self.response_formatter.success_response(data, message)
    
    def handle_error(
        self,
        message: str,
        status_code: int = 400,
        error_code: str = None
    ) -> HTTPException:
        """
        Handle error responses
        """
        return HTTPException(
            status_code=status_code,
            detail=self.response_formatter.error_response(
                message=message,
                error_code=error_code,
                status_code=status_code
            )
        )
    
    def validate_request(self, data: Dict[str, Any], required_fields: list) -> bool:
        """
        Validate request data
        """
        for field in required_fields:
            if field not in data or data[field] is None:
                return False
        return True
