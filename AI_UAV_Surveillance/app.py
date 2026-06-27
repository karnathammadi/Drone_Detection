import logging
import threading
import uuid
from datetime import datetime
from functools import wraps
from pathlib import Path

import cv2
from flask import Flask, Response, abort, flash, jsonify, redirect, render_template, request, send_file, session, url_for
from werkzeug.utils import secure_filename

import config
from modules.database import SurveillanceDB
from modules.detector import UAVDetector
from modules.email_alert import send_detection_email
from modules.frame_saver import save_capture
from modules.report_generator import filter_rows, generate_excel, generate_pdf
from modules.siren_alert import SirenAlert
from modules.voice_alert import VoiceAlert

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = config.SECRET_KEY
app.config["MAX_CONTENT_LENGTH"] = 1024 * 1024 * 1024

for folder in [config.UPLOAD_FOLDER, config.RESULT_FOLDER, config.CAPTURE_FOLDER]:
    folder.mkdir(parents=True, exist_ok=True)

db = SurveillanceDB(config.DATABASE_PATH)
db.init(config.DEFAULT_CONFIDENCE)
detectors = {
    key: UAVDetector(meta["path"], config.CLASS_NAMES, model_key=key, backend=meta["backend"])
    for key, meta in config.MODEL_REGISTRY.items()
}
detector = detectors["yolov8"]
voice_alert = VoiceAlert(cooldown=5)
siren_alert = SirenAlert(config.SOUND_PATH)
camera = None
webcam_tracks = []
video_jobs = {}
video_jobs_lock = threading.Lock()


def login_required(handler):
    @wraps(handler)
    def wrapper(*args, **kwargs):
        if not session.get("authenticated"):
            return redirect(url_for("login"))
        return handler(*args, **kwargs)
    return wrapper


def allowed_file(filename, extensions):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in extensions


def rel_static(path):
    return str(Path(path).relative_to(config.BASE_DIR)).replace("\\", "/")


def current_settings():
    settings = db.get_settings()
    settings.setdefault("confidence_threshold", str(config.DEFAULT_CONFIDENCE))
    return settings


def model_options():
    options = []
    for key, meta in config.MODEL_REGISTRY.items():
        path = Path(meta["path"])
        options.append(
            {
                "key": key,
                "label": meta["label"],
                "description": meta["description"],
                "available": path.exists(),
                "path": path.name,
            }
        )
    return options


def selected_detector():
    requested = request.form.get("model_key") or request.args.get("model_key") or "yolov8"
    if requested not in detectors:
        requested = "yolov8"
    return requested, detectors[requested]


def summarize_detections(detections):
    class_counts = {}
    confidences = []
    for detection in detections:
        class_counts[detection.class_name] = class_counts.get(detection.class_name, 0) + 1
        confidences.append(detection.confidence)
    return {
        "total_objects": len(detections),
        "class_counts": class_counts,
        "average_confidence": round(sum(confidences) / len(confidences), 3) if confidences else 0,
        "max_confidence": round(max(confidences), 3) if confidences else 0,
    }


def handle_alerts(frame, detections, source_type, location):
    settings = current_settings()
    for detection in detections:
        timestamp = datetime.now().isoformat(timespec="seconds")
        capture_path = save_capture(frame, detection.class_name, config.CAPTURE_FOLDER)
        db.add_detection(
            detection.class_name,
            detection.confidence,
            timestamp,
            rel_static(capture_path),
            source_type,
            str(detection.bbox),
            location,
            detection.detection_time_ms,
        )
        if settings.get("voice_enabled") == "1":
            voice_alert.speak(detection.class_name)
        if settings.get("siren_enabled") == "1":
            siren_alert.play()
        if settings.get("email_enabled") == "1":
            email_settings = {
                **settings,
                "email_address": settings.get("email_address") or config.EMAIL_ADDRESS,
                "email_password": settings.get("email_password") or config.EMAIL_PASSWORD,
                "email_to": settings.get("email_to") or config.EMAIL_TO,
                "smtp_server": settings.get("smtp_server") or config.SMTP_SERVER,
                "smtp_port": settings.get("smtp_port") or config.SMTP_PORT,
            }
            try:
                send_detection_email(email_settings, detection.class_name, detection.confidence, timestamp, location, capture_path)
            except Exception as exc:
                logger.warning("Email alert failed: %s", exc)


@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if request.form.get("username") == config.USERNAME and request.form.get("password") == config.PASSWORD:
            session["authenticated"] = True
            return redirect(url_for("dashboard"))
        flash("Invalid username or password.", "danger")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/dashboard")
@login_required
def dashboard():
    total_uploads, total_detections, today, class_counts, daily = db.dashboard_stats()
    class_labels = [row["class_name"] for row in class_counts]
    class_values = [row["c"] for row in class_counts]
    daily_labels = [row["day"] for row in daily]
    daily_values = [row["c"] for row in daily]
    return render_template(
        "dashboard.html",
        total_uploads=total_uploads,
        total_detections=total_detections,
        today=today,
        class_counts=class_counts,
        class_labels=class_labels,
        class_values=class_values,
        daily=daily,
        daily_labels=daily_labels,
        daily_values=daily_values,
        recent=db.recent(8),
    )


@app.route("/image", methods=["GET", "POST"])
@login_required
def image_detection():
    result = None
    detections = []
    summary = None
    model_key, active_detector = selected_detector()
    if request.method == "POST":
        file = request.files.get("image")
        if not file or not file.filename:
            flash("Choose an image file.", "warning")
            return redirect(url_for("image_detection"))
        if not allowed_file(file.filename, config.ALLOWED_IMAGE_EXTENSIONS):
            flash("Unsupported image format.", "danger")
            return redirect(url_for("image_detection"))
        filename = secure_filename(file.filename)
        timestamp = datetime.now().isoformat(timespec="seconds")
        upload_path = config.UPLOAD_FOLDER / f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{filename}"
        result_path = config.RESULT_FOLDER / f"{upload_path.stem}_detected.jpg"
        file.save(upload_path)
        db.add_upload(filename, "Uploaded Image", timestamp)
        settings = current_settings()
        try:
            annotated, detections = active_detector.detect_image(upload_path, result_path, float(settings["confidence_threshold"]))
            if detections:
                handle_alerts(annotated, detections, "image", filename)
            result = rel_static(result_path)
            summary = summarize_detections(detections)
        except Exception as exc:
            logger.exception("Image detection failed")
            flash(str(exc), "danger")
    return render_template(
        "image_detection.html",
        result=result,
        detections=detections,
        summary=summary,
        model_options=model_options(),
        selected_model=model_key,
    )


@app.route("/video", methods=["GET", "POST"])
@login_required
def video_detection():
    processed_video = None
    stats = None
    if request.method == "POST":
        file = request.files.get("video")
        if not file or not file.filename:
            flash("Choose a video file.", "warning")
            return redirect(url_for("video_detection"))
        if not allowed_file(file.filename, config.ALLOWED_VIDEO_EXTENSIONS):
            flash("Unsupported video format.", "danger")
            return redirect(url_for("video_detection"))
        filename = secure_filename(file.filename)
        upload_path = config.UPLOAD_FOLDER / f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{filename}"
        result_path = config.RESULT_FOLDER / f"{upload_path.stem}_processed.mp4"
        file.save(upload_path)
        db.add_upload(filename, "Uploaded Video", datetime.now().isoformat(timespec="seconds"))
        settings = current_settings()

        def on_detection(frame, detections):
            handle_alerts(frame, detections[:1], "video", filename)

        try:
            stats = detector.detect_video(upload_path, result_path, float(settings["confidence_threshold"]), on_detection=on_detection)
            processed_video = rel_static(result_path)
        except Exception as exc:
            logger.exception("Video detection failed")
            flash(str(exc), "danger")
    return render_template("video_detection.html", processed_video=processed_video, stats=stats)


def update_video_job(job_id, **values):
    with video_jobs_lock:
        if job_id in video_jobs:
            video_jobs[job_id].update(values)


def get_video_job(job_id):
    with video_jobs_lock:
        return dict(video_jobs.get(job_id, {}))


def process_video_job(job_id, filename, upload_path, result_path):
    settings = current_settings()

    def on_frame(frame, frame_number):
        ok, buffer = cv2.imencode(".jpg", frame)
        if ok:
            update_video_job(
                job_id,
                latest_frame=buffer.tobytes(),
                processed_frames=frame_number,
                status="processing",
            )

    def on_detection(frame, detections):
        handle_alerts(frame, detections[:1], "video", filename)

    try:
        stats = detector.detect_video(
            upload_path,
            result_path,
            float(settings["confidence_threshold"]),
            on_detection=on_detection,
            on_frame=on_frame,
        )
        update_video_job(
            job_id,
            status="complete",
            stats=stats,
            processed_video=rel_static(result_path),
            result_filename=result_path.name,
        )
    except Exception as exc:
        logger.exception("Background video detection failed")
        update_video_job(job_id, status="error", error=str(exc))


@app.route("/video/start", methods=["POST"])
@login_required
def video_start():
    file = request.files.get("video")
    if not file or not file.filename:
        return jsonify({"error": "Choose a video file."}), 400
    if not allowed_file(file.filename, config.ALLOWED_VIDEO_EXTENSIONS):
        return jsonify({"error": "Unsupported video format."}), 400

    filename = secure_filename(file.filename)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    upload_path = config.UPLOAD_FOLDER / f"{stamp}_{filename}"
    result_path = config.RESULT_FOLDER / f"{upload_path.stem}_processed.mp4"
    file.save(upload_path)
    db.add_upload(filename, "Uploaded Video", datetime.now().isoformat(timespec="seconds"))

    job_id = uuid.uuid4().hex
    with video_jobs_lock:
        video_jobs[job_id] = {
            "status": "queued",
            "filename": filename,
            "processed_frames": 0,
            "latest_frame": None,
            "stats": None,
            "processed_video": None,
            "result_filename": None,
            "error": None,
        }

    thread = threading.Thread(
        target=process_video_job,
        args=(job_id, filename, upload_path, result_path),
        daemon=True,
    )
    thread.start()
    return jsonify({"job_id": job_id})


@app.route("/video/job/<job_id>/status")
@login_required
def video_job_status(job_id):
    job = get_video_job(job_id)
    if not job:
        abort(404)
    return jsonify(
        {
            "status": job.get("status"),
            "filename": job.get("filename"),
            "processed_frames": job.get("processed_frames", 0),
            "stats": job.get("stats"),
            "processed_video": job.get("processed_video"),
            "result_filename": job.get("result_filename"),
            "error": job.get("error"),
            "has_frame": job.get("latest_frame") is not None,
        }
    )


@app.route("/video/job/<job_id>/frame")
@login_required
def video_job_frame(job_id):
    job = get_video_job(job_id)
    if not job:
        abort(404)
    frame = job.get("latest_frame")
    if not frame:
        abort(404)
    return Response(frame, mimetype="image/jpeg")


def stream_video_file(video_path):
    cap = cv2.VideoCapture(str(video_path))
    try:
        while cap.isOpened():
            ok, frame = cap.read()
            if not ok:
                break
            ok, buffer = cv2.imencode(".jpg", frame)
            if ok:
                yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + buffer.tobytes() + b"\r\n"
    finally:
        cap.release()


@app.route("/video/preview/<path:filename>")
@login_required
def video_preview(filename):
    video_path = (config.RESULT_FOLDER / filename).resolve()
    result_root = config.RESULT_FOLDER.resolve()
    if result_root not in video_path.parents or not video_path.exists():
        abort(404)
    return Response(stream_video_file(video_path), mimetype="multipart/x-mixed-replace; boundary=frame")


def result_video_path(filename):
    video_path = (config.RESULT_FOLDER / filename).resolve()
    result_root = config.RESULT_FOLDER.resolve()
    if result_root not in video_path.parents or not video_path.exists():
        abort(404)
    return video_path


@app.route("/video/meta/<path:filename>")
@login_required
def video_meta(filename):
    video_path = result_video_path(filename)
    cap = cv2.VideoCapture(str(video_path))
    try:
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        fps = float(cap.get(cv2.CAP_PROP_FPS) or 0)
        return jsonify({"frames": frame_count, "fps": fps})
    finally:
        cap.release()


@app.route("/video/frame/<path:filename>/<int:frame_index>")
@login_required
def video_frame(filename, frame_index):
    video_path = result_video_path(filename)
    cap = cv2.VideoCapture(str(video_path))
    try:
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        if frame_count <= 0:
            abort(404)
        frame_index = max(0, min(frame_index, frame_count - 1))
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
        ok, frame = cap.read()
        if not ok:
            abort(404)
        ok, buffer = cv2.imencode(".jpg", frame)
        if not ok:
            abort(500)
        return Response(buffer.tobytes(), mimetype="image/jpeg")
    finally:
        cap.release()


@app.route("/webcam")
@login_required
def webcam_detection():
    return render_template("webcam_detection.html")


def generate_camera_stream():
    global camera, webcam_tracks
    if camera is None:
        camera = cv2.VideoCapture(0)
        webcam_tracks = []
    settings = current_settings()
    threshold = float(settings["confidence_threshold"])
    while camera and camera.isOpened():
        ok, frame = camera.read()
        if not ok:
            break
        annotated, detections = detector.detect_frame(frame, threshold)
        unique_new_detections = detector._new_unique_detections(detections, webcam_tracks)
        if unique_new_detections:
            handle_alerts(annotated, unique_new_detections, "webcam", "Live Camera")
        _, buffer = cv2.imencode(".jpg", annotated)
        yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + buffer.tobytes() + b"\r\n"


@app.route("/webcam/start")
@login_required
def webcam_start():
    return Response(generate_camera_stream(), mimetype="multipart/x-mixed-replace; boundary=frame")


@app.route("/webcam/stop")
@login_required
def webcam_stop():
    global camera
    if camera:
        camera.release()
        camera = None
    return ("", 204)


@app.route("/history")
@login_required
def history():
    search = request.args.get("search", "")
    return render_template("history.html", rows=db.history(search), search=search)


@app.route("/history/delete/<int:detection_id>", methods=["POST"])
@login_required
def delete_history(detection_id):
    db.delete_detection(detection_id)
    flash("Detection deleted.", "success")
    return redirect(url_for("history"))


@app.route("/history/export")
@login_required
def export_history():
    output = config.RESULT_FOLDER / "detection_history.csv"
    db.export_csv(output)
    return send_file(output, as_attachment=True)


@app.route("/reports", methods=["GET", "POST"])
@login_required
def reports():
    if request.method == "POST":
        report_type = request.form.get("report_type", "daily")
        output_format = request.form.get("output_format", "pdf")
        rows = filter_rows(db.history(), report_type)
        if output_format == "excel":
            output = config.RESULT_FOLDER / f"{report_type}_uav_report.xlsx"
            generate_excel(rows, output)
        else:
            output = config.RESULT_FOLDER / f"{report_type}_uav_report.pdf"
            generate_pdf(rows, output, f"{report_type.title()} UAV Detection Report")
        return send_file(output, as_attachment=True)
    return render_template("reports.html")


@app.route("/settings", methods=["GET", "POST"])
@login_required
def settings():
    if request.method == "POST":
        db.update_settings(
            {
                "confidence_threshold": request.form.get("confidence_threshold", str(config.DEFAULT_CONFIDENCE)),
                "voice_enabled": "1" if request.form.get("voice_enabled") else "0",
                "siren_enabled": "1" if request.form.get("siren_enabled") else "0",
                "email_enabled": "1" if request.form.get("email_enabled") else "0",
                "email_address": request.form.get("email_address", ""),
                "email_password": request.form.get("email_password", ""),
                "email_to": request.form.get("email_to", ""),
                "smtp_server": request.form.get("smtp_server", "smtp.gmail.com"),
                "smtp_port": request.form.get("smtp_port", "587"),
            }
        )
        flash("Settings saved.", "success")
        return redirect(url_for("settings"))
    return render_template("settings.html", settings=current_settings())


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
