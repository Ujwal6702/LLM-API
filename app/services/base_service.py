"""
Base service class for business logic
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class BaseService(ABC):
    """
    Abstract base service class
    """
    
    def __init__(self):
        self.name = self.__class__.__name__
    
    @abstractmethod
    async def execute(self, *args, **kwargs) -> Any:
        """
        Execute the service logic
        """
        pass
    
    def _validate_input(self, data: Dict[str, Any]) -> bool:
        """
        Validate input data (to be overridden in child classes)
        """
        return True
    
    def _format_output(self, data: Any) -> Any:
        """
        Format output data (to be overridden in child classes)
        """
        return data
