import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

SECRET_KEY = os.getenv("SECRET_KEY", "change-this-secret-key")
USERNAME = os.getenv("APP_USERNAME", "admin")
PASSWORD = os.getenv("APP_PASSWORD", "admin123")

MODEL_PATH = BASE_DIR / "models" / "best.pt"
MODEL_REGISTRY = {
    "yolov8": {
        "label": "YOLOv8",
        "backend": "ultralytics",
        "path": MODEL_PATH,
        "description": "Fast real-time detector for image, video, and webcam surveillance.",
    },
    "fasterrcnn": {
        "label": "Faster R-CNN",
        "backend": "torchvision",
        "path": BASE_DIR / "models" / "fasterrcnn_resnet50_fpn.pth",
        "description": "Two-stage detector for high-accuracy research comparison.",
    },
    "ssd": {
        "label": "SSD",
        "backend": "torchvision",
        "path": BASE_DIR / "models" / "ssd300_vgg16.pth",
        "description": "Single-shot detector for lightweight comparison.",
    },
}
DATABASE_PATH = BASE_DIR / "database" / "surveillance.db"

UPLOAD_FOLDER = BASE_DIR / "static" / "uploads"
RESULT_FOLDER = BASE_DIR / "static" / "results"
CAPTURE_FOLDER = BASE_DIR / "static" / "captures"
SOUND_PATH = BASE_DIR / "static" / "sounds" / "siren.wav"

ALLOWED_IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "bmp"}
ALLOWED_VIDEO_EXTENSIONS = {"mp4", "avi", "mov", "mkv"}

DEFAULT_CONFIDENCE = float(os.getenv("CONFIDENCE_THRESHOLD", "0.60"))
CLASS_NAMES = {
    0: "UAV",
    1: "side-by-side rotor",
    2: "single rotor",
    3: "tandem rotor",
}

EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS", "")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD", "")
EMAIL_TO = os.getenv("EMAIL_TO", EMAIL_ADDRESS)
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
