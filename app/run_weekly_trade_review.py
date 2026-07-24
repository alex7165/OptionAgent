from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path

from app.analysis.trade_excel_snapshot_loader import TradeExcelSnapshotLoader
from app.analysis.trade_snapshot_review import TradeSnapshotReviewRunner
from app.marketdata.yahoo_price_history_provider import YahooPriceHistoryProvider


def run(paths: tuple[Path, ...], end_date: date) -> int:
    snapshots = TradeExcelSnapshotLoader().load(paths)
    reviews = TradeSnapshotReviewRunner(YahooPriceHistoryProvider()).run(
        snapshots,
        end_date=end_date,
    )

    print(f"Excel-Dateien: {len(paths)}")
    print(f"Trades: {len(snapshots)}")
    print(f"Kursverlauf bis: {end_date.isoformat()}")

    reviewed = {review.snapshot.symbol for review in reviews}
    for snapshot in snapshots:
        if snapshot.symbol not in reviewed:
            print(f"{snapshot.symbol:<6} KEINE KURSDATEN")

    for review in reviews:
        snapshot = review.snapshot
        final = review.outcomes[-1]
        wrong = not final.finished_inside_short_strikes
        touched = any(
            outcome.put_touched or outcome.call_touched
            for outcome in review.outcomes
        )
        if not wrong and not touched:
            continue

        status = "VERLETZT" if wrong else "BERÜHRT, AM ENDE INNERHALB"
        print("\n" + "=" * 76)
        print(
            f"{snapshot.symbol} | {status} | Referenz {snapshot.reference_price:.2f} | "
            f"Put {snapshot.short_put_strike:g} | Call {snapshot.short_call_strike:g}"
        )
        for outcome in review.outcomes:
            touches = []
            if outcome.put_touched:
                touches.append("Put-Touch")
            if outcome.call_touched:
                touches.append("Call-Touch")
            print(
                f"Tag {outcome.exit_trading_day_index}: {outcome.exit_date} "
                f"Close {outcome.exit_close:.2f} | "
                f"{'INNERHALB' if outcome.finished_inside_short_strikes else 'VERLETZT'} | "
                f"{', '.join(touches) if touches else 'kein Touch'} | "
                f"MAE {outcome.max_adverse_move_percent:.2f}% | "
                f"MFE {outcome.max_favorable_move_percent:.2f}%"
            )

        repair = review.repair
        if repair.triggered:
            held = not bool(repair.repaired_strike_finished_outside)
            print(
                f"Reparatur: Tag {repair.trigger_day_index}, "
                f"{repair.threatened_side.value}-Seite, "
                f"Strike {repair.original_strike:.2f} → {repair.repaired_strike:.2f}, "
                f"bis Freitag {'gehalten' if held else 'verletzt'}"
            )
        else:
            print("Reparatur: nicht ausgelöst")

    return 0


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Review daily trade Excel exports and simulate repairs."
    )
    parser.add_argument("files", nargs="+", type=Path)
    parser.add_argument("--end-date", type=date.fromisoformat, required=True)
    args = parser.parse_args()
    raise SystemExit(run(tuple(args.files), args.end_date))


if __name__ == "__main__":
    main()
