"""
Configuration management for USASpending MCP Server.

This module handles all the settings and configurations needed to run the server.
Instead of having settings scattered throughout the code, we keep them all here in one place.
This makes it easier to change settings later without searching through the entire codebase.

Think of this like a control panel for your application:
- Server Settings: Where and how the server runs
- API Settings: Connection details for the USASpending.gov API
- Rate Limiting: Controls how many requests we make per minute
- FAR Settings: Where to find Federal Acquisition Regulation data

All settings can be customized using environment variables, which is great for
deploying the same code to different environments (testing, production, etc.)
"""

import os
from typing import Literal


class ServerConfig:
    """
    Server configuration settings class.

    This class stores all the settings the server needs to run.
    Instead of creating instances, we use @classmethod to access settings directly.
    This is like having a single "settings book" that everyone reads from.

    Usage:
        port = ServerConfig.MCP_PORT  # Access port setting
        ServerConfig.validate_required()  # Check all settings are valid
    """

    # ============ SERVER SETTINGS ============
    # These settings control where and how the server runs

    # The port number where the server listens for connections
    # Port numbers must be between 1 and 65535
    # Default is 3002, but can be changed with MCP_PORT environment variable
    MCP_PORT: int = int(os.getenv("MCP_PORT", "3002"))

    # The host address where the server binds
    # "127.0.0.1" means only local machine can connect
    # "0.0.0.0" means anyone can connect (used in Docker)
    HTTP_HOST: str = os.getenv("HTTP_HOST", "127.0.0.1")

    # How much detail we want in log messages
    # DEBUG: Very detailed, for developers debugging problems
    # INFO: Important events and status updates
    # WARNING: Something unexpected happened
    # ERROR: Something went wrong
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = os.getenv(
        "LOG_LEVEL", "DEBUG"
    )

    # ============ API SETTINGS ============
    # These settings control how we connect to the USASpending.gov API

    # How many seconds to wait before giving up on an API request
    # If the server takes longer than this, we stop waiting and report an error
    # Default is 30 seconds
    HTTP_TIMEOUT: float = float(os.getenv("HTTP_TIMEOUT", "30.0"))

    # The base URL for the USASpending.gov API
    # This is where we send all our requests to get federal spending data
    API_BASE_URL: str = os.getenv(
        "API_BASE_URL", "https://api.usaspending.gov/api/v2"
    )

    # ============ RATE LIMITING SETTINGS ============
    # These settings prevent us from overwhelming the API with too many requests

    # How many API requests we're allowed to make per minute
    # This protects the USASpending.gov servers from being overloaded
    # If we reach this limit, we wait a bit before making more requests
    REQUESTS_PER_MINUTE: int = int(os.getenv("REQUESTS_PER_MINUTE", "60"))

    # ============ FAR DATA SETTINGS ============
    # These settings control where we find Federal Acquisition Regulation data

    # The folder path where FAR JSON files are stored
    # FAR data is loaded once when the server starts
    FAR_DATA_PATH: str = os.getenv("FAR_DATA_PATH", "src/usaspending_mcp/data/far")

    @classmethod
    def validate_required(cls) -> None:
        """
        Validate that all required configuration is correct and valid.

        This is like a health check for our settings. Before the server starts,
        we make sure all required settings are present and make sense.
        If something is wrong (like port 99999), we stop and report an error
        so the user knows what to fix.

        Raises:
            ValueError: If any required configuration is missing or invalid
        """
        # Create a dictionary of required settings
        required_config = {
            "API_BASE_URL": cls.API_BASE_URL,
            "MCP_PORT": cls.MCP_PORT,
            "HTTP_TIMEOUT": cls.HTTP_TIMEOUT,
        }

        # Check that each required setting has a value
        for config_name, config_value in required_config.items():
            if config_value is None or config_value == "":
                raise ValueError(f"Required configuration '{config_name}' is missing")

        # Validate that timeout is a positive number
        # A timeout of 0 or negative doesn't make sense
        if cls.HTTP_TIMEOUT <= 0:
            raise ValueError("HTTP_TIMEOUT must be greater than 0")

        # Validate port number is in the valid range
        # Port numbers must be between 1 and 65535
        if cls.MCP_PORT <= 0 or cls.MCP_PORT > 65535:
            raise ValueError("MCP_PORT must be between 1 and 65535")

        # Validate rate limit is positive
        # We can't allow negative or zero requests per minute
        if cls.REQUESTS_PER_MINUTE <= 0:
            raise ValueError("REQUESTS_PER_MINUTE must be greater than 0")

    @classmethod
    def to_dict(cls) -> dict:
        """
        Convert all configuration settings to a dictionary.

        This is useful when we want to:
        - Display settings to the user
        - Log settings for debugging
        - Send settings to other parts of the application

        Returns:
            dict: A dictionary with all configuration settings
        """
        return {
            "MCP_PORT": cls.MCP_PORT,
            "HTTP_HOST": cls.HTTP_HOST,
            "LOG_LEVEL": cls.LOG_LEVEL,
            "HTTP_TIMEOUT": cls.HTTP_TIMEOUT,
            "API_BASE_URL": cls.API_BASE_URL,
            "REQUESTS_PER_MINUTE": cls.REQUESTS_PER_MINUTE,
            "FAR_DATA_PATH": cls.FAR_DATA_PATH,
        }
