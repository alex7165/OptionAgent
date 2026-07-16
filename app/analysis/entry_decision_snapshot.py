from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path

from app.analysis.strategy import Strategy


@dataclass(frozen=True, slots=True)
class EntryDecisionSnapshot:
    symbol: str
    decision_date: date
    report_date: date
    expiration: date
    strategy: Strategy
    reference_price: float
    short_put_strike: float
    short_call_strike: float
    expected_move_percent: float | None = None
    selected_exit_trading_day_index: int | None = None

    def __post_init__(self) -> None:
        if not self.symbol.strip():
            raise ValueError("symbol must not be empty")
        if self.reference_price <= 0:
            raise ValueError("reference_price must be greater than zero")
        if self.short_put_strike >= self.short_call_strike:
            raise ValueError("short put strike must be below short call strike")


class EntryDecisionSnapshotRepository:
    """JSON persistence for the exact entry decision used by reviews."""

    def save(
        self,
        snapshots: tuple[EntryDecisionSnapshot, ...],
        path: str | Path,
    ) -> None:
        destination = Path(path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        rows = []
        for snapshot in snapshots:
            row = asdict(snapshot)
            for key in ("decision_date", "report_date", "expiration"):
                row[key] = row[key].isoformat()
            row["strategy"] = snapshot.strategy.value
            rows.append(row)
        destination.write_text(
            json.dumps(rows, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def load(self, path: str | Path) -> tuple[EntryDecisionSnapshot, ...]:
        source = Path(path)
        rows = json.loads(source.read_text(encoding="utf-8"))
        return tuple(
            EntryDecisionSnapshot(
                symbol=str(row["symbol"]).upper(),
                decision_date=date.fromisoformat(row["decision_date"]),
                report_date=date.fromisoformat(row["report_date"]),
                expiration=date.fromisoformat(row["expiration"]),
                strategy=Strategy(row["strategy"]),
                reference_price=float(row["reference_price"]),
                short_put_strike=float(row["short_put_strike"]),
                short_call_strike=float(row["short_call_strike"]),
                expected_move_percent=(
                    float(row["expected_move_percent"])
                    if row.get("expected_move_percent") is not None
                    else None
                ),
                selected_exit_trading_day_index=(
                    int(row["selected_exit_trading_day_index"])
                    if row.get("selected_exit_trading_day_index") is not None
                    else None
                ),
            )
            for row in rows
        )
