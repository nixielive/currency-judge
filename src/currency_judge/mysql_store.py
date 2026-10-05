"""MySQL observation storage, with atomic, append-only collection batches."""

import json
from datetime import UTC, datetime
from pathlib import Path

from .collection import Quote, utc_text


class MySQLStore:
    def __init__(self, config_path: str):
        import pymysql

        if not Path(config_path).is_file():
            raise ValueError("MySQL client configuration file does not exist")
        self.connection = pymysql.connect(
            read_default_file=str(Path(config_path).resolve()),
            charset="utf8mb4", autocommit=False,
            connect_timeout=10, read_timeout=15, write_timeout=15,
            init_command="SET time_zone = '+00:00'",
        )

    def close(self):
        self.connection.close()

    def save(self, started: datetime, payload: dict, quotes: list[Quote]) -> int:
        # Reconnect before starting a new batch; never retry a partial transaction.
        self.connection.ping(reconnect=True)
        try:
            self.connection.begin()
            with self.connection.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO collection_runs(started_at, completed_at, status, payload_json) VALUES (%s, %s, 'OK', %s)",
                    (utc_text(started), utc_text(datetime.now(UTC)), json.dumps(payload)),
                )
                run_id = cursor.lastrowid
                cursor.executemany(
                    "INSERT INTO quotes(run_id, provider, symbol, bid, ask, mid, price_time, received_at, market_status, quality) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                    [(run_id, "gmo", q.symbol, str(q.bid), str(q.ask), str(q.mid),
                      q.price_time, q.received_at, q.market_status, q.quality) for q in quotes],
                )
            self.connection.commit()
            return run_id
        except Exception:
            self.connection.rollback()
            raise

    def record_error(self, started: datetime, error: str):
        self.connection.ping(reconnect=True)
        try:
            self.connection.begin()
            with self.connection.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO collection_runs(started_at, completed_at, status, error) VALUES (%s, %s, 'ERROR', %s)",
                    (utc_text(started), utc_text(datetime.now(UTC)), error),
                )
            self.connection.commit()
        except Exception:
            self.connection.rollback()
            raise
