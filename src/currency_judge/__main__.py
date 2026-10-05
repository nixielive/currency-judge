import argparse
import logging
import time

from .collection import Store, collect_once


def main() -> int:
    parser = argparse.ArgumentParser(description="Collect public GMO FX quotes (no credentials required)")
    parser.add_argument("--db", default="data/currency_judge.sqlite3")
    parser.add_argument("--once", action="store_true", help="Fetch one batch and exit")
    parser.add_argument("--interval", type=float, default=10, help="Polling interval in seconds (minimum 10)")
    args = parser.parse_args()
    if not 10 <= args.interval <= 3600:
        parser.error("--interval must be between 10 and 3600 seconds")
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
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
