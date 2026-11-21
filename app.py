import os
import cv2
import math
import tempfile
import subprocess
import zipfile
from pathlib import Path

import streamlit as st

st.set_page_config(page_title="ED AI VIRAL CLIPS", page_icon="🎬", layout="centered")

st.markdown("""
<style>
.stApp {max-width: 1000px; margin: auto;}
.hero {background: linear-gradient(120deg,#101827,#1d4ed8); padding: 24px; border-radius: 18px; color: white;}
.hero h1 {margin:0; font-size:2rem;}
.hero p {margin:8px 0 0; color:#dbeafe;}
.small-note {color:#64748b; font-size:.9rem;}
</style>
<div class="hero">
<h1>🎬 ED AI VIRAL CLIPS</h1>
<p>Turn your own videos into vertical short clips.</p>
</div>
""", unsafe_allow_html=True)

st.write("")
st.info("First free version: upload a video you own or have permission to edit. It detects visual scene changes and creates vertical clips. Scene detection does not guarantee a clip will go viral.")

uploaded = st.file_uploader("Upload your video", type=["mp4", "mov", "mkv", "avi", "webm"])

c1, c2 = st.columns(2)
with c1:
    clip_len = st.select_slider("Clip length", options=[15, 20, 30, 45, 60], value=30)
with c2:
    clip_count = st.select_slider("Number of clips", options=[1, 2, 3, 4, 5], value=3)

threshold = st.slider("Scene-change sensitivity", min_value=10, max_value=60, value=25, help="Higher values detect fewer scene changes.")
st.caption("Output: MP4, vertical 9:16, suitable for YouTube Shorts / Reels / TikTok.")

def get_scene_candidates(video_path, threshold_value):
    cap = cv2.VideoCapture(str(video_path))
    fps = cap.get(cv2.CAP_PROP_FPS) or 25
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration = total_frames / fps if fps else 0
    if duration <= 0:
        cap.release()
        raise ValueError("Could not read video duration.")
    sample_every = max(1, int(fps * 1.0))
    prev = None
    scores = []
    frame_no = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        if frame_no % sample_every == 0:
            small = cv2.resize(frame, (160, 90))
            hist = cv2.cvtColor(small, cv2.COLOR_BGR2HSV)
            hist = cv2.calcHist([hist], [0, 1], None, [24, 24], [0, 180, 0, 256])
            cv2.normalize(hist, hist)
            if prev is not None:
                score = cv2.compareHist(prev, hist, cv2.HISTCMP_BHATTACHARYYA) * 100
                if score >= threshold_value:
                    scores.append((frame_no / fps, score))
            prev = hist
        frame_no += 1
    cap.release()
    # Keep strongest, well-spaced scene changes.
    selected = []
    for t, score in sorted(scores, key=lambda x: x[1], reverse=True):
        if t > 2 and t < duration - 2 and all(abs(t - old[0]) >= clip_len * 0.75 for old in selected):
            selected.append((t, score))
        if len(selected) >= 30:
            break
    return duration, [x[0] for x in sorted(selected)]

def ffmpeg_clip(source, output, start, length):
    # Center crop to 9:16, scale to 1080x1920, preserve audio.
    vf = "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920"
    cmd = [
        "ffmpeg", "-y", "-ss", str(max(0, start)), "-i", str(source),
        "-t", str(length), "-vf", vf, "-c:v", "libx264", "-preset", "veryfast",
        "-crf", "23", "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart",
        str(output)
    ]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if result.returncode != 0:
        raise RuntimeError(result.stderr[-1800:])

if uploaded:
    st.video(uploaded)
    if st.button("✨ GENERATE MY SHORT CLIPS", type="primary", use_container_width=True):
        with st.spinner("Analyzing scenes and creating vertical clips..."):
            try:
                workdir = Path(tempfile.mkdtemp(prefix="edclips_"))
                source = workdir / uploaded.name
                source.write_bytes(uploaded.getbuffer())
                duration, candidates = get_scene_candidates(source, threshold)
                if duration < clip_len:
                    raise ValueError(f"Video is shorter than selected clip length ({clip_len}s).")
                # Use scene changes as clip centers; if none, use spaced points.
                centers = candidates[:]
                if not centers:
                    centers = [duration * (i + 1) / (clip_count + 1) for i in range(clip_count)]
                starts = []
                for center in centers:
                    start = min(max(0, center - clip_len / 2), max(0, duration - clip_len))
                    if all(abs(start - s) >= clip_len * 0.8 for s in starts):
                        starts.append(start)
                    if len(starts) >= clip_count:
                        break
                # Fill any remaining clips at evenly spaced positions.
                if len(starts) < clip_count:
                    for i in range(clip_count):
                        start = (duration - clip_len) * i / max(1, clip_count - 1)
                        if all(abs(start - s) >= clip_len * 0.8 for s in starts):
                            starts.append(start)
                        if len(starts) >= clip_count:
                            break
                outputs = []
                for i, start in enumerate(starts[:clip_count], 1):
                    out = workdir / f"ED_Viral_Clip_{i}.mp4"
                    ffmpeg_clip(source, out, start, min(clip_len, duration - start))
                    outputs.append(out)
                zip_path = workdir / "ED_AI_VIRAL_CLIPS.zip"
                with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
                    for out in outputs:
                        z.write(out, out.name)
                st.success(f"Done! Created {len(outputs)} vertical clip(s).")
                for out in outputs:
                    st.video(str(out))
                st.download_button(
                    "⬇️ Download all clips (ZIP)",
                    data=zip_path.read_bytes(),
                    file_name="ED_AI_VIRAL_CLIPS.zip",
                    mime="application/zip",
                    use_container_width=True
                )
            except Exception as e:
                st.error(f"Could not process this video: {e}")
else:
    st.markdown("### How to use")
    st.markdown("1. Upload an MP4/MOV video.  2. Choose clip length and quantity.  3. Press **Generate My Short Clips**.  4. Preview and download the ZIP.")
    st.markdown('<p class="small-note">This starter version detects visual scene changes. Automatic speech understanding, captions, face tracking and YouTube URL imports can be added in later versions, subject to source permissions and hosting limits.</p>', unsafe_allow_html=True)
