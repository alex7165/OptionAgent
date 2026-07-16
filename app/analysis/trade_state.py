from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import date, datetime
from pathlib import Path

from app.analysis.entry_decision_snapshot import EntryDecisionSnapshot


@dataclass(frozen=True, slots=True)
class TradeStateAction:
    timestamp: datetime
    action: str
    quantity: int | None = None
    price: float | None = None
    cash_flow: float | None = None
    note: str | None = None


@dataclass(frozen=True, slots=True)
class TradeState:
    symbol: str
    entry: EntryDecisionSnapshot
    hedge_shares: int = 0
    realized_cash_flow: float = 0.0
    is_open: bool = True
    last_evaluated_at: datetime | None = None
    actions: tuple[TradeStateAction, ...] = ()

    @classmethod
    def from_entry(cls, entry: EntryDecisionSnapshot) -> "TradeState":
        return cls(symbol=entry.symbol, entry=entry)

    def with_evaluation(self, evaluated_at: datetime) -> "TradeState":
        return TradeState(
            symbol=self.symbol,
            entry=self.entry,
            hedge_shares=self.hedge_shares,
            realized_cash_flow=self.realized_cash_flow,
            is_open=self.is_open,
            last_evaluated_at=evaluated_at,
            actions=self.actions,
        )

    def apply_share_trade(
        self,
        *,
        timestamp: datetime,
        quantity: int,
        price: float,
        note: str | None = None,
    ) -> "TradeState":
        if quantity == 0:
            return self
        cash_flow = -quantity * price
        action = TradeStateAction(
            timestamp=timestamp,
            action="buy_shares" if quantity > 0 else "sell_shares",
            quantity=quantity,
            price=price,
            cash_flow=cash_flow,
            note=note,
        )
        return TradeState(
            symbol=self.symbol,
            entry=self.entry,
            hedge_shares=self.hedge_shares + quantity,
            realized_cash_flow=self.realized_cash_flow + cash_flow,
            is_open=self.is_open,
            last_evaluated_at=timestamp,
            actions=self.actions + (action,),
        )


class TradeStateRepository:
    def save(self, state: TradeState, path: str | Path) -> None:
        destination = Path(path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "symbol": state.symbol,
            "entry": self._entry_to_dict(state.entry),
            "hedge_shares": state.hedge_shares,
            "realized_cash_flow": state.realized_cash_flow,
            "is_open": state.is_open,
            "last_evaluated_at": (
                state.last_evaluated_at.isoformat()
                if state.last_evaluated_at is not None
                else None
            ),
            "actions": [
                {
                    **asdict(action),
                    "timestamp": action.timestamp.isoformat(),
                }
                for action in state.actions
            ],
        }
        destination.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def load(self, path: str | Path) -> TradeState:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        entry = self._entry_from_dict(payload["entry"])
        actions = tuple(
            TradeStateAction(
                timestamp=datetime.fromisoformat(row["timestamp"]),
                action=str(row["action"]),
                quantity=(int(row["quantity"]) if row.get("quantity") is not None else None),
                price=(float(row["price"]) if row.get("price") is not None else None),
                cash_flow=(float(row["cash_flow"]) if row.get("cash_flow") is not None else None),
                note=row.get("note"),
            )
            for row in payload.get("actions", [])
        )
        return TradeState(
            symbol=str(payload["symbol"]).upper(),
            entry=entry,
            hedge_shares=int(payload.get("hedge_shares", 0)),
            realized_cash_flow=float(payload.get("realized_cash_flow", 0.0)),
            is_open=bool(payload.get("is_open", True)),
            last_evaluated_at=(
                datetime.fromisoformat(payload["last_evaluated_at"])
                if payload.get("last_evaluated_at")
                else None
            ),
            actions=actions,
        )

    @staticmethod
    def _entry_to_dict(entry: EntryDecisionSnapshot) -> dict:
        row = asdict(entry)
        for key in ("decision_date", "report_date", "expiration"):
            row[key] = row[key].isoformat()
        row["strategy"] = entry.strategy.value
        return row

    @staticmethod
    def _entry_from_dict(row: dict) -> EntryDecisionSnapshot:
        from app.analysis.strategy import Strategy

        return EntryDecisionSnapshot(
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
