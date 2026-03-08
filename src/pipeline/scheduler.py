import logging

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.interval import IntervalTrigger

from src.pipeline.orchestrator import PipelineOrchestrator

logger = logging.getLogger("clip-flow.scheduler")


class SchedulerRunner:
    """Executa o pipeline em intervalos configuráveis via APScheduler."""

    def __init__(
        self,
        interval_hours: int = 6,
        images_per_run: int = 5,
        run_immediately: bool = True,
        use_comfyui: bool | None = None,
    ):
        self.interval_hours = interval_hours
        self.images_per_run = images_per_run
        self.run_immediately = run_immediately
        self.orchestrator = PipelineOrchestrator(
            images_per_run=images_per_run,
            use_comfyui=use_comfyui,
        )
        self.scheduler = BlockingScheduler()

    def _run_job(self):
        """Job executado pelo scheduler."""
        logger.info("Execução agendada iniciando...")
        try:
            result = self.orchestrator.run()
            logger.info(f"Execução completa: {result.images_generated} imagens geradas")
        except Exception as e:
            logger.error(f"Execução agendada falhou: {e}")

    def start(self):
        """Inicia o scheduler. Bloqueia a thread atual."""
        logger.info(f"Iniciando scheduler (intervalo: {self.interval_hours}h)")

        self.scheduler.add_job(
            self._run_job,
            trigger=IntervalTrigger(hours=self.interval_hours),
            id="content_pipeline",
            name="Clip-Flow Content Pipeline",
            replace_existing=True,
        )

        if self.run_immediately:
            logger.info("Executando pipeline imediatamente...")
            self._run_job()

        try:
            logger.info("Scheduler rodando. Pressione Ctrl+C para parar.")
            self.scheduler.start()
        except (KeyboardInterrupt, SystemExit):
            logger.info("Scheduler parado.")
            self.scheduler.shutdown()
