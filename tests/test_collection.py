import copy
import tempfile
import unittest
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from currency_judge.collection import SYMBOLS, Store, collect_once, parse_quotes


NOW = datetime(2026, 9, 21, 1, 0, 10, tzinfo=UTC)


def payload():
    return {"status": 0, "data": [
        {"symbol": symbol, "bid": "150.001", "ask": "150.004",
         "timestamp": "2026-09-21T01:00:09Z", "status": "OPEN"}
        for symbol in SYMBOLS
    ]}


class ParsingTests(unittest.TestCase):
    def test_prices_are_exact_and_times_are_utc(self):
        quote = parse_quotes(payload(), NOW)[0]
        self.assertEqual(quote.mid, Decimal("150.0025"))
        self.assertEqual(quote.quality, "VALID")
        self.assertTrue(quote.price_time.endswith("+00:00"))

    def test_unusable_observations_are_flagged(self):
        for timestamp, status, expected in [
            ("2026-09-21T01:00:09Z", "CLOSE", "CLOSED"),
            ("2026-09-21T01:00:11Z", "OPEN", "FUTURE"),
            ("2026-09-21T00:59:54Z", "OPEN", "STALE"),
            ("2026-09-21T00:59:55Z", "OPEN", "VALID"),
        ]:
            with self.subTest(expected=expected):
                data = payload()
                data["data"][0].update(timestamp=timestamp, status=status)
                self.assertEqual(parse_quotes(data, NOW)[0].quality, expected)

    def test_invalid_prices_and_naive_timestamps_are_rejected(self):
        for changes in [{"bid": "NaN"}, {"ask": "Infinity"}, {"bid": "0"},
                        {"bid": "151"}, {"timestamp": "2026-09-21T01:00:09"},
                        {"status": "UNKNOWN"}]:
            with self.subTest(changes=changes):
                data = payload()
                data["data"][0].update(changes)
                with self.assertRaises(ValueError):
                    parse_quotes(data, NOW)
        with self.assertRaises(ValueError):
            parse_quotes(payload(), NOW.replace(tzinfo=None))

    def test_missing_duplicate_and_failed_response_are_rejected(self):
        missing = payload()
        missing["data"].pop()
        duplicate = payload()
        duplicate["data"].append(copy.deepcopy(duplicate["data"][0]))
        for data in [missing, duplicate, {"status": 1, "data": []}]:
            with self.assertRaises(ValueError):
                parse_quotes(data, NOW)


class StorageTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.path = str(Path(self.directory.name) / "quotes.sqlite3")
        self.store = Store(self.path)

    def tearDown(self):
        self.store.close()
        self.directory.cleanup()

    def test_collection_retains_original_and_survives_reopen(self):
        data = payload()
        collect_once(self.store, lambda: (data, NOW))
        data["data"][0]["bid"] = "150.002"
        collect_once(self.store, lambda: (data, NOW))
        self.store.close()
        self.store = Store(self.path)
        rows = self.store.connection.execute(
            "SELECT bid FROM quotes WHERE symbol='USD_JPY' ORDER BY id"
        ).fetchall()
        self.assertEqual(rows, [("150.001",), ("150.002",)])

    def test_invalid_batch_records_failure_without_partial_quotes(self):
        data = payload()
        data["data"][-1]["ask"] = "-1"
        with self.assertRaises(ValueError):
            collect_once(self.store, lambda: (data, NOW))
        self.assertEqual(self.store.connection.execute("SELECT count(*) FROM quotes").fetchone()[0], 0)
        self.assertEqual(self.store.connection.execute("SELECT status FROM collection_runs").fetchone()[0], "ERROR")

    def test_network_failure_is_recorded_and_next_collection_recovers(self):
        def unavailable():
            raise TimeoutError("test timeout")
        with self.assertRaises(TimeoutError):
            collect_once(self.store, unavailable)
        collect_once(self.store, lambda: (payload(), NOW))
        self.assertEqual(self.store.connection.execute(
            "SELECT status FROM collection_runs ORDER BY id"
        ).fetchall(), [("ERROR",), ("OK",)])


if __name__ == "__main__":
    unittest.main()
