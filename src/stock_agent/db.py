from collections.abc import Iterator
from contextlib import contextmanager

import psycopg
from psycopg import Connection

from stock_agent.config import get_settings


@contextmanager
def get_connection() -> Iterator[Connection]:
    settings = get_settings()
    with psycopg.connect(settings.resolved_database_url, connect_timeout=1) as conn:
        yield conn
