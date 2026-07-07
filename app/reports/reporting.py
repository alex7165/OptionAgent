from datetime import datetime
from pathlib import Path


def save_report(question: str, answer: str) -> Path:
    reports_dir = Path("reports")
    reports_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename = reports_dir / f"report_{timestamp}.md"

    content = f"""# OptionAgent Report

## Zeitpunkt

{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## Frage

{question}

## Antwort

{answer}
"""

    filename.write_text(content, encoding="utf-8")
    return filename