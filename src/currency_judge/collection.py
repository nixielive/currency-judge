"""Market observations: immutable inputs, independent of UI and prediction."""

import json
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from urllib.request import Request, urlopen

ENDPOINT = "https://forex-api.coin.z.com/public/v1/ticker"
SYMBOLS = ("USD_JPY", "EUR_USD", "EUR_JPY", "GBP_USD", "GBP_JPY", "AUD_USD")


def utc_text(value: datetime) -> str:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("Timezone-aware timestamp required")
    return value.astimezone(UTC).isoformat(timespec="microseconds")


@dataclass(frozen=True)
class Quote:
    symbol: str
    bid: Decimal
    ask: Decimal
    price_time: str
    received_at: str
    market_status: str
    quality: str

    @property
    def mid(self) -> Decimal:
        return (self.bid + self.ask) / Decimal(2)


def parse_quotes(payload: dict, received_at: datetime, max_age: float = 15) -> list[Quote]:
    """Reject malformed batches; retain closed/stale observations for audit."""
    received = utc_text(received_at)
    if payload.get("status") != 0 or not isinstance(payload.get("data"), list):
        raise ValueError("Invalid or unsuccessful GMO ticker response")
    quotes = []
    seen = set()
    for item in payload["data"]:
        symbol = item.get("symbol")
        if symbol not in SYMBOLS:
            continue
        if symbol in seen:
            raise ValueError(f"Duplicate symbol: {symbol}")
        seen.add(symbol)
        try:
            bid, ask = Decimal(item["bid"]), Decimal(item["ask"])
            price_time = datetime.fromisoformat(item["timestamp"].replace("Z", "+00:00"))
            price_text = utc_text(price_time)
            status = item["status"]
        except (KeyError, TypeError, ValueError, InvalidOperation) as exc:
            raise ValueError(f"Malformed quote: {symbol}") from exc
        if not bid.is_finite() or not ask.is_finite() or bid <= 0 or ask < bid:
            raise ValueError(f"Invalid bid/ask: {symbol}")
        if status not in ("OPEN", "CLOSE"):
            raise ValueError(f"Unknown market status: {status}")
        age = (received_at - price_time).total_seconds()
        quality = "VALID"
        if status == "CLOSE":
            quality = "CLOSED"
        elif age < 0:
            quality = "FUTURE"
        elif age > max_age:
            quality = "STALE"
        quotes.append(Quote(symbol, bid, ask, price_text, received, status, quality))
    missing = set(SYMBOLS) - seen
    if missing:
        raise ValueError(f"Missing symbols: {', '.join(sorted(missing))}")
    return quotes


def fetch_ticker() -> tuple[dict, datetime]:
    request = Request(ENDPOINT, headers={"User-Agent": "currency-judge/0.1"})
    with urlopen(request, timeout=10) as response:
        raw = response.read()
        received_at = datetime.now(UTC)
    return json.loads(raw), received_at


class Store:
    def __init__(self, path: str):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(path, timeout=10)
        self.connection.execute("PRAGMA foreign_keys = ON")
        self.connection.execute("PRAGMA journal_mode = WAL")
        self.connection.executescript("""
            CREATE TABLE IF NOT EXISTS collection_runs (
                id INTEGER PRIMARY KEY,
                started_at TEXT NOT NULL,
                completed_at TEXT NOT NULL,
                status TEXT NOT NULL CHECK(status IN ('OK', 'ERROR')),
                error TEXT,
                payload_json TEXT
            );
            CREATE TABLE IF NOT EXISTS quotes (
                id INTEGER PRIMARY KEY,
                run_id INTEGER NOT NULL REFERENCES collection_runs(id),
                provider TEXT NOT NULL,
                symbol TEXT NOT NULL,
                bid TEXT NOT NULL,
                ask TEXT NOT NULL,
                mid TEXT NOT NULL,
                price_time TEXT NOT NULL,
                received_at TEXT NOT NULL,
                market_status TEXT NOT NULL,
                quality TEXT NOT NULL,
                UNIQUE(run_id, symbol)
            );
            CREATE INDEX IF NOT EXISTS quotes_symbol_time ON quotes(symbol, received_at);
        """)

    def close(self):
        self.connection.close()

    def save(self, started: datetime, payload: dict, quotes: list[Quote]) -> int:
        with self.connection:
            cursor = self.connection.execute(
                "INSERT INTO collection_runs(started_at, completed_at, status, payload_json) VALUES (?, ?, 'OK', ?)",
                (utc_text(started), utc_text(datetime.now(UTC)), json.dumps(payload)),
            )
            run_id = cursor.lastrowid
            self.connection.executemany(
                "INSERT INTO quotes(run_id, provider, symbol, bid, ask, mid, price_time, received_at, market_status, quality) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                [(run_id, "gmo", q.symbol, str(q.bid), str(q.ask), str(q.mid),
                  q.price_time, q.received_at, q.market_status, q.quality) for q in quotes],
            )
        return run_id

    def record_error(self, started: datetime, error: str):
        with self.connection:
            self.connection.execute(
                "INSERT INTO collection_runs(started_at, completed_at, status, error) VALUES (?, ?, 'ERROR', ?)",
                (utc_text(started), utc_text(datetime.now(UTC)), error),
            )


def collect_once(store: Store, fetch=fetch_ticker) -> list[Quote]:
    started = datetime.now(UTC)
    try:
        payload, received = fetch()
        quotes = parse_quotes(payload, received)
        store.save(started, payload, quotes)
        return quotes
    except Exception as exc:
        store.record_error(started, f"{type(exc).__name__}: {exc}")
        raise
