"""Agent Manifest Pydantic Models.

Based on traylinx-agent.yaml specification.
"""

import re
from typing import Literal, Self

from pydantic import BaseModel, EmailStr, Field, HttpUrl, model_validator


class AuthorInfo(BaseModel):
    """Agent author information."""
    
    name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr | None = None
    url: HttpUrl | None = None


class AgentInfo(BaseModel):
    """Agent identity and metadata."""
    
    name: str = Field(
        ...,
        min_length=2,
        max_length=64,
        description="Unique agent identifier (lowercase, hyphens)",
    )
    display_name: str = Field(..., min_length=1, max_length=100)
    version: str = Field(
        ...,
        description="Semantic version (e.g., 1.0.0)",
    )
    description: str = Field(..., min_length=10, max_length=1000)
    icon_url: HttpUrl | None = None
    author: AuthorInfo
    license: str | None = Field(None, max_length=50)
    homepage: HttpUrl | None = None
    tags: list[str] = Field(default_factory=list, max_length=10)
    
    @model_validator(mode="after")
    def validate_name_format(self) -> Self:
        """Validate name is RFC 1035 label format."""
        if not re.match(r"^[a-z][a-z0-9-]*[a-z0-9]$", self.name):
            raise ValueError(
                "Name must be lowercase, start with a letter, "
                "end with letter/number, and contain only letters, numbers, hyphens"
            )
        if "--" in self.name:
            raise ValueError("Name cannot contain consecutive hyphens")
        return self
    
    @model_validator(mode="after")
    def validate_semver(self) -> Self:
        """Validate version is semver format."""
        if not re.match(r"^\d+\.\d+\.\d+(-[a-zA-Z0-9.]+)?$", self.version):
            raise ValueError(
                "Version must be semver format (e.g., 1.0.0, 2.1.0-beta)"
            )
        return self


class AgentCapability(BaseModel):
    """Agent capability declaration."""
    
    key: Literal["domain", "op", "input_format", "output_format", "scope"] | str
    value: str = Field(..., min_length=1, max_length=64)
    description: str | None = None
    
    @model_validator(mode="after")
    def validate_custom_key(self) -> Self:
        """Custom keys must start with x-."""
        standard_keys = {"domain", "op", "input_format", "output_format", "scope"}
        if self.key not in standard_keys and not self.key.startswith("x-"):
            raise ValueError(
                f"Custom capability keys must start with 'x-', got: {self.key}"
            )
        return self


class EndpointSchema(BaseModel):
    """Endpoint input/output schema references."""
    
    input: str | None = Field(None, description="Path to input JSON schema")
    output: str | None = Field(None, description="Path to output JSON schema")


class AgentEndpoint(BaseModel):
    """Agent A2A endpoint definition."""
    
    path: str = Field(
        ...,
        description="Endpoint path (must start with /a2a/)",
    )
    method: Literal["GET", "POST", "PUT", "DELETE"] = "POST"
    description: str = Field(..., min_length=5, max_length=500)
    schema_: EndpointSchema | None = Field(None, alias="schema")
    timeout_seconds: int = Field(default=60, ge=1, le=600)
    auth_required: bool = True
    
    @model_validator(mode="after")
    def validate_path(self) -> Self:
        """Validate path starts with /a2a/."""
        if not self.path.startswith("/a2a/"):
            raise ValueError("Endpoint path must start with /a2a/")
        return self


class PricingRate(BaseModel):
    """Usage-based pricing rate."""
    
    metric: Literal["request", "compute_minute", "token", "mb_processed"]
    amount: int = Field(ge=0, description="Credits per unit")
    description: str | None = None


class SubscriptionTier(BaseModel):
    """Subscription pricing tier."""
    
    name: str = Field(..., min_length=1, max_length=50)
    credits_per_month: int = Field(ge=0)
    price_usd: float = Field(ge=0)


class AgentPricing(BaseModel):
    """Agent pricing configuration."""
    
    model: Literal["usage_based", "subscription", "free"] = "free"
    currency: Literal["CREDITS"] = "CREDITS"
    rates: list[PricingRate] = Field(default_factory=list)
    subscription_tiers: list[SubscriptionTier] = Field(default_factory=list)


class ExternalDependency(BaseModel):
    """External API dependency."""
    
    external_api: str
    required: bool = True


class AgentInfrastructure(BaseModel):
    """Agent infrastructure requirements."""
    
    min_memory: str | None = Field(None, description="e.g., 1GB, 512MB")
    min_cpu: str | None = Field(None, description="e.g., 0.5, 2")
    network_access: bool = True
    environment: list[str] = Field(default_factory=list, description="Required env vars")
    dependencies: list[ExternalDependency] = Field(default_factory=list)


class AgentManifest(BaseModel):
    """Complete Traylinx Agent Manifest (traylinx-agent.yaml)."""
    
    manifest_version: Literal["1.0"] = "1.0"
    info: AgentInfo
    capabilities: list[AgentCapability] = Field(min_length=1)
    endpoints: list[AgentEndpoint] = Field(min_length=1)
    pricing: AgentPricing = Field(default_factory=AgentPricing)
    infrastructure: AgentInfrastructure | None = None
    
    @model_validator(mode="after")
    def validate_pricing_config(self) -> Self:
        """Validate pricing configuration is consistent."""
        if self.pricing.model == "usage_based" and not self.pricing.rates:
            raise ValueError("Usage-based pricing requires at least one rate")
        if self.pricing.model == "subscription" and not self.pricing.subscription_tiers:
            raise ValueError("Subscription pricing requires at least one tier")
        return self


def load_manifest_from_yaml(path: str) -> AgentManifest:
    """Load and validate manifest from YAML file."""
    import yaml
    from pathlib import Path
    
    manifest_path = Path(path)
    if not manifest_path.exists():
        raise FileNotFoundError(f"Manifest not found: {path}")
    
    with open(manifest_path) as f:
        data = yaml.safe_load(f)
    
    return AgentManifest.model_validate(data)


def export_json_schema(output_path: str | None = None) -> dict:
    """Export AgentManifest as JSON Schema."""
    import json
    from pathlib import Path
    
    schema = AgentManifest.model_json_schema()
    
    if output_path:
        Path(output_path).write_text(json.dumps(schema, indent=2))
    
    return schema
