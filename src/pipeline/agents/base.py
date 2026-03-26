from abc import ABC, abstractmethod
import logging

from src.pipeline.models import TrendItem


class BaseSourceAgent(ABC):
    """Classe base abstrata para todos os agentes de fonte."""

    def __init__(self, name: str):
        self.name = name
        self.logger = logging.getLogger(f"clip-flow.agent.{name}")

    @abstractmethod
    def fetch(self) -> list[TrendItem]:
        """Busca itens em alta desta fonte.
        Deve tratar seus próprios erros e retornar lista vazia em caso de falha."""
        ...

    def is_available(self) -> bool:
        """Verifica se este agente pode rodar (deps instaladas, etc)."""
        return True
