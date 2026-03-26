"""Cliente para Instagram Graph API — publicacao de conteudo.

Suporta:
- Imagem unica (post feed)
- Carousel (2-10 imagens)
- Reels (video + cover)
- Insights de media e conta

Requer INSTAGRAM_ACCESS_TOKEN e INSTAGRAM_BUSINESS_ID no .env.
Imagens precisam estar em URL publica (CDN, ngrok, etc).

Referencia: https://developers.facebook.com/docs/instagram-platform/instagram-graph-api
"""

import asyncio
import logging
import os
from pathlib import Path

import httpx

import config

logger = logging.getLogger("clip-flow.instagram")

# ── Erros especificos ──────────────────────────────────────────────

class InstagramAPIError(Exception):
    """Erro retornado pela Instagram Graph API."""

    def __init__(self, message: str, code: int = 0, subcode: int = 0, fb_trace_id: str = ""):
        self.code = code
        self.subcode = subcode
        self.fb_trace_id = fb_trace_id
        super().__init__(message)

    def __str__(self):
        base = super().__str__()
        return f"[IG-{self.code}/{self.subcode}] {base} (trace: {self.fb_trace_id})"


class InstagramRateLimitError(InstagramAPIError):
    """Rate limit atingido (codigo 4 ou 32)."""
    pass


class InstagramMediaError(InstagramAPIError):
    """Erro ao criar/publicar container de media."""
    pass


# ── Cliente principal ──────────────────────────────────────────────

class InstagramClient:
    """Cliente async para Instagram Graph API — publicacao e metricas."""

    # Status do container de video/reel
    _CONTAINER_FINISHED = "FINISHED"
    _CONTAINER_ERROR = "ERROR"
    _CONTAINER_IN_PROGRESS = "IN_PROGRESS"

    # Metricas disponiveis por tipo de media
    MEDIA_METRICS_IMAGE = ["impressions", "reach", "likes", "comments", "shares", "saved"]
    MEDIA_METRICS_CAROUSEL = ["impressions", "reach", "likes", "comments", "shares", "saved"]
    MEDIA_METRICS_REEL = ["impressions", "reach", "likes", "comments", "shares", "saved", "plays"]
    ACCOUNT_METRICS_DEFAULT = ["impressions", "reach", "follower_count"]

    def __init__(self, access_token: str | None = None, business_id: str | None = None):
        self.access_token = access_token or config.INSTAGRAM_ACCESS_TOKEN
        self.business_id = business_id or config.INSTAGRAM_BUSINESS_ID
        self.api_base = config.INSTAGRAM_API_BASE
        self._client: httpx.AsyncClient | None = None

    # ── Lifecycle ──────────────────────────────────────────────────

    async def _get_client(self) -> httpx.AsyncClient:
        """Retorna httpx client reutilizavel (lazy init)."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(30.0, connect=10.0),
                headers={"User-Agent": "ClipFlow/2.0"},
            )
        return self._client

    async def close(self):
        """Fecha o client HTTP."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    # ── Verificacao ────────────────────────────────────────────────

    def is_available(self) -> bool:
        """Verifica se as credenciais estao configuradas."""
        return bool(self.access_token) and bool(self.business_id)

    # ── Publicacao: Imagem unica ───────────────────────────────────

    async def publish_image(self, image_url: str, caption: str) -> dict:
        """Publica imagem unica no Instagram.

        Instagram Graph API flow:
        1. POST /{ig-user-id}/media — cria container (image_url + caption)
        2. POST /{ig-user-id}/media_publish — publica o container

        Args:
            image_url: URL publica da imagem (JPEG/PNG, max 8MB)
            caption: Legenda com hashtags (max 2200 chars)

        Returns:
            {id: str, permalink: str, timestamp: str}
        """
        caption = self._truncate_caption(caption)
        logger.info(f"Publicando imagem: {image_url[:80]}...")

        container_id = await self._create_container(
            image_url=image_url,
            caption=caption,
        )
        result = await self._publish_container(container_id)

        logger.info(f"Imagem publicada com sucesso — id={result.get('id')}")
        return result

    # ── Publicacao: Carousel ───────────────────────────────────────

    async def publish_carousel(self, image_urls: list[str], caption: str) -> dict:
        """Publica carousel (2-10 imagens) no Instagram.

        Flow:
        1. POST /{ig-user-id}/media para cada imagem (is_carousel_item=true)
        2. POST /{ig-user-id}/media com children=[item_ids] + caption
        3. POST /{ig-user-id}/media_publish

        Args:
            image_urls: Lista de 2-10 URLs publicas de imagens
            caption: Legenda unica para o carousel

        Returns:
            {id: str, permalink: str, timestamp: str}
        """
        if len(image_urls) < 2:
            raise ValueError("Carousel requer no minimo 2 imagens")
        if len(image_urls) > 10:
            raise ValueError("Carousel suporta no maximo 10 imagens")

        caption = self._truncate_caption(caption)
        logger.info(f"Publicando carousel com {len(image_urls)} imagens...")

        # Passo 1: criar containers individuais em paralelo
        tasks = [
            self._create_container(image_url=url, is_carousel_item=True)
            for url in image_urls
        ]
        item_ids = await asyncio.gather(*tasks)
        logger.info(f"Carousel: {len(item_ids)} containers criados")

        # Passo 2: criar container do carousel
        carousel_id = await self._create_container(
            media_type="CAROUSEL",
            children=list(item_ids),
            caption=caption,
        )

        # Passo 3: publicar
        result = await self._publish_container(carousel_id)
        logger.info(f"Carousel publicado com sucesso — id={result.get('id')}")
        return result

    # ── Publicacao: Reel ───────────────────────────────────────────

    async def publish_reel(
        self,
        video_url: str,
        caption: str,
        cover_url: str | None = None,
        share_to_feed: bool = True,
    ) -> dict:
        """Publica Reel no Instagram.

        Flow:
        1. POST /{ig-user-id}/media (media_type=REELS, video_url, caption)
        2. Poll GET /{container-id}?fields=status_code ate FINISHED
        3. POST /{ig-user-id}/media_publish

        Args:
            video_url: URL publica do video (MP4, max 15min, max 1GB)
            caption: Legenda do reel
            cover_url: URL da thumbnail (opcional)
            share_to_feed: Se True, aparece tambem no feed

        Returns:
            {id: str, permalink: str, timestamp: str}
        """
        caption = self._truncate_caption(caption)
        logger.info(f"Publicando Reel: {video_url[:80]}...")

        params = {
            "media_type": "REELS",
            "video_url": video_url,
            "caption": caption,
            "share_to_feed": str(share_to_feed).lower(),
        }
        if cover_url:
            params["cover_url"] = cover_url

        container_id = await self._create_container(**params)

        # Reels precisam de processamento — poll ate FINISHED
        ok = await self._wait_for_container(container_id, timeout=120)
        if not ok:
            raise InstagramMediaError(
                f"Timeout aguardando processamento do Reel (container={container_id})"
            )

        result = await self._publish_container(container_id)
        logger.info(f"Reel publicado com sucesso — id={result.get('id')}")
        return result

    # ── Insights: Media ────────────────────────────────────────────

    async def get_media_insights(self, media_id: str, metrics: list[str] | None = None) -> dict:
        """Busca metricas de um post publicado.

        Args:
            media_id: ID do post no Instagram
            metrics: Lista de metricas (default: impressions, reach, likes, etc.)

        Returns:
            {metric_name: value, ...}
        """
        if metrics is None:
            metrics = self.MEDIA_METRICS_IMAGE

        data = await self._request(
            "GET",
            f"/{media_id}/insights",
            params={"metric": ",".join(metrics)},
        )

        # Parsear resposta do insights API
        result = {}
        for item in data.get("data", []):
            name = item.get("name", "")
            values = item.get("values", [])
            if values:
                result[name] = values[0].get("value", 0)
        return result

    # ── Insights: Conta ────────────────────────────────────────────

    async def get_account_insights(
        self,
        period: str = "day",
        metrics: list[str] | None = None,
    ) -> dict:
        """Metricas da conta (followers, reach, impressions).

        Args:
            period: "day", "week", "days_28" (lifetime nao suportado para todas)
            metrics: Lista de metricas (default: impressions, reach, follower_count)

        Returns:
            {metric_name: {values: [...], title: str}, ...}
        """
        if metrics is None:
            metrics = self.ACCOUNT_METRICS_DEFAULT

        data = await self._request(
            "GET",
            f"/{self.business_id}/insights",
            params={
                "metric": ",".join(metrics),
                "period": period,
            },
        )

        result = {}
        for item in data.get("data", []):
            name = item.get("name", "")
            result[name] = {
                "title": item.get("title", name),
                "values": item.get("values", []),
            }
        return result

    # ── Informacoes da conta ───────────────────────────────────────

    async def get_account_info(self) -> dict:
        """Busca informacoes basicas da conta Instagram Business.

        Returns:
            {id, username, name, biography, followers_count, media_count, ...}
        """
        data = await self._request(
            "GET",
            f"/{self.business_id}",
            params={
                "fields": "id,username,name,biography,followers_count,media_count,profile_picture_url",
            },
        )
        return data

    # ── Helpers internos ───────────────────────────────────────────

    async def _create_container(self, **kwargs) -> str:
        """Cria media container na Graph API e retorna container_id.

        Kwargs aceitos:
            image_url, video_url, caption, media_type,
            is_carousel_item, children, cover_url, share_to_feed
        """
        params = {k: v for k, v in kwargs.items() if v is not None}

        # children precisa ser lista separada por virgula
        if "children" in params and isinstance(params["children"], list):
            params["children"] = ",".join(params["children"])

        # is_carousel_item precisa ser string "true"
        if "is_carousel_item" in params:
            params["is_carousel_item"] = str(params["is_carousel_item"]).lower()

        data = await self._request(
            "POST",
            f"/{self.business_id}/media",
            params=params,
        )

        container_id = data.get("id")
        if not container_id:
            raise InstagramMediaError(f"API nao retornou container_id: {data}")

        logger.debug(f"Container criado: {container_id}")
        return container_id

    async def _publish_container(self, container_id: str) -> dict:
        """Publica um container e retorna dados do post.

        Returns:
            {id: str, permalink: str, timestamp: str}
        """
        data = await self._request(
            "POST",
            f"/{self.business_id}/media_publish",
            params={"creation_id": container_id},
        )

        media_id = data.get("id")
        if not media_id:
            raise InstagramMediaError(f"Publish nao retornou media_id: {data}")

        # Buscar permalink e timestamp do post publicado
        media_info = await self._request(
            "GET",
            f"/{media_id}",
            params={"fields": "id,permalink,timestamp,media_type"},
        )

        return {
            "id": media_info.get("id", media_id),
            "permalink": media_info.get("permalink", ""),
            "timestamp": media_info.get("timestamp", ""),
            "media_type": media_info.get("media_type", ""),
        }

    async def _wait_for_container(self, container_id: str, timeout: int = 60) -> bool:
        """Poll status do container ate FINISHED (necessario para videos/reels).

        Args:
            container_id: ID do container
            timeout: Timeout em segundos

        Returns:
            True se FINISHED, False se timeout
        """
        elapsed = 0
        interval = 3  # segundos entre polls

        while elapsed < timeout:
            data = await self._request(
                "GET",
                f"/{container_id}",
                params={"fields": "status_code,status"},
            )

            status = data.get("status_code", "")
            logger.debug(f"Container {container_id} status: {status}")

            if status == self._CONTAINER_FINISHED:
                return True

            if status == self._CONTAINER_ERROR:
                error_msg = data.get("status", "Erro desconhecido no processamento")
                raise InstagramMediaError(
                    f"Container {container_id} falhou: {error_msg}"
                )

            await asyncio.sleep(interval)
            elapsed += interval

        logger.warning(f"Timeout ({timeout}s) aguardando container {container_id}")
        return False

    async def _request(
        self,
        method: str,
        endpoint: str,
        params: dict | None = None,
        max_retries: int = 2,
    ) -> dict:
        """Helper HTTP com retry e tratamento de erros da Graph API.

        Args:
            method: "GET" ou "POST"
            endpoint: Path relativo (ex: /{ig-user-id}/media)
            params: Query params ou form data
            max_retries: Tentativas em caso de rate limit

        Returns:
            JSON da resposta

        Raises:
            InstagramRateLimitError: Rate limit excedido apos retries
            InstagramAPIError: Erro generico da API
        """
        url = f"{self.api_base}{endpoint}"
        params = dict(params or {})
        params["access_token"] = self.access_token

        client = await self._get_client()

        for attempt in range(max_retries + 1):
            try:
                if method.upper() == "GET":
                    response = await client.get(url, params=params)
                else:
                    response = await client.post(url, params=params)

                data = response.json()

                # Verificar erro na resposta
                if "error" in data:
                    error = data["error"]
                    code = error.get("code", 0)
                    subcode = error.get("error_subcode", 0)
                    message = error.get("message", "Erro desconhecido")
                    trace_id = error.get("fbtrace_id", "")

                    # Rate limit: codigos 4 (app), 32 (page), 80004 (API)
                    if code in (4, 32) or subcode == 2207051:
                        if attempt < max_retries:
                            wait = 60 * (attempt + 1)  # backoff: 60s, 120s
                            logger.warning(
                                f"Rate limit atingido (code={code}), "
                                f"aguardando {wait}s (tentativa {attempt + 1}/{max_retries})"
                            )
                            await asyncio.sleep(wait)
                            continue
                        raise InstagramRateLimitError(message, code, subcode, trace_id)

                    # OAuth: token expirado ou invalido
                    if code == 190:
                        raise InstagramAPIError(
                            f"Token invalido ou expirado: {message}", code, subcode, trace_id
                        )

                    raise InstagramAPIError(message, code, subcode, trace_id)

                response.raise_for_status()
                return data

            except httpx.HTTPStatusError as e:
                logger.error(f"HTTP {e.response.status_code} em {method} {endpoint}")
                raise InstagramAPIError(f"HTTP {e.response.status_code}: {str(e)}")

            except httpx.RequestError as e:
                logger.error(f"Erro de conexao em {method} {endpoint}: {e}")
                if attempt < max_retries:
                    await asyncio.sleep(5)
                    continue
                raise InstagramAPIError(f"Erro de conexao: {str(e)}")

        # Nunca deve chegar aqui, mas por seguranca
        raise InstagramAPIError("Maximo de retries excedido")

    # ── Utilidades ─────────────────────────────────────────────────

    @staticmethod
    def _truncate_caption(caption: str) -> str:
        """Trunca caption para o limite do Instagram (2200 chars)."""
        max_len = config.INSTAGRAM_MAX_CAPTION_LENGTH
        if len(caption) > max_len:
            logger.warning(f"Caption truncada de {len(caption)} para {max_len} chars")
            return caption[:max_len - 3] + "..."
        return caption

    @staticmethod
    def get_public_image_url(image_path: str) -> str:
        """Converte path local para URL publica acessivel pela Graph API.

        Ordem de prioridade:
        1. Se CDN base URL configurada, usa CDN
        2. Senao, usa URL local da API (requer ngrok/tunel para producao)

        Args:
            image_path: Path absoluto ou nome do arquivo

        Returns:
            URL publica da imagem
        """
        filename = Path(image_path).name
        cdn_base = os.getenv("INSTAGRAM_CDN_BASE", "")

        if cdn_base:
            url = f"{cdn_base.rstrip('/')}/{filename}"
            logger.debug(f"URL via CDN: {url}")
            return url

        # Fallback: URL local da API
        api_base = os.getenv("INSTAGRAM_API_PUBLIC_URL", "http://localhost:8000")
        url = f"{api_base.rstrip('/')}/drive/images/{filename}"
        logger.warning(
            f"Usando URL local para imagem: {url} — "
            "Para publicar no Instagram, configure INSTAGRAM_CDN_BASE ou "
            "INSTAGRAM_API_PUBLIC_URL (ex: URL do ngrok) no .env"
        )
        return url
