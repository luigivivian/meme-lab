"""Log sanitizer — filtra dados sensiveis de todas as mensagens de log.

Implementa logging.Filter que intercepta records antes de qualquer handler.
Mascara: GOOGLE_API_KEY, BLUESKY_APP_PASSWORD, INSTAGRAM_ACCESS_TOKEN,
DATABASE_URL password, padroes genericos (sk-*, ghp_*, Bearer tokens).

Formato: ***{ultimos 4 chars} (per D-08).
"""
import logging
import os
import re
import urllib.parse


class SensitiveDataFilter(logging.Filter):
    """Filtra dados sensiveis de todas as mensagens de log."""

    def __init__(self):
        super().__init__()
        self._patterns = self._build_patterns()

    def _build_patterns(self) -> list[tuple[re.Pattern, str]]:
        patterns = []
        # D-07: Valores de env vars conhecidas
        for key in ["GOOGLE_API_KEY", "BLUESKY_APP_PASSWORD", "INSTAGRAM_ACCESS_TOKEN",
                     "GOOGLE_API_KEY_PAID"]:
            value = os.getenv(key, "")
            if value and len(value) > 4:
                escaped = re.escape(value)
                patterns.append((re.compile(escaped), f"***{value[-4:]}"))

        # D-07: DATABASE_URL password
        db_url = os.getenv("DATABASE_URL", "")
        if ":" in db_url and "@" in db_url:
            try:
                clean_url = db_url
                for driver in ["+aiomysql", "+aiosqlite", "+pymysql"]:
                    clean_url = clean_url.replace(driver, "")
                parsed = urllib.parse.urlparse(clean_url)
                if parsed.password and len(parsed.password) > 4:
                    escaped_pw = re.escape(parsed.password)
                    patterns.append((re.compile(escaped_pw), f"***{parsed.password[-4:]}"))
                elif parsed.password:
                    escaped_pw = re.escape(parsed.password)
                    patterns.append((re.compile(escaped_pw), "***"))
            except Exception:
                pass

        # D-07: Padroes genericos
        patterns.append((re.compile(r'sk-[A-Za-z0-9]{20,}'), '***'))
        patterns.append((re.compile(r'ghp_[A-Za-z0-9]{36,}'), '***'))
        patterns.append((re.compile(r'Bearer\s+[A-Za-z0-9._-]{20,}'), 'Bearer ***'))

        return patterns

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            for pattern, replacement in self._patterns:
                record.msg = pattern.sub(replacement, record.msg)
        if record.args:
            if isinstance(record.args, dict):
                record.args = {k: self._sanitize(v) for k, v in record.args.items()}
            elif isinstance(record.args, tuple):
                record.args = tuple(self._sanitize(a) for a in record.args)
        return True

    def _sanitize(self, value):
        if isinstance(value, str):
            for pattern, replacement in self._patterns:
                value = pattern.sub(replacement, value)
        return value


def setup_log_sanitizer():
    """Instala o filtro no root logger. Chamar ANTES de qualquer log."""
    root = logging.getLogger()
    root.addFilter(SensitiveDataFilter())
