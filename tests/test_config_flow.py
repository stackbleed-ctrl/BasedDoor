"""Tests — Config Flow Validation Helpers."""
from __future__ import annotations

import os
import sys
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from custom_components.baseddoor.config_flow import _test_ollama, _test_piper


class TestOllamaConnectionTest:
    @pytest.mark.asyncio
    async def test_returns_none_on_success(self):
        """Simulate Ollama responding with a model list that includes our model."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "models": [{"name": "llama3.2:3b"}]
        }

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_cls.return_value = mock_client

            result = await _test_ollama("http://localhost:11434", "llama3.2:3b")
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_error_when_model_missing(self):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "models": [{"name": "mistral:7b"}]
        }

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_cls.return_value = mock_client

            result = await _test_ollama("http://localhost:11434", "llama3.2:3b")
        assert result == "model_not_found"

    @pytest.mark.asyncio
    async def test_returns_unreachable_on_connection_error(self):
        import httpx

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.get = AsyncMock(side_effect=httpx.ConnectError("refused"))
            mock_client_cls.return_value = mock_client

            result = await _test_ollama("http://localhost:19999", "llama3.2:3b")
        assert result == "ollama_unreachable"

    @pytest.mark.asyncio
    async def test_model_base_name_match(self):
        """llama3.2:3b should match a model listed as llama3.2:3b-instruct."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "models": [{"name": "llama3.2:3b-instruct-q4"}]
        }

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_cls.return_value = mock_client

            result = await _test_ollama("http://localhost:11434", "llama3.2:3b")
        # Base name "llama3.2" should match "llama3.2:3b-instruct-q4"
        assert result is None


class TestPiperConnectionTest:
    @pytest.mark.asyncio
    async def test_returns_none_on_200(self):
        mock_response = MagicMock()
        mock_response.status_code = 200

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_cls.return_value = mock_client

            result = await _test_piper("http://localhost:5000")
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_on_404(self):
        """404 on /health is acceptable — endpoint may not exist but server is up."""
        mock_response = MagicMock()
        mock_response.status_code = 404

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_cls.return_value = mock_client

            result = await _test_piper("http://localhost:5000")
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_error_on_connection_failure(self):
        import httpx

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.get = AsyncMock(side_effect=httpx.ConnectError("refused"))
            mock_client_cls.return_value = mock_client

            result = await _test_piper("http://localhost:19999")
        assert result == "piper_unreachable"
