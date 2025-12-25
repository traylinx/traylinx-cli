"""Tests for manifest models."""

import pytest
from pydantic import ValidationError

from traylinx.models.manifest import (
    AgentManifest,
    AgentInfo,
    AuthorInfo,
    AgentCapability,
    AgentEndpoint,
    AgentPricing,
)


class TestAgentInfo:
    """Tests for AgentInfo model."""
    
    def test_valid_name(self):
        """Valid name formats should pass."""
        info = AgentInfo(
            name="my-agent",
            display_name="My Agent",
            version="1.0.0",
            description="Test agent description that is long enough",
            author=AuthorInfo(name="Test Author"),
        )
        assert info.name == "my-agent"
    
    def test_invalid_name_uppercase(self):
        """Uppercase names should fail."""
        with pytest.raises(ValidationError) as exc:
            AgentInfo(
                name="My-Agent",
                display_name="My Agent",
                version="1.0.0",
                description="Test agent description that is long enough",
                author=AuthorInfo(name="Test Author"),
            )
        assert "lowercase" in str(exc.value).lower()
    
    def test_invalid_name_spaces(self):
        """Names with spaces should fail."""
        with pytest.raises(ValidationError):
            AgentInfo(
                name="my agent",
                display_name="My Agent",
                version="1.0.0",
                description="Test agent description that is long enough",
                author=AuthorInfo(name="Test Author"),
            )
    
    def test_invalid_semver(self):
        """Invalid semver should fail."""
        with pytest.raises(ValidationError) as exc:
            AgentInfo(
                name="my-agent",
                display_name="My Agent",
                version="1.0",  # Missing patch version
                description="Test agent description that is long enough",
                author=AuthorInfo(name="Test Author"),
            )
        assert "semver" in str(exc.value).lower()


class TestAgentCapability:
    """Tests for AgentCapability model."""
    
    def test_standard_key(self):
        """Standard keys should work."""
        cap = AgentCapability(key="domain", value="general")
        assert cap.key == "domain"
    
    def test_custom_key_with_prefix(self):
        """Custom keys with x- prefix should work."""
        cap = AgentCapability(key="x-custom-feature", value="enabled")
        assert cap.key == "x-custom-feature"
    
    def test_custom_key_without_prefix(self):
        """Custom keys without x- prefix should fail."""
        with pytest.raises(ValidationError) as exc:
            AgentCapability(key="custom-feature", value="enabled")
        assert "x-" in str(exc.value)


class TestAgentEndpoint:
    """Tests for AgentEndpoint model."""
    
    def test_valid_path(self):
        """Paths starting with /a2a/ should work."""
        endpoint = AgentEndpoint(
            path="/a2a/run",
            method="POST",
            description="Run the agent",
        )
        assert endpoint.path == "/a2a/run"
    
    def test_invalid_path(self):
        """Paths not starting with /a2a/ should fail."""
        with pytest.raises(ValidationError) as exc:
            AgentEndpoint(
                path="/api/run",
                method="POST",
                description="Run the agent",
            )
        assert "/a2a/" in str(exc.value)


class TestAgentManifest:
    """Tests for full AgentManifest model."""
    
    def test_valid_manifest(self):
        """Valid manifest should pass."""
        manifest = AgentManifest(
            info=AgentInfo(
                name="test-agent",
                display_name="Test Agent",
                version="1.0.0",
                description="A test agent description that is long enough",
                author=AuthorInfo(name="Test Author"),
            ),
            capabilities=[
                AgentCapability(key="domain", value="general"),
            ],
            endpoints=[
                AgentEndpoint(
                    path="/a2a/run",
                    method="POST",
                    description="Run the agent",
                ),
            ],
        )
        assert manifest.info.name == "test-agent"
        assert manifest.manifest_version == "1.0"
    
    def test_free_pricing_no_rates_ok(self):
        """Free pricing without rates should pass."""
        manifest = AgentManifest(
            info=AgentInfo(
                name="free-agent",
                display_name="Free Agent",
                version="1.0.0",
                description="A free agent description that is long enough",
                author=AuthorInfo(name="Test Author"),
            ),
            capabilities=[AgentCapability(key="domain", value="general")],
            endpoints=[AgentEndpoint(path="/a2a/run", method="POST", description="Run the agent")],
            pricing=AgentPricing(model="free"),
        )
        assert manifest.pricing.model == "free"
    
    def test_usage_based_requires_rates(self):
        """Usage-based pricing without rates should fail."""
        with pytest.raises(ValidationError) as exc:
            AgentManifest(
                info=AgentInfo(
                    name="paid-agent",
                    display_name="Paid Agent",
                    version="1.0.0",
                    description="A paid agent description that is long enough",
                    author=AuthorInfo(name="Test Author"),
                ),
                capabilities=[AgentCapability(key="domain", value="general")],
                endpoints=[AgentEndpoint(path="/a2a/run", method="POST", description="Run the agent")],
                pricing=AgentPricing(model="usage_based", rates=[]),
            )
        assert "rate" in str(exc.value).lower()
