"""HashtagWorker — gera hashtags relevantes para o conteudo.

Mix de hashtags: tematicas + humor generico + branded.
"""

import logging

from config import HASHTAG_COUNT
from src.pipeline.models_v2 import ContentPackage

logger = logging.getLogger("clip-flow.worker.hashtag")

# Hashtags fixas do perfil (sempre incluidas)
BRANDED_HASHTAGS = [
    "#magomestre420",
    "#magomestre",
    "#gandalf",
    "#memesmago",
]

# Hashtags genericas de humor/memes brasileiros
HUMOR_HASHTAGS = [
    "#memes",
    "#memesbrasileiros",
    "#humor",
    "#engracado",
    "#risada",
    "#zoeira",
    "#memesbr",
    "#humorbrasil",
    "#piadas",
    "#comedia",
    "#viral",
    "#trending",
    "#420",
    "#weed",
    "#maconha",
    "#larica"
]

# Mapa de temas para hashtags especificas
TOPIC_HASHTAGS = {
    "segunda": ["#segundafeira", "#segunda", "#mondaymood", "#voltaatrabalhar"],
    "cafe": ["#cafe", "#coffee", "#cafedamanha", "#masamescafe"],
    "trabalho": ["#trabalho", "#trampo", "#escritorio", "#homeoffice", "#chefe"],
    "tecnologia": ["#tecnologia", "#internet", "#wifi", "#celular", "#redessociais"],
    "comida": ["#comida", "#fome", "#cozinha", "#receita", "#foodlover"],
    "relacionamento": ["#relacionamento", "#crush", "#namoro", "#amor", "#solteiro"],
    "sono": ["#sono", "#dormir", "#preguica", "#cansaco", "#fimdesemana"],
    "feriado": ["#feriado", "#ferias", "#descanso", "#folga", "#fimdesemana"],
    "internet": ["#internet", "#redessociais", "#instagram", "#tiktok", "#twitter"],
}


class HashtagWorker:
    """Pesquisa e monta lista de hashtags relevantes."""

    async def research(self, package: ContentPackage) -> list[str]:
        """Gera lista de hashtags para um ContentPackage.

        Returns:
            lista de hashtags (com #) limitada a HASHTAG_COUNT
        """
        hashtags = list(BRANDED_HASHTAGS)

        # Adicionar hashtags tematicas baseadas no topico
        topic_lower = package.topic.lower()
        for keyword, tags in TOPIC_HASHTAGS.items():
            if keyword in topic_lower:
                hashtags.extend(tags)

        # Completar com hashtags genericas de humor
        for tag in HUMOR_HASHTAGS:
            if tag not in hashtags:
                hashtags.append(tag)
            if len(hashtags) >= HASHTAG_COUNT:
                break

        # Deduplicar e limitar
        seen = set()
        unique = []
        for tag in hashtags:
            if tag not in seen:
                seen.add(tag)
                unique.append(tag)

        result = unique[:HASHTAG_COUNT]
        logger.info(f"Hashtags geradas: {len(result)} tags")
        return result
