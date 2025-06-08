import os
from functools import lru_cache
from pathlib import Path
from typing import Optional, Dict, Any
from pydantic import Field, validator
from pydantic_settings import BaseSettings
import logger


# Create a centralized logger instance
_app_logger = None

def get_logger():
    """Get the centralized logger instance."""
    global _app_logger
    if _app_logger is None:
        _app_logger = logger.Logger("LLM-API")
    return _app_logger


class BaseConfig:
    """Base configuration class with common utilities."""
    
    def __init__(self):
        self.logger = get_logger()
        self._project_root = Path(__file__).parent.absolute()
        
    @property
    def app_logger(self):
        """Get the centralized application logger."""
        return get_logger()
    
    @property
    def project_root(self) -> Path:
        """Get the current project root directory."""
        return self._project_root
    
    @property
    def project_root_str(self) -> str:
        """Get the current project root directory as string."""
        return str(self._project_root)
    
    def log_config_loaded(self, config_name: str) -> None:
        """Log configuration loading."""
        self.logger.info(f"{config_name} configuration loaded from: {self.project_root_str}")


class Settings(BaseSettings, BaseConfig):
    """Application settings with environment variable support."""
    
    # Application Settings
    app_name: str = Field(default="LLM-API", env="APP_NAME")
    debug: bool = Field(default=False, env="DEBUG")
    secret_key: str = Field(..., env="SECRET_KEY")
    host: str = Field(default="0.0.0.0", env="HOST")
    port: int = Field(default=8000, env="PORT")
    
    # API Configuration
    api_version: str = Field(default="v1", env="API_VERSION")
    api_prefix: str = Field(default="/api", env="API_PREFIX")
    
    # Security Settings
    cors_origins: str = Field(default="*", env="CORS_ORIGINS")
    allowed_hosts: str = Field(default="*", env="ALLOWED_HOSTS")
    
    # Logging Configuration
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        env="LOG_FORMAT"
    )
    
    # Environment
    environment: str = Field(default="development", env="ENVIRONMENT")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        BaseConfig.__init__(self)
        
    @validator('environment')
    def validate_environment(cls, v):
        allowed_envs = ['development', 'staging', 'production', 'testing']
        if v.lower() not in allowed_envs:
            raise ValueError(f'Environment must be one of: {", ".join(allowed_envs)}')
        return v.lower()
    
    @validator('log_level')
    def validate_log_level(cls, v):
        allowed_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if v.upper() not in allowed_levels:
            raise ValueError(f'Log level must be one of: {", ".join(allowed_levels)}')
        return v.upper()
    
    @property
    def cors_origins_list(self) -> list:
        """Convert CORS origins string to list."""
        if self.cors_origins == "*":
            return ["*"]
        return [origin.strip() for origin in self.cors_origins.split(",")]
    
    @property
    def allowed_hosts_list(self) -> list:
        """Convert allowed hosts string to list."""
        if self.allowed_hosts == "*":
            return ["*"]
        return [host.strip() for host in self.allowed_hosts.split(",")]
    
    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.environment == "development"
    
    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment == "production"
    
    @property
    def api_base_url(self) -> str:
        """Get the complete API base URL."""
        return f"{self.api_prefix}/{self.api_version}"
    
    def log_startup_info(self) -> None:
        """Log application startup information."""
        self.log_config_loaded("Application")
        self.logger.info(f"App Name: {self.app_name}")
        self.logger.info(f"Environment: {self.environment}")
        self.logger.info(f"Debug Mode: {self.debug}")
        self.logger.info(f"Host: {self.host}:{self.port}")
        self.logger.info(f"API Base URL: {self.api_base_url}")
        self.logger.info(f"Project Root: {self.project_root_str}")


class DevelopmentSettings(Settings):
    """Development environment specific settings."""
    
    debug: bool = Field(default=True, env="DEBUG")
    log_level: str = Field(default="DEBUG", env="LOG_LEVEL")
    environment: str = Field(default="development", env="ENVIRONMENT")
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.logger.debug("Development settings initialized")


class ProductionSettings(Settings):
    """Production environment specific settings."""
    
    debug: bool = Field(default=False, env="DEBUG")
    log_level: str = Field(default="WARNING", env="LOG_LEVEL")
    environment: str = Field(default="production", env="ENVIRONMENT")
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.logger.info("Production settings initialized")


class ConfigFactory:
    """Factory class for creating configuration objects."""
    
    @staticmethod
    def create_settings(environment: Optional[str] = None) -> Settings:
        """Create settings based on environment."""
        env = environment or os.getenv("ENVIRONMENT", "development").lower()
        
        if env == "production":
            return ProductionSettings()
        elif env == "development":
            return DevelopmentSettings()
        else:
            return Settings(environment=env)


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    settings = ConfigFactory.create_settings()
    settings.log_startup_info()
    return settings


# Convenience function to get current directory
def get_project_root() -> str:
    """Get the current project root directory path."""
    return str(Path(__file__).parent.absolute())


# Export commonly used objects
__all__ = [
    "Settings",
    "DevelopmentSettings", 
    "ProductionSettings",
    "ConfigFactory",
    "get_settings",
    "get_project_root",
    "get_logger"
]
