"""Configuration management for USASpending MCP Server."""

import os
from typing import Literal


class ServerConfig:
    """Server configuration settings."""

    # Server settings
    MCP_PORT: int = int(os.getenv("MCP_PORT", "3002"))
    HTTP_HOST: str = os.getenv("HTTP_HOST", "127.0.0.1")
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = os.getenv(
        "LOG_LEVEL", "INFO"
    )

    # API settings
    HTTP_TIMEOUT: float = float(os.getenv("HTTP_TIMEOUT", "30.0"))
    API_BASE_URL: str = os.getenv(
        "API_BASE_URL", "https://api.usaspending.gov/api/v2"
    )

    # Rate limiting
    REQUESTS_PER_MINUTE: int = int(os.getenv("REQUESTS_PER_MINUTE", "60"))

    # FAR settings
    FAR_DATA_PATH: str = os.getenv("FAR_DATA_PATH", "docs/data/far")

    @classmethod
    def validate_required(cls) -> None:
        """Validate that all required configuration is present."""
        required_config = {
            "API_BASE_URL": cls.API_BASE_URL,
            "MCP_PORT": cls.MCP_PORT,
            "HTTP_TIMEOUT": cls.HTTP_TIMEOUT,
        }

        for config_name, config_value in required_config.items():
            if config_value is None or config_value == "":
                raise ValueError(f"Required configuration '{config_name}' is missing")

        if cls.HTTP_TIMEOUT <= 0:
            raise ValueError("HTTP_TIMEOUT must be greater than 0")

        if cls.MCP_PORT <= 0 or cls.MCP_PORT > 65535:
            raise ValueError("MCP_PORT must be between 1 and 65535")

        if cls.REQUESTS_PER_MINUTE <= 0:
            raise ValueError("REQUESTS_PER_MINUTE must be greater than 0")

    @classmethod
    def to_dict(cls) -> dict:
        """Convert configuration to dictionary."""
        return {
            "MCP_PORT": cls.MCP_PORT,
            "HTTP_HOST": cls.HTTP_HOST,
            "LOG_LEVEL": cls.LOG_LEVEL,
            "HTTP_TIMEOUT": cls.HTTP_TIMEOUT,
            "API_BASE_URL": cls.API_BASE_URL,
            "REQUESTS_PER_MINUTE": cls.REQUESTS_PER_MINUTE,
            "FAR_DATA_PATH": cls.FAR_DATA_PATH,
        }
