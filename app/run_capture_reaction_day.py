from __future__ import annotations

import argparse
import re
from datetime import date
from pathlib import Path

from app.analysis.pending_training_cohort import (
    PendingTradeExcelImporter,
    PendingTrainingCohortBuilder,
    PendingTrainingCohortRepository,
)
from app.marketdata.yahoo_price_history_provider import YahooPriceHistoryProvider


DATE_PATTERN = re.compile(r"(\d{4}-\d{2}-\d{2})")


def decision_date_from_filename(path: Path) -> date:
    match = DATE_PATTERN.search(path.name)
    if match is None:
        raise ValueError(
            "Could not derive decision date from filename; use --decision-date"
        )
    return date.fromisoformat(match.group(1))


def run(
    trades_path: Path,
    decision_date: date | None = None,
    output_path: Path | None = None,
) -> int:
    resolved_date = decision_date or decision_date_from_filename(trades_path)
    entries = PendingTradeExcelImporter().load(trades_path, resolved_date)
    cohort = PendingTrainingCohortBuilder(
        YahooPriceHistoryProvider()
    ).build(entries, source_file=str(trades_path))

    destination = output_path or Path(
        "data/pending_training"
    ) / f"{resolved_date.isoformat()}.json"
    PendingTrainingCohortRepository().save(cohort, destination)

    print(f"Trade-Tabelle: {trades_path}")
    print(f"Entscheidungstag: {resolved_date.isoformat()}")
    print(f"Offene Lernkohorte: {destination}")
    print(f"Erfasste Reaktionstage: {len(cohort.captured_trades)}")
    for item in cohort.captured_trades:
        status = (
            "INNERHALB"
            if item.finished_inside_short_strikes
            else "VERLETZT"
        )
        touches = []
        if item.put_touched:
            touches.append("Put-Touch")
        if item.call_touched:
            touches.append("Call-Touch")
        touch_text = ", ".join(touches) if touches else "kein Touch"
        print(
            f"{item.symbol:<5} | {item.reaction_date} | "
            f"Close {item.close:.2f} ({item.close_move_percent:+.2f} %) | "
            f"{status} | {touch_text}"
        )
    for symbol in cohort.missing_symbols:
        print(f"{symbol:<5} | KEIN ABGESCHLOSSENER REAKTIONSTAG")

    return 0 if not cohort.missing_symbols else 1


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trades",
        type=Path,
        required=True,
        help="Daily-trades Excel file",
    )
    parser.add_argument("--decision-date", type=date.fromisoformat)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    raise SystemExit(run(args.trades, args.decision_date, args.output))


if __name__ == "__main__":
    main()
