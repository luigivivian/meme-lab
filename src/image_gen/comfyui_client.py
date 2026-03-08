"""Cliente REST/WebSocket para comunicacao com o servidor ComfyUI local.

Envia workflows parametrizados, acompanha progresso via WebSocket,
e recupera imagens geradas. Suporta txt2img (LoRA) e img2img (referencia).
"""

import json
import uuid
import logging
import random
import time
from pathlib import Path

import requests
import websocket

logger = logging.getLogger("clip-flow.comfyui")


class ComfyUIClient:
    """Cliente para o servidor ComfyUI rodando localmente."""

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 8188,
        timeout: int = 300,
        lora_strength: float = 0.85,
        sampling_steps: int = 25,
        guidance: float = 4.0,
        img2img_denoise: float = 0.55,
    ):
        self.server_address = f"{host}:{port}"
        self.client_id = str(uuid.uuid4())
        self.timeout = timeout
        self.lora_strength = lora_strength
        self.sampling_steps = sampling_steps
        self.guidance = guidance
        self.img2img_denoise = img2img_denoise

        workflows_dir = Path(__file__).parent / "workflows"
        self.workflow_path = workflows_dir / "flux_mago_lora.json"
        self.img2img_workflow_path = workflows_dir / "flux_img2img.json"

    def is_available(self) -> bool:
        """Verifica se o servidor ComfyUI esta rodando."""
        try:
            r = requests.get(
                f"http://{self.server_address}/system_stats",
                timeout=5,
            )
            return r.status_code == 200
        except (requests.ConnectionError, requests.Timeout):
            return False

    def generate_background(self, prompt_text: str, output_path: str) -> str | None:
        """Gera uma imagem de background usando o workflow Flux + LoRA (txt2img).

        Args:
            prompt_text: Prompt completo para geracao de imagem.
            output_path: Caminho onde salvar a imagem gerada.

        Returns:
            Caminho da imagem gerada, ou None em caso de falha.
        """
        workflow = self._load_workflow(prompt_text)
        return self._execute_workflow(workflow, output_path)

    def generate_img2img(
        self,
        prompt_text: str,
        reference_image_path: str,
        output_path: str,
    ) -> str | None:
        """Gera uma variacao de imagem baseada em referencia (img2img).

        Usa uma imagem de referencia como base e aplica o prompt para
        gerar variacoes que mantem o estilo e proporcoes do original.

        Args:
            prompt_text: Prompt descrevendo a variacao desejada.
            reference_image_path: Caminho da imagem de referencia local.
            output_path: Caminho onde salvar a imagem gerada.

        Returns:
            Caminho da imagem gerada, ou None em caso de falha.
        """
        # Upload da referencia para o ComfyUI
        uploaded_name = self._upload_image(reference_image_path)
        if not uploaded_name:
            return None

        workflow = self._load_img2img_workflow(prompt_text, uploaded_name)
        return self._execute_workflow(workflow, output_path)

    def _upload_image(self, image_path: str) -> str | None:
        """Faz upload de imagem para o diretorio input do ComfyUI.

        Pre-redimensiona para 1080x1360 com Pillow antes do upload
        para evitar OOM no ImageScale do ComfyUI com lowvram.

        Returns:
            Nome do arquivo no servidor, ou None em caso de falha.
        """
        from PIL import Image
        import io

        path = Path(image_path)
        if not path.exists():
            logger.error(f"Imagem de referencia nao encontrada: {image_path}")
            return None

        try:
            # Pre-redimensionar para 1080x1360 (target do workflow)
            img = Image.open(path).convert("RGB")
            target_w, target_h = 1080, 1360

            if img.size != (target_w, target_h):
                # Crop centralizado para manter proporcao 4:5
                src_ratio = img.width / img.height
                target_ratio = target_w / target_h

                if src_ratio > target_ratio:
                    new_w = int(img.height * target_ratio)
                    left = (img.width - new_w) // 2
                    img = img.crop((left, 0, left + new_w, img.height))
                elif src_ratio < target_ratio:
                    new_h = int(img.width / target_ratio)
                    top = (img.height - new_h) // 2
                    img = img.crop((0, top, img.width, top + new_h))

                img = img.resize((target_w, target_h), Image.LANCZOS)
                logger.info(f"Referencia redimensionada para {target_w}x{target_h}")

            # Converter para bytes PNG em memoria
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            buf.seek(0)

            upload_name = f"ref_{path.stem}.png"
            files = {"image": (upload_name, buf, "image/png")}
            data = {"overwrite": "true"}
            response = requests.post(
                f"http://{self.server_address}/upload/image",
                files=files,
                data=data,
                timeout=30,
            )

            if response.status_code == 200:
                result = response.json()
                name = result.get("name", upload_name)
                logger.info(f"Referencia uploaded para ComfyUI: {name}")
                return name
            else:
                logger.error(f"Upload falhou (HTTP {response.status_code}): {response.text}")
                return None

        except Exception as e:
            logger.error(f"Erro no upload da referencia: {e}")
            return None

    def _execute_workflow(self, workflow: dict, output_path: str) -> str | None:
        """Executa workflow no ComfyUI via WebSocket e recupera resultado."""
        ws = websocket.WebSocket()
        ws.settimeout(self.timeout)
        try:
            ws.connect(f"ws://{self.server_address}/ws?clientId={self.client_id}")
        except Exception as e:
            logger.error(f"Falha ao conectar WebSocket ComfyUI: {e}")
            return None

        try:
            result = self._queue_prompt(workflow)
            if "prompt_id" not in result:
                logger.error(f"Erro ao enfileirar prompt: {result}")
                return None

            prompt_id = result["prompt_id"]
            logger.info(f"Prompt enfileirado no ComfyUI: {prompt_id}")

            if not self._track_progress(ws, prompt_id):
                return None

            return self._retrieve_image(prompt_id, output_path)

        except Exception as e:
            logger.error(f"Erro durante geracao ComfyUI: {e}")
            return None
        finally:
            ws.close()

    def _load_workflow(self, prompt_text: str) -> dict:
        """Carrega workflow txt2img (LoRA) e substitui campos parametrizados."""
        with open(self.workflow_path, "r", encoding="utf-8") as f:
            workflow = json.load(f)

        workflow["5"]["inputs"]["text"] = prompt_text
        workflow["11"]["inputs"]["noise_seed"] = random.randint(0, 2**32 - 1)
        workflow["15"]["inputs"]["filename_prefix"] = f"mago_{int(time.time())}"

        workflow["2"]["inputs"]["strength_model"] = self.lora_strength
        workflow["2"]["inputs"]["strength_clip"] = self.lora_strength
        workflow["6"]["inputs"]["guidance"] = self.guidance
        workflow["10"]["inputs"]["steps"] = self.sampling_steps

        return workflow

    def _load_img2img_workflow(self, prompt_text: str, reference_name: str) -> dict:
        """Carrega workflow img2img e substitui campos parametrizados."""
        with open(self.img2img_workflow_path, "r", encoding="utf-8") as f:
            workflow = json.load(f)

        # Prompt de texto
        workflow["5"]["inputs"]["text"] = prompt_text

        # Imagem de referencia (nome no servidor ComfyUI)
        workflow["16"]["inputs"]["image"] = reference_name

        # Seed aleatoria
        workflow["11"]["inputs"]["noise_seed"] = random.randint(0, 2**32 - 1)

        # Prefixo de saida
        workflow["15"]["inputs"]["filename_prefix"] = f"mago_i2i_{int(time.time())}"

        # Parametros configuraveis
        workflow["6"]["inputs"]["guidance"] = self.guidance
        workflow["10"]["inputs"]["steps"] = self.sampling_steps
        workflow["10"]["inputs"]["denoise"] = self.img2img_denoise

        return workflow

    def _queue_prompt(self, workflow: dict) -> dict:
        """Envia workflow para a fila de execucao do ComfyUI."""
        data = {"prompt": workflow, "client_id": self.client_id}
        response = requests.post(
            f"http://{self.server_address}/prompt",
            json=data,
            headers={"Content-Type": "application/json"},
        )
        return response.json()

    def _track_progress(self, ws, prompt_id: str) -> bool:
        """Monitora progresso da geracao via WebSocket."""
        while True:
            try:
                raw = ws.recv()
                if isinstance(raw, bytes):
                    continue

                msg = json.loads(raw)
                msg_type = msg.get("type", "")

                if msg_type == "progress":
                    step = msg["data"]["value"]
                    total = msg["data"]["max"]
                    if step % 5 == 0 or step == total:
                        logger.debug(f"ComfyUI progresso: {step}/{total}")

                elif msg_type == "executing":
                    node = msg["data"].get("node")
                    if node is None and msg["data"].get("prompt_id") == prompt_id:
                        logger.info("Geracao ComfyUI concluida")
                        return True

                elif msg_type == "execution_error":
                    error_data = msg.get("data", {})
                    logger.error(f"Erro na execucao ComfyUI: {error_data}")
                    return False

                elif msg_type == "execution_cached":
                    logger.debug("Nos em cache reutilizados")

            except websocket.WebSocketTimeoutException:
                logger.error(f"Timeout ({self.timeout}s) aguardando geracao ComfyUI")
                return False
            except Exception as e:
                logger.error(f"Erro no WebSocket ComfyUI: {e}")
                return False

    def _retrieve_image(self, prompt_id: str, output_path: str) -> str | None:
        """Recupera a imagem gerada do historico do ComfyUI."""
        try:
            history = requests.get(
                f"http://{self.server_address}/history/{prompt_id}",
                timeout=30,
            ).json()
        except Exception as e:
            logger.error(f"Falha ao buscar historico: {e}")
            return None

        if prompt_id not in history:
            logger.error("Prompt nao encontrado no historico do ComfyUI")
            return None

        outputs = history[prompt_id].get("outputs", {})
        for node_id in outputs:
            if "images" not in outputs[node_id]:
                continue

            image_info = outputs[node_id]["images"][0]
            try:
                image_data = requests.get(
                    f"http://{self.server_address}/view",
                    params={
                        "filename": image_info["filename"],
                        "subfolder": image_info.get("subfolder", ""),
                        "type": image_info.get("type", "output"),
                    },
                    timeout=30,
                ).content

                Path(output_path).parent.mkdir(parents=True, exist_ok=True)
                with open(output_path, "wb") as f:
                    f.write(image_data)

                logger.info(f"Background salvo: {output_path}")
                return output_path

            except Exception as e:
                logger.error(f"Falha ao baixar imagem do ComfyUI: {e}")
                return None

        logger.error("Nenhuma imagem encontrada na saida do ComfyUI")
        return None
