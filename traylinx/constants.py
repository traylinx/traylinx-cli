"""
Traylinx CLI Constants and Configuration.

This module centralizes all URLs, endpoints, and global configuration.
Environment variables are loaded here and made available throughout the CLI.

Environment Variables:
    TRAYLINX_REGISTRY_URL: Agent Registry API base URL
    TRAYLINX_AGENT_KEY: Agent authentication key
    TRAYLINX_SECRET_TOKEN: Agent secret token from Sentinel
    TRAYLINX_ENV: Environment (dev, staging, prod)
"""

import os
from dataclasses import dataclass, field
from typing import Optional


# =============================================================================
# ENVIRONMENT NAMES
# =============================================================================

ENV_DEV = "dev"
ENV_STAGING = "staging"
ENV_PROD = "prod"


# =============================================================================
# API ENDPOINTS
# =============================================================================

@dataclass(frozen=True)
class Endpoints:
    """All API endpoints used by the CLI."""
    
    # A2A Catalog Endpoints (authenticated)
    CATALOG_PUBLISH: str = "/a2a/catalog/publish"
    CATALOG_UNPUBLISH: str = "/a2a/catalog/unpublish"
    CATALOG_VERSIONS: str = "/a2a/catalog/versions"
    
    # Public Catalog Endpoints (no auth)
    CATALOG_SEARCH: str = "/catalog/search"
    CATALOG_AGENT: str = "/catalog/agents/{agent_key}"
    
    # Registry Endpoints
    REGISTRY_REGISTER: str = "/a2a/registry/register"
    REGISTRY_HEARTBEAT: str = "/a2a/registry/heartbeat"
    REGISTRY_DISCOVER: str = "/a2a/registry/discover"
    
    # Health Endpoints
    HEALTH: str = "/health"
    READY: str = "/ready"


ENDPOINTS = Endpoints()


# =============================================================================
# DEFAULT URLS BY ENVIRONMENT
# =============================================================================

DEFAULT_URLS = {
    ENV_DEV: "http://localhost:8000",
    ENV_STAGING: "https://staging-api.traylinx.com",
    ENV_PROD: "https://api.traylinx.com",
}


# =============================================================================
# ENVIRONMENT VARIABLE NAMES
# =============================================================================

class EnvVars:
    """Environment variable names."""
    
    REGISTRY_URL = "TRAYLINX_REGISTRY_URL"
    AGENT_KEY = "TRAYLINX_AGENT_KEY"
    SECRET_TOKEN = "TRAYLINX_SECRET_TOKEN"
    ENV = "TRAYLINX_ENV"
    CONFIG_PATH = "TRAYLINX_CONFIG_PATH"
    DEBUG = "TRAYLINX_DEBUG"


# =============================================================================
# GLOBAL SETTINGS
# =============================================================================

@dataclass
class Settings:
    """
    Global CLI settings loaded from environment variables.
    
    Priority order:
    1. Environment variables
    2. Config file (~/.traylinx/config.yaml)
    3. Default values
    """
    
    # Environment
    env: str = field(default_factory=lambda: os.getenv(EnvVars.ENV, ENV_DEV))
    debug: bool = field(default_factory=lambda: os.getenv(EnvVars.DEBUG, "").lower() in ("1", "true"))
    
    # API Configuration
    registry_url: Optional[str] = field(default_factory=lambda: os.getenv(EnvVars.REGISTRY_URL))
    
    # Authentication
    agent_key: Optional[str] = field(default_factory=lambda: os.getenv(EnvVars.AGENT_KEY))
    secret_token: Optional[str] = field(default_factory=lambda: os.getenv(EnvVars.SECRET_TOKEN))
    
    # Paths
    config_path: Optional[str] = field(default_factory=lambda: os.getenv(EnvVars.CONFIG_PATH))
    
    @property
    def effective_registry_url(self) -> str:
        """Get registry URL with fallback to environment default."""
        return self.registry_url or DEFAULT_URLS.get(self.env, DEFAULT_URLS[ENV_DEV])
    
    @property
    def is_authenticated(self) -> bool:
        """Check if authentication credentials are available."""
        return bool(self.agent_key and self.secret_token)


def get_settings() -> Settings:
    """Get global settings singleton."""
    return Settings()


# =============================================================================
# API CONTENT TYPES
# =============================================================================

CONTENT_TYPE_A2A = "application/vnd.traylinx.a2a+json; version=1"
CONTENT_TYPE_JSON = "application/json"


# =============================================================================
# REQUEST TIMEOUTS
# =============================================================================

DEFAULT_TIMEOUT = 30.0  # seconds
PUBLISH_TIMEOUT = 60.0  # seconds (larger for file uploads)


# =============================================================================
# MANIFEST DEFAULTS
# =============================================================================

MANIFEST_FILENAME = "traylinx-agent.yaml"
MANIFEST_VERSION = "1.0"


# =============================================================================
# TEMPLATE NAMES
# =============================================================================

TEMPLATE_BASIC = "basic"
TEMPLATE_RESEARCH = "research"
AVAILABLE_TEMPLATES = [TEMPLATE_BASIC, TEMPLATE_RESEARCH]
