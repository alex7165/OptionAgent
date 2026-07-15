from pathlib import Path

from openpyxl import Workbook

from app.analysis.trade_export_row import TradeExportRow


class TradeExporter:
    HEADERS = [
        "Aktie",
        "Kurs",
        "Strategie",
        "Score",
        "ShortPutProzent",
        "LongPutProzent",
        "ShortCallProzent",
        "LongCallProzent",
        "ShortPutStrike",
        "LongPutStrike",
        "ShortCallStrike",
        "LongCallStrike",
    ]

    def export_rows(self, candidates) -> list[TradeExportRow]:
        rows: list[TradeExportRow] = []

        for candidate in candidates:
            if candidate.strike_selection is None:
                continue

            price = candidate.snapshot.quote.price
            selection = candidate.strike_selection

            strategy = (
                "Iron Condor"
                if selection.long_put is not None and selection.long_call is not None
                else "Short Strangle"
            )

            rows.append(
                TradeExportRow(
                    aktie=candidate.earnings_event.symbol,
                    kurs=price,
                    strategie=strategy,
                    score=(
                        candidate.decision_report.trade_score.total
                        if candidate.decision_report is not None
                        else None
                    ),
                    short_put_prozent=(selection.put.strike / price - 1) * 100,
                    long_put_prozent=(
                        (selection.long_put.strike / price - 1) * 100
                        if selection.long_put is not None
                        else None
                    ),
                    short_call_prozent=(selection.call.strike / price - 1) * 100,
                    long_call_prozent=(
                        (selection.long_call.strike / price - 1) * 100
                        if selection.long_call is not None
                        else None
                    ),
                    short_put_strike=selection.put.strike,
                    long_put_strike=(
                        selection.long_put.strike
                        if selection.long_put is not None
                        else None
                    ),
                    short_call_strike=selection.call.strike,
                    long_call_strike=(
                        selection.long_call.strike
                        if selection.long_call is not None
                        else None
                    ),
                )
            )

        return rows

    def export_excel(self, candidates, output_path: str | Path) -> None:
        rows = self.export_rows(candidates)
        rows.sort(key=lambda row: row.aktie)

        workbook = Workbook()
        worksheet = workbook.active
        worksheet.title = "Earnings Crush"

        worksheet.append(self.HEADERS)

        for row in rows:
            worksheet.append(
                [
                    row.aktie,
                    row.kurs,
                    row.strategie,
                    row.score,
                    row.short_put_prozent,
                    row.long_put_prozent,
                    row.short_call_prozent,
                    row.long_call_prozent,
                    row.short_put_strike,
                    row.long_put_strike,
                    row.short_call_strike,
                    row.long_call_strike,
                ]
            )

        workbook.save(Path(output_path))