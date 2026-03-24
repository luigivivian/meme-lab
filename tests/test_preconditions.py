"""Testes para pre-condicoes Phase 1: CORS, Gemini models, log sanitizer, health."""
import logging
import os
import pytest
from httpx import AsyncClient, ASGITransport
from src.api.app import app


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# PRE-01: CORS
@pytest.mark.asyncio
async def test_cors_credentials(client):
    """CORS retorna headers corretos para request credenciado de localhost:3000."""
    response = await client.options(
        "/health",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.headers.get("access-control-allow-origin") == "http://localhost:3000"
    assert response.headers.get("access-control-allow-credentials") == "true"


@pytest.mark.asyncio
async def test_cors_rejects_unknown_origin(client):
    """CORS nao retorna allow-origin para dominio desconhecido."""
    response = await client.options(
        "/health",
        headers={
            "Origin": "http://evil.com",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.headers.get("access-control-allow-origin") != "http://evil.com"


# PRE-02: Gemini model discovery (stub — filled in Plan 02)
@pytest.mark.asyncio
async def test_model_discovery():
    """Gemini model discovery retorna lista de modelos de imagem."""
    pytest.skip("Implementado no Plan 02")


# PRE-03: Log sanitizer
def test_log_sanitizer_masks_api_key():
    """Log sanitizer mascara GOOGLE_API_KEY no output."""
    from src.api.log_sanitizer import SensitiveDataFilter
    os.environ["GOOGLE_API_KEY"] = "AIzaSyD-test-key-1234567890abcdef"
    f = SensitiveDataFilter()
    record = logging.LogRecord(
        name="test", level=logging.INFO, pathname="", lineno=0,
        msg="Key is AIzaSyD-test-key-1234567890abcdef here",
        args=None, exc_info=None,
    )
    f.filter(record)
    assert "AIzaSyD-test-key-1234567890abcdef" not in record.msg
    assert "***" in record.msg


def test_log_sanitizer_masks_args():
    """Log sanitizer mascara valores em record.args (% formatting)."""
    from src.api.log_sanitizer import SensitiveDataFilter
    os.environ["GOOGLE_API_KEY"] = "AIzaSyD-test-key-1234567890abcdef"
    f = SensitiveDataFilter()
    record = logging.LogRecord(
        name="test", level=logging.INFO, pathname="", lineno=0,
        msg="Key: %s", args=("AIzaSyD-test-key-1234567890abcdef",),
        exc_info=None,
    )
    f.filter(record)
    assert "AIzaSyD-test-key-1234567890abcdef" not in str(record.args)


def test_log_sanitizer_masks_database_url():
    """Log sanitizer mascara password do DATABASE_URL."""
    from src.api.log_sanitizer import SensitiveDataFilter
    os.environ["DATABASE_URL"] = "mysql+aiomysql://root:masterkey@localhost/memelab"
    f = SensitiveDataFilter()
    record = logging.LogRecord(
        name="test", level=logging.INFO, pathname="", lineno=0,
        msg="DB: mysql+aiomysql://root:masterkey@localhost/memelab",
        args=None, exc_info=None,
    )
    f.filter(record)
    assert "masterkey" not in record.msg
    assert "***" in record.msg


def test_log_sanitizer_masks_bearer_token():
    """Log sanitizer mascara Bearer tokens."""
    from src.api.log_sanitizer import SensitiveDataFilter
    f = SensitiveDataFilter()
    record = logging.LogRecord(
        name="test", level=logging.INFO, pathname="", lineno=0,
        msg="Auth: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.abcdef",
        args=None, exc_info=None,
    )
    f.filter(record)
    assert "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9" not in record.msg


# PRE-01 + D-09: Health endpoint (stub — filled in Plan 02)
@pytest.mark.asyncio
async def test_health_endpoint(client):
    """GET /health retorna status com info de DB e Gemini."""
    pytest.skip("Implementado no Plan 02")
