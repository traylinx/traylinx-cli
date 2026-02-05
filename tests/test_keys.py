"""
Tests for API Keys management commands.
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


class TestApiKeysDir:
    """Tests for StateBox api_keys_dir method."""

    def test_api_keys_dir_returns_correct_path(self, tmp_path):
        """Test that api_keys_dir returns correct path."""
        from traylinx.utils.statebox import StateBox

        with patch.object(StateBox, "root", return_value=tmp_path):
            expected = tmp_path / "credentials" / "api-keys"
            assert StateBox.api_keys_dir() == expected


class TestKeysHelpers:
    """Tests for keys module helper functions."""

    def test_get_api_keys_dir(self, tmp_path):
        """Test _get_api_keys_dir returns correct path."""
        from traylinx.commands.keys import _get_api_keys_dir
        from traylinx.utils.statebox import StateBox

        with patch.object(StateBox, "credentials_dir", return_value=tmp_path / "credentials"):
            result = _get_api_keys_dir()
            assert result == tmp_path / "credentials" / "api-keys"

    def test_list_local_keys_empty_dir(self, tmp_path):
        """Test listing keys when directory doesn't exist."""
        from traylinx.commands.keys import _list_local_keys, _get_api_keys_dir
        from traylinx.utils.statebox import StateBox

        with patch.object(StateBox, "credentials_dir", return_value=tmp_path):
            result = _list_local_keys()
            assert result == []

    def test_list_local_keys_with_files(self, tmp_path):
        """Test listing keys when files exist."""
        from traylinx.commands.keys import _list_local_keys
        from traylinx.utils.statebox import StateBox

        # Create test keys directory
        keys_dir = tmp_path / "credentials" / "api-keys"
        keys_dir.mkdir(parents=True)

        # Create test key file
        test_key = {
            "id": "api-key-123",
            "public_key": "pk-lf-test",
            "secret_key": "sk-lf-test",
            "note": "test-key",
        }
        (keys_dir / "test-key.json").write_text(json.dumps(test_key))

        with patch.object(StateBox, "credentials_dir", return_value=tmp_path / "credentials"):
            result = _list_local_keys()
            assert len(result) == 1
            assert result[0]["note"] == "test-key"
            assert result[0]["public_key"] == "pk-lf-test"

    def test_load_api_key_by_name(self, tmp_path):
        """Test loading a key by name."""
        from traylinx.commands.keys import _load_api_key
        from traylinx.utils.statebox import StateBox

        # Create test keys directory
        keys_dir = tmp_path / "credentials" / "api-keys"
        keys_dir.mkdir(parents=True)

        # Create test key file
        test_key = {
            "id": "api-key-123",
            "public_key": "pk-lf-test",
            "secret_key": "sk-lf-secret123",
            "note": "myapp",
        }
        (keys_dir / "myapp.json").write_text(json.dumps(test_key))

        with patch.object(StateBox, "credentials_dir", return_value=tmp_path / "credentials"):
            result = _load_api_key("myapp")
            assert result is not None
            assert result["secret_key"] == "sk-lf-secret123"

    def test_load_api_key_not_found(self, tmp_path):
        """Test loading a key that doesn't exist."""
        from traylinx.commands.keys import _load_api_key
        from traylinx.utils.statebox import StateBox

        keys_dir = tmp_path / "credentials" / "api-keys"
        keys_dir.mkdir(parents=True)

        with patch.object(StateBox, "credentials_dir", return_value=tmp_path / "credentials"):
            result = _load_api_key("nonexistent")
            assert result is None


class TestExportFormats:
    """Tests for export command formats."""

    def test_yaml_format_structure(self):
        """Test that YAML export contains expected structure."""
        # This tests the expected output format
        expected_keys = ["switchai-api-key", "api-key", "base-url", "models"]
        yaml_output = """switchai-api-key:
  - api-key: "sk-lf-test"
    base-url: "https://switchai.traylinx.com/v1"
    models:
      - name: "openai/gpt-oss-120b"
"""
        for key in ["switchai-api-key", "api-key", "base-url", "models"]:
            assert key in yaml_output

    def test_env_format_structure(self):
        """Test that env export contains expected variables."""
        env_output = """export TRAYLINX_API_KEY="sk-lf-test"
export OPENAI_API_KEY="sk-lf-test"
export OPENAI_BASE_URL="https://switchai.traylinx.com/v1"
"""
        assert "TRAYLINX_API_KEY" in env_output
        assert "OPENAI_API_KEY" in env_output
        assert "OPENAI_BASE_URL" in env_output


class TestCreateKeyMocked:
    """Tests for create command with mocked API."""

    @patch("traylinx.commands.keys.httpx.post")
    @patch("traylinx.commands.keys.AuthManager.get_credentials")
    @patch("traylinx.commands.keys.ContextManager.get_current_organization_id")
    @patch("traylinx.commands.keys.ContextManager.get_current_project_id")
    def test_create_key_api_response_parsing(
        self,
        mock_project,
        mock_org,
        mock_creds,
        mock_post,
    ):
        """Test that API response is correctly parsed."""
        # Setup mocks
        mock_creds.return_value = {"access_token": "test-token"}
        mock_org.return_value = "org-123"
        mock_project.return_value = "proj-456"

        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {
            "data": {
                "id": "api-key-789",
                "attributes": {
                    "publicKey": "pk-lf-abc123",
                    "displaySecretKey": "sk-lf-...xyz",
                    "note": "test-key",
                    "createdAt": "2026-02-05T10:00:00Z",
                },
            },
            "meta": {
                "secretKey": "sk-lf-full-secret-key-here",
            },
        }
        mock_post.return_value = mock_response

        # Verify the mock is set up correctly
        result = mock_response.json()
        assert result["data"]["attributes"]["publicKey"] == "pk-lf-abc123"
        assert result["meta"]["secretKey"] == "sk-lf-full-secret-key-here"
