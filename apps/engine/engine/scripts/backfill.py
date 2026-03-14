"""Manual historical data backfill from Taostats API.

Usage:
    python -m engine.scripts.backfill --from 2024-01-01
    python -m engine.scripts.backfill --subnet 19 --from 2024-01-01
    python -m engine.scripts.backfill --subnet 19 --from 2024-01-01 --to 2024-06-30
"""

import argparse
import asyncio
from datetime import UTC, datetime

from engine.core.logging import get_logger, setup_logging
from engine.ingestion.taostats_sync import run_taostats_backfill

log = get_logger(__name__)


def _parse_date(date_str: str) -> datetime:
    """Parse an ISO date string into a UTC datetime."""
    try:
        dt = datetime.fromisoformat(date_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        return dt
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            f"Invalid date format: {date_str}. Use YYYY-MM-DD."
        ) from exc


def main() -> None:
    """Entry point for the manual backfill CLI."""
    parser = argparse.ArgumentParser(
        description="Manual historical data backfill from Taostats API"
    )
    parser.add_argument(
        "--subnet",
        type=int,
        default=None,
        help="Specific subnet netuid to backfill (default: all active subnets)",
    )
    parser.add_argument(
        "--from",
        dest="from_date",
        type=_parse_date,
        required=True,
        help="Start date for backfill (ISO format: YYYY-MM-DD)",
    )
    parser.add_argument(
        "--to",
        dest="to_date",
        type=_parse_date,
        default=None,
        help="End date for backfill (ISO format: YYYY-MM-DD, default: now)",
    )

    args = parser.parse_args()

    setup_logging(debug=True)

    subnet_desc = f"subnet {args.subnet}" if args.subnet else "all active subnets"
    to_desc = args.to_date.strftime("%Y-%m-%d") if args.to_date else "now"
    log.info(
        "manual_backfill_starting",
        subnet=args.subnet,
        from_date=args.from_date.strftime("%Y-%m-%d"),
        to_date=to_desc,
        worker="backfill_cli",
    )

    from_str = args.from_date.strftime("%Y-%m-%d")
    print(f"Starting backfill for {subnet_desc} from {from_str} to {to_desc}")  # noqa: T201

    asyncio.run(
        run_taostats_backfill(
            subnet_filter=args.subnet,
            since_override=args.from_date,
            until_override=args.to_date,
        )
    )

    print("Backfill complete.")  # noqa: T201


if __name__ == "__main__":
    main()
