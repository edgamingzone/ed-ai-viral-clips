import os, re, cv2, zipfile, shutil, tempfile, subprocess
from pathlib import Path
import streamlit as st

st.set_page_config(page_title="ED AI VIRAL CLIPS", page_icon="🎬", layout="centered")
st.title("🎬 ED AI VIRAL CLIPS")
st.subheader("YouTube link to vertical Shorts")
st.write("Paste a video link. The app fetches it on the server and creates vertical clips.")
st.warning("Only use videos you own or have permission to download and edit. Follow YouTube's terms and copyright law. This app does not bypass private videos, DRM, or paywalls.")

url = st.text_input("Paste YouTube video link", placeholder="https://www.youtube.com/watch?v=...")
clip_length = st.select_slider("Clip length (seconds)", options=[15, 30, 45, 60], value=30)
number_clips = st.select_slider("Number of clips", options=[1, 3, 5], value=3)
sensitivity = st.slider("Scene-change sensitivity", 10, 60, 25)

def fetch_video(link, folder):
    if not re.match(r"^https?://(www\.)?(youtube\.com|youtu\.be)/", link.strip()):
        raise ValueError("Please paste a valid YouTube video URL.")
    out = os.path.join(folder, "source.%(ext)s")
    cmd = ["yt-dlp", "--no-playlist", "--max-filesize", "200M", "-f",
           "bv*[height<=720]+ba/b[height<=720]/b", "--merge-output-format", "mp4",
           "-o", out, link.strip()]
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if p.returncode:
        raise RuntimeError((p.stderr or p.stdout or "Could not fetch this video.")[-1600:])
    files = [x for x in Path(folder).glob("source.*") if x.is_file()]
    if not files:
        raise RuntimeError("Video could not be fetched. Try another permitted public video link.")
    return str(max(files, key=lambda x: x.stat().st_size))

def detect_scenes(path, sensitivity):
    cap = cv2.VideoCapture(path)
    if not cap.isOpened(): raise RuntimeError("Could not read the video.")
    fps = cap.get(cv2.CAP_PROP_FPS) or 25
    frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    duration = frames / fps if frames else 0
    starts, prev, idx = [0.0], None, 0
    while True:
        ok, frame = cap.read()
        if not ok: break
        if idx % max(1, int(fps)) == 0:
            gray = cv2.cvtColor(cv2.resize(frame, (160, 90)), cv2.COLOR_BGR2GRAY)
            if prev is not None:
                score = float(cv2.absdiff(gray, prev).mean())
                t = idx / fps
                if score >= sensitivity and t - starts[-1] >= 5: starts.append(t)
            prev = gray
        idx += 1
    cap.release()
    return starts, duration

def create_clips(path, folder, length, count, sensitivity):
    starts, duration = detect_scenes(path, sensitivity)
    if duration <= 0: raise RuntimeError("Could not determine video duration.")
    candidates = [s for s in starts if s + length <= duration]
    candidates += [max(0, min(duration-length, (duration-length)*i/(count+1))) for i in range(1, count+1)]
    selected = []
    for s in candidates:
        if all(abs(s-x) > 3 for x in selected): selected.append(s)
        if len(selected) == count: break
    if not selected: selected = [0]
    results = []
    for i, start in enumerate(selected, 1):
        target = os.path.join(folder, f"ED_Short_{i:02d}.mp4")
        cmd = ["ffmpeg", "-y", "-ss", str(start), "-i", path, "-t", str(length),
               "-vf", "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920",
               "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
               "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", target]
        p = subprocess.run(cmd, capture_output=True, text=True)
        if p.returncode == 0 and os.path.exists(target): results.append(target)
    if not results: raise RuntimeError("No clips created. Try a shorter clip length.")
    return results

if st.button("✨ Generate Shorts", type="primary", use_container_width=True):
    if not url.strip():
        st.error("Please paste a YouTube link first.")
        st.stop()
    folder = tempfile.mkdtemp(prefix="edclips_")
    try:
        with st.spinner("Fetching video on the server..."):
            source = fetch_video(url, folder)
        st.success("Video fetched. Creating vertical clips...")
        with st.spinner("Detecting scenes and generating Shorts..."):
            clips = create_clips(source, folder, clip_length, number_clips, sensitivity)
        st.success(f"Created {len(clips)} clip(s).")
        archive = os.path.join(folder, "ED_AI_VIRAL_CLIPS.zip")
        with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as z:
            for clip in clips: z.write(clip, os.path.basename(clip))
        with open(archive, "rb") as f:
            st.download_button("⬇️ Download all Shorts", f, "ED_AI_VIRAL_CLIPS.zip", "application/zip", use_container_width=True)
        for clip in clips:
            st.video(clip)
            with open(clip, "rb") as f:
                st.download_button(f"Download {os.path.basename(clip)}", f, os.path.basename(clip), "video/mp4")
        st.caption("Basic visual scene-change detection; it does not guarantee viral clips.")
    except subprocess.TimeoutExpired:
        st.error("Fetching took too long. Try a shorter video.")
    except Exception as e:
        st.error(f"Could not process this video: {e}")
    finally:
        shutil.rmtree(folder, ignore_errors=True)
