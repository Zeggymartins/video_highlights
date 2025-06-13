from flask import Flask, request, send_from_directory, jsonify
from werkzeug.utils import secure_filename
from flask_cors import CORS
import os
import logging
import cv2
import numpy as np
from faster_whisper import WhisperModel
import subprocess

# --- CONFIGURATION ---
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), '..', 'uploaded_videos')
FILES_FOLDER = '../files'
AUDIO_OUTPUT = os.path.join(FILES_FOLDER, 'audio.wav')
CAPTIONS_PATH = os.path.join(FILES_FOLDER, 'captions.txt')
ALLOWED_EXTENSIONS = {'mp4', 'mov', 'avi', 'mkv'}

# --- SETUP ---
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(FILES_FOLDER, exist_ok=True)

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
CORS(app)
# CORS(app, resources={r"/*": {"origins": "https://your-frontend.com"}})


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- MODEL LOAD ---
model = WhisperModel("medium", compute_type="float32", num_workers=1)

# --- HELPERS ---
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_video_duration(path):
    cap = cv2.VideoCapture(path)
    if not cap.isOpened():
        return 0
    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT)
    cap.release()
    return round(frame_count / fps, 2) if fps else 0

def extract_audio(video_path, audio_path=AUDIO_OUTPUT):
    try:
        command = [
            "ffmpeg", "-y", "-i", video_path,
            "-vn", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1", audio_path
        ]
        subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return audio_path
    except subprocess.CalledProcessError as e:
        raise Exception(f"ffmpeg error: {e.stderr.decode()}")

def transcribe_audio(audio_path, language="en"):
    try:
        segments, _ = model.transcribe(audio_path, language=language, task="translate")
        captions = []
        labeled_segments = []

        with open(CAPTIONS_PATH, "w", encoding="utf-8") as f:
            for segment in segments:
                start, end, text = segment.start, segment.end, segment.text.strip()
                duration = end - start
                wps = len(text.split()) / duration if duration > 0 else 0

                labels = []
                if wps > 3.5:
                    labels.append("fast speech")
                elif wps < 1.0:
                    labels.append("slow speech")
                if duration > 5 and wps < 0.5:
                    labels.append("long silence")

                captions.append((start, end, text))
                labeled_segments.append((start, end, text, labels))
                f.write(f"{start:.2f} --> {end:.2f}\n{text}\n\n")

        return labeled_segments
    except Exception as e:
        logger.error("❌ Transcription failed: %s", e)
        return []

def detect_motion_spikes(video_path, threshold=30.0):
    cap = cv2.VideoCapture(video_path)
    motion_times = []
    prev_gray = None
    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_idx = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        if prev_gray is not None:
            diff = cv2.absdiff(prev_gray, gray)
            motion_level = cv2.mean(diff)[0]
            if motion_level > threshold:
                timestamp = round(frame_idx / fps, 2)
                motion_times.append(timestamp)
        prev_gray = gray
        frame_idx += 1

    cap.release()
    return motion_times

def detect_bright_spikes(video_path, brightness_threshold=200):
    cap = cv2.VideoCapture(video_path)
    bright_times = []
    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_idx = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        brightness = np.mean(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY))
        if brightness > brightness_threshold:
            bright_times.append(round(frame_idx / fps, 2))
        frame_idx += 1

    cap.release()
    return bright_times

def get_highlight_segments(segments, motion_spikes, bright_spikes, margin=1.5):
    highlights = []

    for start, end, text, labels in segments:
        time_range = lambda t: start - margin <= t <= end + margin

        motion_hit = any(time_range(t) for t in motion_spikes)
        bright_hit = any(time_range(t) for t in bright_spikes)

        if motion_hit:
            labels.append("fast motion")
        if bright_hit:
            labels.append("bright display")

        if labels:
            highlights.append({
                "start": round(start, 2),
                "end": round(end, 2),
                "text": text.strip(),
                "labels": list(set(labels))
            })

    return highlights

# --- ROUTES ---
@app.route('/')
def root():
    return jsonify({"message": "Video processing API is running."})

@app.route('/upload', methods=['POST'])
def upload_video():
    if 'video' not in request.files:
        return jsonify({"error": "No video file part"}), 400

    video = request.files['video']
    if video.filename == '':
        return jsonify({"error": "No selected file"}), 400

    if not allowed_file(video.filename):
        return jsonify({"error": "Unsupported file type"}), 400

    filename = secure_filename(video.filename)
    save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    video.save(save_path)

    size_mb = round(os.path.getsize(save_path) / (1024 * 1024), 2)
    duration = get_video_duration(save_path)

    try:
        motion_spikes = detect_motion_spikes(save_path)
        bright_spikes = detect_bright_spikes(save_path)
        audio_path = extract_audio(save_path)
        labeled_segments = transcribe_audio(audio_path)

        captions = [f"[{round(s[0], 1)}s - {round(s[1], 1)}s] {s[2]}" for s in labeled_segments]
        highlights = get_highlight_segments(labeled_segments, motion_spikes, bright_spikes)

        return jsonify({
            "filename": filename,
            "size_mb": size_mb,
            "duration": duration,
            "motion_spikes": motion_spikes,
            "captions": captions,
            "highlights": highlights,
            "audio_url": "/files/audio.wav"
        })

    except Exception as e:
        logger.error("⚠️ Processing failed: %s", e)
        return jsonify({"error": "An error occurred during processing", "details": str(e)}), 500

@app.route('/videos/<filename>')
def serve_video(filename):
    path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    print(f"🔍 Serving: {path}")
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


@app.route('/files/<filename>')
def serve_file(filename):
    return send_from_directory(os.path.abspath(FILES_FOLDER), filename)

# --- MAIN ---
if __name__ == '__main__':
    app.run(debug=True)
