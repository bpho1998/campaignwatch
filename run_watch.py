"""
Run both watchers and rebuild feed.xml with any new matches.

Usage:
    FEC_API_KEY=your_key python3 run_watch.py            # both sources
    FEC_API_KEY=your_key python3 run_watch.py --fec-only  # skip the slow CalAccess bulk download
    python3 run_watch.py --calaccess-only

Intended to run on a schedule (cron / systemd timer / GitHub Actions):
    */5  * * * *  cd /path/to/campaign-watch && FEC_API_KEY=xxx python3 run_watch.py --fec-only
    0    6 * * *  cd /path/to/campaign-watch && python3 run_watch.py --calaccess-only

FEC is cheap to poll every few minutes. CalAccess's bulk export only
refreshes ~daily, so there's no benefit to running that half more than
once or twice a day.
"""
import argparse
import sys

import feed_store


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--fec-only", action="store_true")
    parser.add_argument("--calaccess-only", action="store_true")
    args = parser.parse_args()

    seen = feed_store.load_seen()
    new_items = []

    if not args.calaccess_only:
        import fec_watcher
        try:
            new_items += fec_watcher.run(seen)
        except Exception as e:
            print(f"[fec_watcher] error: {e}", file=sys.stderr)

    if not args.fec_only:
        import calaccess_watcher
        try:
            new_items += calaccess_watcher.run(seen)
        except Exception as e:
            print(f"[calaccess_watcher] error: {e}", file=sys.stderr)

    feed_store.save_seen(seen)
    count = feed_store.write_feed(new_items)
    print(f"Added {count} new item(s) to {feed_store.config.FEED_PATH}")


if __name__ == "__main__":
    main()
