from pathlib import Path

from openpyxl import Workbook

from app.analysis.trade_export_row import TradeExportRow


class TradeExporter:
    HEADERS = [
        "Aktie",
        "Kurs",
        "Strategie",
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

            rows.append(
                TradeExportRow(
                    aktie=candidate.earnings_event.symbol,
                    kurs=price,
                    strategie="Short Strangle",
                    short_put_prozent=(
                        (candidate.strike_selection.put.strike / price - 1) * 100
                    ),
                    short_call_prozent=(
                        (candidate.strike_selection.call.strike / price - 1) * 100
                    ),
                    short_put_strike=candidate.strike_selection.put.strike,
                    short_call_strike=candidate.strike_selection.call.strike,
                )
            )

        return rows

    def export_excel(
        self,
        candidates,
        output_path: str | Path,
    ) -> None:
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