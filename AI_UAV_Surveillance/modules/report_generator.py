from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas


def filter_rows(rows, report_type):
    now = datetime.now()
    if report_type == "daily":
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif report_type == "weekly":
        start = now - timedelta(days=7)
    else:
        start = now - timedelta(days=30)
    return [row for row in rows if datetime.fromisoformat(row["timestamp"]) >= start]


def generate_excel(rows, output_path):
    data = [dict(row) for row in rows]
    df = pd.DataFrame(data)
    df.to_excel(output_path, index=False)
    return output_path


def generate_pdf(rows, output_path, title):
    path = Path(output_path)
    c = canvas.Canvas(str(path), pagesize=letter)
    width, height = letter
    y = height - 50
    c.setFont("Helvetica-Bold", 16)
    c.drawString(40, y, title)
    y -= 30
    c.setFont("Helvetica", 9)
    for row in rows:
        line = f"{row['timestamp']} | {row['class_name']} | {row['confidence']:.2f} | {row['source_type']}"
        c.drawString(40, y, line[:115])
        y -= 16
        if y < 50:
            c.showPage()
            c.setFont("Helvetica", 9)
            y = height - 50
    c.save()
    return path
