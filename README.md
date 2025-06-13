# 🎮 Video Highlights Detection API

This project provides an AI-powered backend and frontend to analyze videos, detect highlight moments using motion and brightness spikes, transcribe speech, and generate captions. Users can upload videos through the frontend interface, which communicates with the Flask backend API to return the processed results and visualizes them in a user-friendly format.

---

## 📁 Project Structure

```
project-root/
│
├── backend/
│   ├── app/
│   │   ├── main.py               # Flask app and API routes
│   │               
│   ├── uploaded_videos
│   |___files     
│   └── requirements.txt
│
├── frontend/
│   ├── upload.html               # Video upload interface
│   ├── templates/play.html       # Results viewer page
│   ├── static/                   # JS, CSS, images
│
├── .env                          # Environment variables
├── .gitignore
└── README.md                     # Project documentation
```

---

## ✨ Features

- Upload videos via a simple frontend.
- Detect motion and brightness spikes using OpenCV.
- Transcribe speech using Whisper and generate human-readable captions.
- Analyze and combine audio + visual cues to detect highlights.
- Display key segments and captions in an interactive viewer.
- Show real-time upload and processing status using alerts and spinners.
- Persistent metadata via `sessionStorage` between pages.

---

## ⚙️ Prerequisites

- Python 3.9+
- pip
- html, bootstrap, css and javascript
- ffmpeg installed and added to your system PATH

---

## 🥪 Setup

### 1. Clone the repo

```bash
git clone https://github.com/your-username/video-highlights-api.git
cd video-highlights-api
```

### 2. Create and activate virtual environment

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install dependencies

```bash
cd backend
pip install -r requirements.txt
```

If using Whisper, make sure `ffmpeg` is installed globally:

```bash
brew install ffmpeg  # macOS

```

---

## 📦 Environment Configuration

Create a `.env` file in the root directory:

### `.env`

```env
APP_URL=http://127.0.0.1:5000

```



---

## ▶️ Running the Project

### 1. Start the Flask API

```bash
cd backend
source ../venv/bin/activate
flask --app app/main.py run
```

By default, this runs at `http://127.0.0.1:5000`.

---

### 2. Open the Frontend

Open `frontend/upload.html` directly in your browser (you **don’t** serve it from Flask).

Make sure:

- The upload form submits to `http://127.0.0.1:5000/upload`
- The response redirects to `play.html`, which reads metadata from `sessionStorage`

To ensure your `play.html` is accessible:

- It must be inside `frontend/`
- Do **not** move it to the Flask `templates/` folder unless you want Flask to render it

---

## 📤 API Endpoint

### `POST /upload`

Uploads a video and returns metadata + highlights.

**Request:**

- `FormData` with one field: `video` (file input)

**Response:**

```json
{
  "filename": "example.mp4",
  "size_mb": 12.4,
  "duration": 145.2,
  "motion_spikes": [3.4, 6.7, ...],
  "captions": [
    "[0.0s - 4.0s] Hello world.",
    "[4.0s - 10.0s] Welcome to the video."
  ],
  "highlights": [
    {
      "start": 3.0,
      "end": 8.0,
      "text": "Exciting moment"
    }
  ],
  "audio_url": "/files/audio.wav"
}
```

---

## 🛠️ Customization

- Replace `detect_motion_spikes`, `detect_bright_spikes`, and `transcribe_audio` with your own logic as needed.
- Customize the frontend in `upload.html` and `play.html` to match your branding.
- Adjust highlight generation thresholds in `transformer.py`.

