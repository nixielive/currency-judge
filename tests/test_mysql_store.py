import unittest
from unittest.mock import MagicMock

from currency_judge.mysql_store import MySQLStore
from test_collection import NOW, payload
from currency_judge.collection import parse_quotes


class MySQLTransactionTests(unittest.TestCase):
    def setUp(self):
        self.store = MySQLStore.__new__(MySQLStore)
        self.store.connection = MagicMock()
        self.cursor = self.store.connection.cursor.return_value.__enter__.return_value
        self.cursor.lastrowid = 42

    def test_failed_quote_insert_rolls_back_run_and_quotes(self):
        self.cursor.executemany.side_effect = RuntimeError("write failed")
        with self.assertRaises(RuntimeError):
            self.store.save(NOW, payload(), parse_quotes(payload(), NOW))
        self.store.connection.rollback.assert_called_once()
        self.store.connection.commit.assert_not_called()

    def test_commit_failure_is_rolled_back_and_propagated(self):
        self.store.connection.commit.side_effect = RuntimeError("commit failed")
        with self.assertRaises(RuntimeError):
            self.store.save(NOW, payload(), parse_quotes(payload(), NOW))
        self.store.connection.rollback.assert_called_once()

    def test_failed_error_write_rolls_back(self):
        self.cursor.execute.side_effect = RuntimeError("write failed")
        with self.assertRaises(RuntimeError):
            self.store.record_error(NOW, "timeout")
        self.store.connection.rollback.assert_called_once()
        self.store.connection.commit.assert_not_called()

    def test_decimal_and_timezone_values_are_preserved(self):
        self.assertEqual(self.store.save(NOW, payload(), parse_quotes(payload(), NOW)), 42)
        rows = self.cursor.executemany.call_args.args[1]
        self.assertEqual(rows[0][3:6], ("150.001", "150.004", "150.0025"))
        self.assertTrue(rows[0][6].endswith("+00:00"))
        self.assertEqual(len(rows), 6)
        self.store.connection.commit.assert_called_once()

    def test_unavailable_database_does_not_start_or_retry_batch(self):
        self.store.connection.ping.side_effect = ConnectionError("database unavailable")
        with self.assertRaises(ConnectionError):
            self.store.save(NOW, payload(), parse_quotes(payload(), NOW))
        self.store.connection.begin.assert_not_called()
        self.cursor.execute.assert_not_called()
        self.store.connection.commit.assert_not_called()

    def test_next_batch_can_resume_after_connection_recovers(self):
        self.store.connection.ping.side_effect = [ConnectionError("database unavailable"), None]
        with self.assertRaises(ConnectionError):
            self.store.save(NOW, payload(), parse_quotes(payload(), NOW))
        self.assertEqual(self.store.save(NOW, payload(), parse_quotes(payload(), NOW)), 42)
        self.store.connection.begin.assert_called_once()
        self.store.connection.commit.assert_called_once()
