from dataclasses import dataclass
from pathlib import Path
from time import perf_counter

import cv2


@dataclass
class Detection:
    class_name: str
    confidence: float
    bbox: tuple
    detection_time_ms: float


class UAVDetector:
    def __init__(self, model_path, class_names, model_key="yolov8", backend="ultralytics"):
        self.model_path = Path(model_path)
        self.class_names = class_names
        self.model_key = model_key
        self.backend = backend
        self.model = None

    def load(self):
        if self.model is None:
            if not self.model_path.exists():
                raise FileNotFoundError(f"{self.model_key} model not found: {self.model_path}")
            if self.backend == "ultralytics":
                from ultralytics import YOLO

                self.model = YOLO(str(self.model_path))
            else:
                raise NotImplementedError(
                    f"{self.model_key} inference needs exported TorchScript/ONNX integration. "
                    "Run the model notebook first and place the exported model in the configured models folder."
                )
        return self.model

    def info(self):
        return {
            "key": self.model_key,
            "backend": self.backend,
            "path": str(self.model_path),
            "available": self.model_path.exists(),
        }

    def detect_frame(self, frame, confidence_threshold):
        model = self.load()
        started = perf_counter()
        results = model(frame, conf=float(confidence_threshold), verbose=False)
        detection_time_ms = (perf_counter() - started) * 1000
        detections = []
        annotated = frame.copy()
        for result in results:
            annotated = result.plot()
            for box in result.boxes:
                cls_id = int(box.cls[0])
                confidence = float(box.conf[0])
                label = self.class_names.get(cls_id, model.names.get(cls_id, str(cls_id)))
                if confidence >= float(confidence_threshold):
                    xyxy = tuple(int(v) for v in box.xyxy[0].tolist())
                    detections.append(Detection(label, confidence, xyxy, detection_time_ms))
        return annotated, detections

    def detect_image(self, input_path, output_path, confidence_threshold):
        frame = cv2.imread(str(input_path))
        if frame is None:
            raise ValueError(f"Could not read image: {input_path}")
        annotated, detections = self.detect_frame(frame, confidence_threshold)
        cv2.imwrite(str(output_path), annotated)
        return annotated, detections

    def _iou(self, first, second):
        ax1, ay1, ax2, ay2 = first
        bx1, by1, bx2, by2 = second
        ix1, iy1 = max(ax1, bx1), max(ay1, by1)
        ix2, iy2 = min(ax2, bx2), min(ay2, by2)
        intersection = max(0, ix2 - ix1) * max(0, iy2 - iy1)
        area_a = max(1, ax2 - ax1) * max(1, ay2 - ay1)
        area_b = max(1, bx2 - bx1) * max(1, by2 - by1)
        return intersection / float(area_a + area_b - intersection)

    def _center_score(self, first, second):
        ax1, ay1, ax2, ay2 = first
        bx1, by1, bx2, by2 = second
        acx, acy = (ax1 + ax2) / 2, (ay1 + ay2) / 2
        bcx, bcy = (bx1 + bx2) / 2, (by1 + by2) / 2
        distance = ((acx - bcx) ** 2 + (acy - bcy) ** 2) ** 0.5
        scale = max(ax2 - ax1, ay2 - ay1, bx2 - bx1, by2 - by1, 1)
        return max(0, 1 - (distance / (scale * 1.25)))

    def _new_unique_detections(self, detections, tracks, max_missed=30):
        new_detections = []
        matched_track_ids = set()

        for track in tracks:
            track["missed"] += 1

        for detection in detections:
            best_track = None
            best_score = 0
            for track in tracks:
                if track["id"] in matched_track_ids or track["class_name"] != detection.class_name:
                    continue
                score = max(self._iou(track["bbox"], detection.bbox), self._center_score(track["bbox"], detection.bbox))
                if score > best_score:
                    best_score = score
                    best_track = track

            if best_track and best_score >= 0.30:
                best_track["bbox"] = detection.bbox
                best_track["missed"] = 0
                matched_track_ids.add(best_track["id"])
            else:
                track_id = len(tracks) + 1
                tracks.append({"id": track_id, "class_name": detection.class_name, "bbox": detection.bbox, "missed": 0})
                matched_track_ids.add(track_id)
                new_detections.append(detection)

        tracks[:] = [track for track in tracks if track["missed"] <= max_missed]
        return new_detections

    def detect_video(self, input_path, output_path, confidence_threshold, on_detection=None, on_frame=None):
        cap = cv2.VideoCapture(str(input_path))
        if not cap.isOpened():
            raise ValueError(f"Could not open video: {input_path}")

        fps = cap.get(cv2.CAP_PROP_FPS) or 20
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(str(output_path), fourcc, fps, (width, height))

        tracks = []
        stats = {"frames": 0, "detections": 0, "classes": {}}
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            annotated, detections = self.detect_frame(frame, confidence_threshold)
            unique_new_detections = self._new_unique_detections(detections, tracks)
            writer.write(annotated)
            stats["frames"] += 1
            if on_frame:
                on_frame(annotated, stats["frames"])
            stats["detections"] += len(unique_new_detections)
            for detection in unique_new_detections:
                stats["classes"][detection.class_name] = stats["classes"].get(detection.class_name, 0) + 1
            if unique_new_detections and on_detection:
                on_detection(annotated, unique_new_detections)

        cap.release()
        writer.release()
        return stats
