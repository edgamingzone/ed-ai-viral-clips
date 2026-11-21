---
title: ED AI VIRAL CLIPS
emoji: 🎬
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 7860
---

# ED AI VIRAL CLIPS

A beginner-friendly first version that turns an uploaded, authorized video into vertical MP4 clips.

## Run locally
1. Install Python 3.11 and FFmpeg.
2. Run `pip install -r requirements.txt`
3. Run `streamlit run app.py`

## Deploy free (subject to platform limits)
Create a new Hugging Face Space and choose **Docker**. Upload `app.py`, `requirements.txt`, and `Dockerfile`.

## Current MVP limitations
- Uploads only; it does not download arbitrary YouTube videos.
- Scene-change detection is a basic editing aid, not a guarantee of viral performance.
- No automatic captions, speech understanding, or face tracking yet.
- Use only videos you own, have permission to edit, or are licensed for reuse.
