from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse, FileResponse
import subprocess
import os
import uuid

app = FastAPI()

@app.get("/")
def root():
    return {"status": "ok"}

@app.get("/convert")
def convert(url: str = Query(...)):
    video_id = str(uuid.uuid4())
    os.makedirs(video_id, exist_ok=True)

    video_path = f"{video_id}/video.mp4"
    audio_path = f"{video_id}/audio.mp3"
    frames_path = f"{video_id}/frames_%04d.png"

    # Descargar el video
    subprocess.run([
        "yt-dlp",
        "-f", "bv*+ba/b",
        "-o", video_path,
        url
    ])

    # Extraer audio
    subprocess.run([
        "ffmpeg", "-i", video_path, "-vn",
        "-acodec", "mp3", audio_path
    ])

    # Convertir a frames
    subprocess.run([
        "ffmpeg", "-i", video_path,
        frames_path
    ])

    frames = sorted(f for f in os.listdir(video_id) if f.endswith(".png"))

    return JSONResponse({
        "id": video_id,
        "audio": f"/audio/{video_id}",
        "frames": [f"/frame/{video_id}/{f}" for f in frames]
    })

@app.get("/audio/{folder}")
def get_audio(folder: str):
    return FileResponse(f"{folder}/audio.mp3")

@app.get("/frame/{folder}/{filename}")
def get_frame(folder: str, filename: str):
    return FileResponse(f"{folder}/{filename}")
