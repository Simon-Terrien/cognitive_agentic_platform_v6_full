import logging


def configure_logging(level: str = 'INFO', loki_enabled: bool = False) -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format='%(asctime)s [%(levelname)s] %(name)s :: %(message)s',
    )
    if loki_enabled:
        from app.core.loki import LokiLogHandler, get_loki_sink

        root = logging.getLogger()
        if not any(isinstance(handler, LokiLogHandler) for handler in root.handlers):
            root.addHandler(LokiLogHandler(get_loki_sink()))
