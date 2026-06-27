import csv
import sqlite3
from contextlib import contextmanager
from pathlib import Path


class SurveillanceDB:
    def __init__(self, db_path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def connect(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def init(self, default_confidence=0.38):
        with self.connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS detections (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    class_name TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    timestamp TEXT NOT NULL,
                    image_path TEXT,
                    source_type TEXT NOT NULL,
                    bbox TEXT,
                    source_location TEXT,
                    detection_time_ms REAL
                );

                CREATE TABLE IF NOT EXISTS uploads (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    filename TEXT NOT NULL,
                    source_type TEXT NOT NULL,
                    timestamp TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
                """
            )
            defaults = {
                "confidence_threshold": str(default_confidence),
                "voice_enabled": "1",
                "siren_enabled": "1",
                "email_enabled": "0",
                "email_address": "",
                "email_password": "",
                "email_to": "",
                "smtp_server": "smtp.gmail.com",
                "smtp_port": "587",
            }
            self._ensure_column(conn, "detections", "detection_time_ms", "REAL")
            for key, value in defaults.items():
                conn.execute(
                    "INSERT OR IGNORE INTO settings(key, value) VALUES(?, ?)",
                    (key, value),
                )
            current_confidence = conn.execute(
                "SELECT value FROM settings WHERE key = 'confidence_threshold'"
            ).fetchone()
            if current_confidence and current_confidence["value"] in {"", "0.38", "0.5", "0.50"}:
                conn.execute(
                    "UPDATE settings SET value = ? WHERE key = 'confidence_threshold'",
                    (str(default_confidence),),
                )

    def _ensure_column(self, conn, table, column, column_type):
        columns = [row["name"] for row in conn.execute(f"PRAGMA table_info({table})")]
        if column not in columns:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {column_type}")

    def add_upload(self, filename, source_type, timestamp):
        with self.connect() as conn:
            conn.execute(
                "INSERT INTO uploads(filename, source_type, timestamp) VALUES(?, ?, ?)",
                (filename, source_type, timestamp),
            )

    def add_detection(self, class_name, confidence, timestamp, image_path, source_type, bbox="", source_location="", detection_time_ms=0):
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO detections(class_name, confidence, timestamp, image_path, source_type, bbox, source_location, detection_time_ms)
                VALUES(?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (class_name, confidence, timestamp, image_path, source_type, bbox, source_location, detection_time_ms),
            )

    def delete_detection(self, detection_id):
        with self.connect() as conn:
            conn.execute("DELETE FROM detections WHERE id = ?", (detection_id,))

    def get_settings(self):
        with self.connect() as conn:
            return {row["key"]: row["value"] for row in conn.execute("SELECT key, value FROM settings")}

    def update_settings(self, settings):
        with self.connect() as conn:
            for key, value in settings.items():
                conn.execute(
                    "INSERT INTO settings(key, value) VALUES(?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                    (key, str(value)),
                )

    def history(self, search=""):
        query = "SELECT * FROM detections"
        params = []
        if search:
            query += " WHERE class_name LIKE ? OR source_type LIKE ?"
            params = [f"%{search}%", f"%{search}%"]
        query += " ORDER BY timestamp DESC"
        with self.connect() as conn:
            return conn.execute(query, params).fetchall()

    def recent(self, limit=10):
        with self.connect() as conn:
            return conn.execute(
                "SELECT * FROM detections ORDER BY timestamp DESC LIMIT ?",
                (limit,),
            ).fetchall()

    def dashboard_stats(self):
        with self.connect() as conn:
            total_uploads = conn.execute("SELECT COUNT(*) AS c FROM uploads").fetchone()["c"]
            total_detections = conn.execute("SELECT COUNT(*) AS c FROM detections").fetchone()["c"]
            today = conn.execute(
                "SELECT COUNT(*) AS c FROM detections WHERE date(timestamp) = date('now', 'localtime')"
            ).fetchone()["c"]
            class_counts = conn.execute(
                "SELECT class_name, COUNT(*) AS c FROM detections GROUP BY class_name ORDER BY c DESC"
            ).fetchall()
            daily = conn.execute(
                """
                SELECT date(timestamp) AS day, COUNT(*) AS c
                FROM detections
                GROUP BY date(timestamp)
                ORDER BY day DESC
                LIMIT 7
                """
            ).fetchall()
        return total_uploads, total_detections, today, class_counts, list(reversed(daily))

    def export_csv(self, output_path):
        rows = self.history()
        with open(output_path, "w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(["id", "class_name", "confidence", "timestamp", "image_path", "source_type", "bbox", "detection_time_ms"])
            for row in rows:
                writer.writerow([row["id"], row["class_name"], row["confidence"], row["timestamp"], row["image_path"], row["source_type"], row["bbox"], row["detection_time_ms"]])
