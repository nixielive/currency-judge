import argparse
import logging
import time

from .collection import Store, collect_once


def main() -> int:
    parser = argparse.ArgumentParser(description="Collect public GMO FX quotes (no credentials required)")
    storage = parser.add_mutually_exclusive_group()
    storage.add_argument("--db", default="data/currency_judge.sqlite3")
    storage.add_argument("--mysql-config", help="MySQL client option file ([client] section)")
    parser.add_argument("--once", action="store_true", help="Fetch one batch and exit")
    parser.add_argument("--interval", type=float, default=10, help="Polling interval in seconds (minimum 10)")
    args = parser.parse_args()
    if not 10 <= args.interval <= 3600:
        parser.error("--interval must be between 10 and 3600 seconds")
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    if args.mysql_config:
        from .mysql_store import MySQLStore
        store = MySQLStore(args.mysql_config)
    else:
        store = Store(args.db)
    failures = 0
    try:
        while True:
            try:
                quotes = collect_once(store)
                failures = 0
                logging.info("Saved %d quotes (%d VALID)", len(quotes), sum(q.quality == "VALID" for q in quotes))
                if args.once:
                    return 0
            except Exception as exc:
                failures += 1
                logging.error("Collection failed: %s", exc)
                if args.once:
                    return 1
            time.sleep(max(args.interval, min(300, 10 * 2 ** min(failures, 5))))
    except KeyboardInterrupt:
        logging.info("Collector stopped")
        return 0
    finally:
        store.close()


if __name__ == "__main__":
    raise SystemExit(main())
