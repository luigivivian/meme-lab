import argparse
import logging
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def setup_logging(verbose: bool = False):
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def main():
    parser = argparse.ArgumentParser(
        description="Clip-Flow: Pipeline automático de conteúdo Gandalf Sincero"
    )
    parser.add_argument(
        "--mode",
        choices=["once", "schedule", "agents"],
        default="once",
        help="Modo: 'once' (sequencial), 'schedule' (agendado), 'agents' (multi-agente paralelo)",
    )
    parser.add_argument(
        "--count",
        type=int,
        default=None,
        help="Quantidade de imagens a gerar por execução",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=None,
        help="Intervalo em horas entre execuções (modo schedule)",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Saída detalhada (debug logs)",
    )
    parser.add_argument(
        "--comfyui",
        action="store_true",
        help="Gerar backgrounds via ComfyUI local (requer servidor rodando)",
    )
    parser.add_argument(
        "--no-comfyui",
        action="store_true",
        help="Forçar uso de backgrounds estáticos (ignora config)",
    )

    args = parser.parse_args()
    setup_logging(args.verbose)

    from config import PIPELINE_IMAGES_PER_RUN, PIPELINE_INTERVAL_HOURS

    images_per_run = args.count or PIPELINE_IMAGES_PER_RUN
    interval_hours = args.interval or PIPELINE_INTERVAL_HOURS

    # Determinar modo ComfyUI
    use_comfyui = None  # usa config padrao
    if args.comfyui:
        use_comfyui = True
    elif args.no_comfyui:
        use_comfyui = False

    if args.mode == "once":
        from src.pipeline.orchestrator import PipelineOrchestrator

        orchestrator = PipelineOrchestrator(
            images_per_run=images_per_run,
            use_comfyui=use_comfyui,
        )
        result = orchestrator.run()

        print(f"\n{'=' * 50}")
        print("Resultado do pipeline:")
        print(f"  Trends coletados:    {result.trends_fetched}")
        print(f"  Temas analisados:    {result.topics_analyzed}")
        print(f"  Imagens geradas:     {result.images_generated}")
        if result.content:
            print("\nConteúdo gerado:")
            for c in result.content:
                print(f"  - {c.phrase[:60]}...")
                print(f"    -> {c.image_path}")
        if result.errors:
            print(f"\nErros ({len(result.errors)}):")
            for err in result.errors:
                print(f"  ! {err}")
        print(f"{'=' * 50}")

    elif args.mode == "agents":
        import asyncio
        from src.pipeline.async_orchestrator import AsyncPipelineOrchestrator

        orchestrator = AsyncPipelineOrchestrator(
            images_per_run=images_per_run,
            use_comfyui=use_comfyui,
        )
        result = asyncio.run(orchestrator.run())

        print(f"\n{'=' * 50}")
        print("Resultado do pipeline multi-agente:")
        print(f"  Trends coletados:    {result.trends_fetched}")
        print(f"  Eventos enfileirados:{result.trend_events_queued}")
        print(f"  Work orders:         {result.work_orders_emitted}")
        print(f"  Imagens geradas:     {result.images_generated}")
        print(f"  Pacotes produzidos:  {result.packages_produced}")
        if result.content:
            print("\nConteudo gerado:")
            for pkg in result.content:
                print(f"  - {pkg.phrase[:60]}...")
                print(f"    -> {pkg.image_path}")
                if pkg.caption:
                    print(f"    Legenda: {pkg.caption[:80]}...")
                if pkg.hashtags:
                    print(f"    Hashtags: {' '.join(pkg.hashtags[:5])}...")
                print(f"    Quality: {pkg.quality_score:.2f}")
        if result.errors:
            print(f"\nErros ({len(result.errors)}):")
            for err in result.errors:
                print(f"  ! {err}")
        print(f"{'=' * 50}")

    elif args.mode == "schedule":
        from src.pipeline.scheduler import SchedulerRunner

        runner = SchedulerRunner(
            interval_hours=interval_hours,
            images_per_run=images_per_run,
            run_immediately=True,
            use_comfyui=use_comfyui,
        )
        runner.start()


if __name__ == "__main__":
    main()
