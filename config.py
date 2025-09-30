"""
Configuration module for the Coding AI Assistant
"""

import os
from typing import Optional, List
from pydantic_settings import BaseSettings
from pydantic import Field, validator

class Settings(BaseSettings):
    """Application settings with validation"""
    
    # MongoDB Configuration
    mongo_uri: str = Field(
        default="mongodb://localhost:27017/",
        env="MONGO_URI",
        description="MongoDB connection URI"
    )
    
    # Model Configuration
    model_path: str = Field(
        default="./models/phi-3.1-mini-4k-instruct.gguf",
        env="MODEL_PATH",
        description="Path to the language model file"
    )
    
    model_url: str = Field(
        default="https://huggingface.co/TheBloke/Phi-3-mini-4k-instruct-GGUF/resolve/main/phi-3-mini-4k-instruct.Q4_K_M.gguf",
        env="MODEL_URL",
        description="URL to download the model from"
    )
    
    # Security Configuration
    secret_key: str = Field(
        default="change-this-secret-key-in-production",
        env="SECRET_KEY",
        description="Secret key for JWT encoding"
    )
    
    algorithm: str = Field(
        default="HS256",
        description="JWT encoding algorithm"
    )
    
    access_token_expire_minutes: int = Field(
        default=30,
        description="Access token expiration time in minutes"
    )
    
    # Server Configuration
    port: int = Field(
        env="PORT",
        description="Server port"
    )
    
    host: str = Field(
        default="0.0.0.0",
        description="Server host"
    )
    
    # CORS Configuration
    cors_origins: List[str] = Field(
        default=["*"],
        env="CORS_ORIGINS",
        description="Allowed CORS origins"
    )
    
    # Rate Limiting
    rate_limit_chat: str = Field(
        default="30/minute",
        description="Rate limit for chat endpoint"
    )
    
    rate_limit_history: str = Field(
        default="10/minute",
        description="Rate limit for history endpoint"
    )
    
    rate_limit_save: str = Field(
        default="20/minute",
        description="Rate limit for save endpoint"
    )
    
    rate_limit_suggest: str = Field(
        default="10/minute",
        description="Rate limit for suggest endpoint"
    )
    
    # Logging Configuration
    log_level: str = Field(
        default="INFO",
        env="LOG_LEVEL",
        description="Logging level"
    )
    
    log_file: str = Field(
        default="app.log",
        description="Log file path"
    )
    
    # Model Parameters
    model_context_size: int = Field(
        default=4096,
        description="Model context window size"
    )
    
    model_max_tokens: int = Field(
        default=512,
        description="Maximum tokens for model generation"
    )
    
    model_temperature: float = Field(
        default=0.7,
        description="Model temperature for generation"
    )
    
    model_top_p: float = Field(
        default=0.95,
        description="Model top-p for generation"
    )
    
    model_threads: int = Field(
        default=2,
        description="Number of threads for model inference"
    )
    
    # Application Configuration
    app_name: str = Field(
        default="Coding AI Assistant",
        description="Application name"
    )
    
    app_version: str = Field(
        default="1.0.0",
        description="Application version"
    )
    
    app_description: str = Field(
        default="AI-powered coding assistant with adaptive learning",
        description="Application description"
    )
    
    # Database Configuration
    db_name: str = Field(
        default="coding_assistant",
        description="Database name"
    )
    
    db_timeout_ms: int = Field(
        default=5000,
        description="Database connection timeout in milliseconds"
    )
    
    # Feature Flags
    enable_auth: bool = Field(
        default=True,
        env="ENABLE_AUTH",
        description="Enable authentication features"
    )
    
    enable_rate_limiting: bool = Field(
        default=True,
        env="ENABLE_RATE_LIMITING",
        description="Enable rate limiting"
    )
    
    enable_model_download: bool = Field(
        default=True,
        env="ENABLE_MODEL_DOWNLOAD",
        description="Enable automatic model download"
    )
    
    enable_mock_responses: bool = Field(
        default=True,
        env="ENABLE_MOCK_RESPONSES",
        description="Enable mock responses when model is unavailable"
    )
    
    @validator("cors_origins", pre=True)
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v
    
    @validator("secret_key")
    def validate_secret_key(cls, v):
        if v == "change-this-secret-key-in-production":
            import warnings
            warnings.warn(
                "Using default secret key. Please change it in production!",
                RuntimeWarning
            )
        return v
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

# Create global settings instance
settings = Settings()