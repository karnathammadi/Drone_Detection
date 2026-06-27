from datetime import datetime
from pathlib import Path

import cv2


def save_capture(frame, class_name, base_folder):
    now = datetime.now()
    folder = Path(base_folder) / now.strftime("%Y") / now.strftime("%m") / now.strftime("%d")
    folder.mkdir(parents=True, exist_ok=True)
    safe_class = class_name.replace(" ", "_").replace("/", "_")
    filename = f"{safe_class}_{now.strftime('%Y%m%d_%H%M%S')}.jpg"
    output_path = folder / filename
    counter = 2
    while output_path.exists():
        output_path = folder / f"{safe_class}_{now.strftime('%Y%m%d_%H%M%S')}_{counter}.jpg"
        counter += 1
    cv2.imwrite(str(output_path), frame)
    return output_path
