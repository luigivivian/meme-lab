"""Testes de validacao da migracao Anthropic -> Gemini.

Roda em 3 niveis:
1. Testes de IMPORTACAO — verifica que nenhum arquivo importa anthropic
2. Testes de ESTRUTURA — verifica interfaces e contratos
3. Testes de INTEGRACAO — chama Gemini API de verdade (precisa GOOGLE_API_KEY)

Uso:
    # Testes offline (sem API key)
    python -m pytest tests/test_gemini_migration.py -v -k "not integration"

    # Testes completos (com API key)
    python -m pytest tests/test_gemini_migration.py -v
"""

import ast
import importlib
import json
import os
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

# Garantir que o projeto esta no path
PROJECT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_DIR))


# ============================================================
# Nivel 1: Testes de IMPORTACAO — anthropic nao deve ser importado
# ============================================================

class TestNoAnthropicImports:
    """Verifica que nenhum arquivo do projeto importa anthropic diretamente."""

    MIGRATED_FILES = [
        "src/phrases.py",
        "src/pipeline/processors/analyzer.py",
        "src/pipeline/workers/caption_worker.py",
        "src/llm_client.py",
    ]

    @pytest.mark.parametrize("filepath", MIGRATED_FILES)
    def test_no_anthropic_import(self, filepath):
        """Arquivo nao deve importar 'anthropic'."""
        full_path = PROJECT_DIR / filepath
        if not full_path.exists():
            pytest.skip(f"Arquivo nao encontrado: {filepath}")

        source = full_path.read_text(encoding="utf-8")
        tree = ast.parse(source)

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert alias.name != "anthropic", (
                        f"{filepath} ainda importa 'anthropic' na linha {node.lineno}"
                    )
            elif isinstance(node, ast.ImportFrom):
                if node.module and "anthropic" in node.module:
                    pytest.fail(
                        f"{filepath} ainda importa de 'anthropic' na linha {node.lineno}"
                    )

    def test_llm_client_uses_gemini(self):
        """llm_client.py deve importar google.genai."""
        source = (PROJECT_DIR / "src/llm_client.py").read_text(encoding="utf-8")
        assert "google" in source and "genai" in source, "llm_client.py deve usar google genai"

    def test_requirements_has_gemini(self):
        """requirements.txt deve ter google-genai."""
        reqs = (PROJECT_DIR / "requirements.txt").read_text(encoding="utf-8")
        assert "google-genai" in reqs, "requirements.txt deve incluir google-genai"

    def test_requirements_no_anthropic(self):
        """requirements.txt nao deve ter anthropic."""
        reqs = (PROJECT_DIR / "requirements.txt").read_text(encoding="utf-8")
        assert "anthropic" not in reqs.lower(), "requirements.txt ainda tem anthropic"


# ============================================================
# Nivel 2: Testes de ESTRUTURA — interfaces e contratos
# ============================================================

class TestLLMClientInterface:
    """Verifica que llm_client.py expoe as funcoes corretas."""

    def test_generate_function_exists(self):
        """llm_client deve exportar funcao generate()."""
        from src import llm_client
        assert hasattr(llm_client, "generate"), "llm_client.generate() nao encontrada"
        assert callable(llm_client.generate)

    def test_agenerate_function_exists(self):
        """llm_client deve exportar funcao agenerate()."""
        from src import llm_client
        assert hasattr(llm_client, "agenerate"), "llm_client.agenerate() nao encontrada"
        assert callable(llm_client.agenerate)

    def test_generate_json_function_exists(self):
        """llm_client deve exportar funcao generate_json()."""
        from src import llm_client
        assert hasattr(llm_client, "generate_json"), "llm_client.generate_json() nao encontrada"
        assert callable(llm_client.generate_json)

    def test_generate_signature(self):
        """generate() deve aceitar system_prompt, user_message, max_tokens."""
        import inspect
        from src.llm_client import generate
        sig = inspect.signature(generate)
        params = list(sig.parameters.keys())
        assert "system_prompt" in params
        assert "user_message" in params
        assert "max_tokens" in params


class TestPhrasesInterface:
    """Verifica que phrases.py mantem a mesma interface publica."""

    def test_generate_phrases_exists(self):
        """generate_phrases(topic, count) deve existir."""
        from src.phrases import generate_phrases
        import inspect
        sig = inspect.signature(generate_phrases)
        params = list(sig.parameters.keys())
        assert "topic" in params
        assert "count" in params

    @patch("src.phrases.generate")
    def test_generate_phrases_returns_list(self, mock_generate):
        """generate_phrases deve retornar lista de strings."""
        mock_generate.return_value = "Frase um\nFrase dois\nFrase tres"
        from src.phrases import generate_phrases
        result = generate_phrases("teste", count=3)
        assert isinstance(result, list)
        assert len(result) == 3
        assert all(isinstance(f, str) for f in result)

    @patch("src.phrases.generate")
    def test_generate_phrases_strips_empty_lines(self, mock_generate):
        """generate_phrases deve ignorar linhas vazias."""
        mock_generate.return_value = "Frase um\n\n\nFrase dois\n\n"
        from src.phrases import generate_phrases
        result = generate_phrases("teste", count=2)
        assert len(result) == 2


class TestAnalyzerInterface:
    """Verifica que ClaudeAnalyzer mantem a mesma interface."""

    def test_analyzer_class_exists(self):
        """ClaudeAnalyzer deve existir (nome mantido por compatibilidade)."""
        from src.pipeline.processors.analyzer import ClaudeAnalyzer
        analyzer = ClaudeAnalyzer()
        assert hasattr(analyzer, "analyze")

    @patch("src.pipeline.processors.analyzer.generate_json")
    def test_analyzer_returns_analyzed_topics(self, mock_json):
        """analyze() deve retornar lista de AnalyzedTopic."""
        mock_json.return_value = json.dumps([{
            "original_title": "Teste Trend",
            "gandalf_topic": "cafe na segunda",
            "humor_angle": "zoeira leve",
            "relevance_score": 0.9,
        }])
        from src.pipeline.processors.analyzer import ClaudeAnalyzer
        from src.pipeline.models import TrendItem, TrendSource
        analyzer = ClaudeAnalyzer()
        trends = [TrendItem(title="Teste Trend", source=TrendSource.GOOGLE_TRENDS)]
        result = analyzer.analyze(trends, count=1)
        assert len(result) == 1
        assert result[0].gandalf_topic == "cafe na segunda"


class TestCaptionWorkerInterface:
    """Verifica que CaptionWorker mantem a mesma interface."""

    def test_caption_worker_exists(self):
        """CaptionWorker deve existir e ter metodo generate."""
        from src.pipeline.workers.caption_worker import CaptionWorker
        worker = CaptionWorker()
        assert hasattr(worker, "generate")


class TestConfigUpdated:
    """Verifica que config.py foi atualizado para Gemini."""

    def test_gemini_max_concurrent_exists(self):
        """config deve ter GEMINI_MAX_CONCURRENT."""
        from config import GEMINI_MAX_CONCURRENT
        assert isinstance(GEMINI_MAX_CONCURRENT, int)
        assert GEMINI_MAX_CONCURRENT > 0

    def test_system_prompt_has_mago_mestre(self):
        """SYSTEM_PROMPT deve mencionar Mago Mestre."""
        from config import SYSTEM_PROMPT
        assert "Mago Mestre" in SYSTEM_PROMPT or "mago" in SYSTEM_PROMPT.lower()

    def test_system_prompt_has_formulas(self):
        """SYSTEM_PROMPT refinado deve ter formulas de viralizacao."""
        from config import SYSTEM_PROMPT
        assert "VIRAL" in SYSTEM_PROMPT or "viral" in SYSTEM_PROMPT

    def test_system_prompt_max_chars_rule(self):
        """SYSTEM_PROMPT deve manter regra de 120 caracteres."""
        from config import SYSTEM_PROMPT
        assert "120" in SYSTEM_PROMPT


# ============================================================
# Nivel 3: Testes de INTEGRACAO — chamadas reais ao Gemini
# ============================================================

@pytest.mark.skipif(
    not os.getenv("GOOGLE_API_KEY"),
    reason="GOOGLE_API_KEY nao configurada — pulando testes de integracao"
)
class TestIntegrationGemini:
    """Testes que fazem chamadas reais ao Gemini API."""

    def test_llm_client_generate(self):
        """generate() deve retornar texto nao vazio."""
        from src.llm_client import generate
        result = generate(
            system_prompt="Responda em portugues, seja breve.",
            user_message="Diga 'ola mundo' e nada mais.",
            max_tokens=50,
        )
        assert isinstance(result, str)
        assert len(result) > 0

    def test_llm_client_generate_json(self):
        """generate_json() deve retornar JSON valido."""
        from src.llm_client import generate_json
        result = generate_json(
            system_prompt="Responda em JSON valido.",
            user_message='Retorne: {"status": "ok", "numero": 42}',
            max_tokens=100,
        )
        parsed = json.loads(result)
        assert isinstance(parsed, dict)

    def test_generate_phrases_integration(self):
        """generate_phrases() deve retornar frases reais."""
        from src.phrases import generate_phrases
        frases = generate_phrases("cafe", count=2)
        assert isinstance(frases, list)
        assert len(frases) >= 1
        # Cada frase deve ter conteudo
        for f in frases:
            assert len(f) > 5, f"Frase muito curta: '{f}'"

    def test_phrases_quality(self):
        """Frases geradas devem atender criterios de qualidade."""
        from src.phrases import generate_phrases
        frases = generate_phrases("segunda-feira", count=3)

        for frase in frases:
            # Nao deve ter numeracao (1., 2., -)
            assert not frase[0].isdigit(), f"Frase com numeracao: '{frase}'"
            assert not frase.startswith("-"), f"Frase com marcador: '{frase}'"
            # Deve ter tamanho razoavel
            assert len(frase) <= 150, f"Frase muito longa ({len(frase)} chars): '{frase}'"
            assert len(frase) >= 10, f"Frase muito curta: '{frase}'"

    def test_analyzer_integration(self):
        """ClaudeAnalyzer.analyze() deve retornar AnalyzedTopics reais."""
        from src.pipeline.processors.analyzer import ClaudeAnalyzer
        from src.pipeline.models import TrendItem, TrendSource
        analyzer = ClaudeAnalyzer()
        trends = [
            TrendItem(title="Copa do Mundo", source=TrendSource.GOOGLE_TRENDS, traffic="100K+"),
            TrendItem(title="Black Friday", source=TrendSource.GOOGLE_TRENDS, traffic="50K+"),
            TrendItem(title="ChatGPT", source=TrendSource.REDDIT, traffic="10K+"),
        ]
        result = analyzer.analyze(trends, count=2)
        assert len(result) >= 1
        for topic in result:
            assert topic.gandalf_topic, "gandalf_topic vazio"
            assert topic.humor_angle, "humor_angle vazio"
            assert 0 <= topic.relevance_score <= 1
