# app.py
import os
import time
import json
import tempfile
import re
from datetime import datetime

import streamlit as st
from supabase import create_client
from google import genai
from google.genai import types
import requests

# ---------------------------
# Fix inotify file watcher issue (cloud safe)
# ---------------------------
os.environ["STREAMLIT_SERVER_FILE_WATCHER_TYPE"] = "none"

# ---------------------------
# Config & secrets
# ---------------------------
st.set_page_config(page_title="VoiceScribe", page_icon="🎙️", layout="wide")

SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
CLOUDFLARE_ACCOUNT_ID = st.secrets["CLOUDFLARE_ACCOUNT_ID"]
CLOUDFLARE_TOKEN = st.secrets["CLOUDFLARE_TOKEN"]
GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY") or os.environ.get("GEMINI_API_KEY")

if GEMINI_API_KEY:
    os.environ["GEMINI_API_KEY"] = GEMINI_API_KEY

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
BUCKET_NAME = "voice-recordings"

# ---------------------------
# Helpers
# ---------------------------
def supabase_sign_up(email: str, password: str):
    return supabase.auth.sign_up({"email": email, "password": password})

def supabase_sign_in(email: str, password: str):
    return supabase.auth.sign_in_with_password({"email": email, "password": password})

def get_current_user():
    return supabase.auth.get_user()

def upload_to_supabase_storage(user_id: str, filename: str, file_bytes: bytes):
    path = f"{user_id}/{filename}"
    try:
        supabase.storage.from_(BUCKET_NAME).upload(path, file_bytes)
    except Exception:
        supabase.storage.from_(BUCKET_NAME).update(path, file_bytes)
    return path

def insert_voice_recording_row(user_id, filename, path, size, file_type):
    row = {
        "user_id": user_id,
        "file_name": filename,
        "file_path": path,
        "file_size": size,
        "file_type": file_type,
        "processing_status": "uploaded",
        "transcription_status": "pending",
        "analysis_status": "pending",
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
    }
    return supabase.table("voice_recordings").insert(row).execute()

def call_cloudflare_transcribe(local_file_path: str):
    url = f"https://api.cloudflare.com/client/v4/accounts/{CLOUDFLARE_ACCOUNT_ID}/ai/run/@cf/deepgram/nova-3"
    params = {"detect_language": "true"}
    headers = {
        "Authorization": f"Bearer {CLOUDFLARE_TOKEN}",
        "Content-Type": "application/octet-stream",
    }
    with open(local_file_path, "rb") as f:
        resp = requests.post(url, params=params, headers=headers, data=f, timeout=120)
    try:
        body = resp.json()
    except Exception:
        body = {"raw_text": resp.text, "status_code": resp.status_code}
    return {"status_code": resp.status_code, "body": body, "ok": resp.ok}

def insert_transcription(user_id, recording_id, transcription_text, cloudflare_response, processing_time_ms=None):
    row = {
        "user_id": user_id,
        "recording_id": recording_id,
        "transcription_text": transcription_text,
        "cloudflare_response": cloudflare_response,
        "processing_time_ms": processing_time_ms,
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
    }
    return supabase.table("voice_transcriptions").insert(row).execute()

def analyze_with_gemini(user_id, recording_id, transcription_id, transcription_text):
    client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
    model = "gemini-2.5-pro"
    prompt = f"""
You are a compliance analysis assistant. Analyze the transcription below for compliance risk,
breaches, regulatory violations, and produce ONLY JSON with:
- compliance_score (0-100)
- risk_level (low, medium, high)
- compliance_breaches (list of objects with type, excerpt, explanation)
- recommendations (list of strings)
- analysis_summary (2-4 sentences)

Transcription:
\"\"\"{transcription_text}\"\"\"
"""
    contents = [types.Content(role="user", parts=[types.Part.from_text(prompt)])]
    config = types.GenerateContentConfig(
        thinking_config=types.ThinkingConfig(thinking_budget=-1),
        safety_settings=[
            types.SafetySetting(category="HARM_CATEGORY_HARASSMENT", threshold="BLOCK_LOW_AND_ABOVE"),
            types.SafetySetting(category="HARM_CATEGORY_HATE_SPEECH", threshold="BLOCK_LOW_AND_ABOVE"),
            types.SafetySetting(category="HARM_CATEGORY_SEXUALLY_EXPLICIT", threshold="BLOCK_LOW_AND_ABOVE"),
            types.SafetySetting(category="HARM_CATEGORY_DANGEROUS_CONTENT", threshold="BLOCK_LOW_AND_ABOVE"),
        ],
    )
    result_text = ""
    for chunk in client.models.generate_content_stream(model=model, contents=contents, config=config):
        if hasattr(chunk, "text") and chunk.text:
            result_text += chunk.text

    # Extract JSON safely
    try:
        match = re.search(r"\{.*\}", result_text, re.S)
        if match:
            ai_json = json.loads(match.group(0))
        else:
            ai_json = {"raw_text": result_text}
    except Exception:
        ai_json = {"raw_text": result_text}

    analysis_row = {
        "user_id": user_id,
        "recording_id": recording_id,
        "transcription_id": transcription_id,
        "compliance_score": ai_json.get("compliance_score"),
        "risk_level": ai_json.get("risk_level"),
        "compliance_breaches": ai_json.get("compliance_breaches"),
        "recommendations": ai_json.get("recommendations"),
        "analysis_summary": ai_json.get("analysis_summary"),
        "ai_analysis_response": ai_json,
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
    }
    supabase.table("voice_compliance_analysis").insert(analysis_row).execute()
    return ai_json

def extract_transcription_text(cf_body):
    """Try multiple keys where Deepgram may store transcription text"""
    if not isinstance(cf_body, dict):
        return str(cf_body)
    return (
        cf_body.get("transcript")
        or cf_body.get("text")
        or cf_body.get("results", {})
            .get("channels", [{}])[0]
            .get("alternatives", [{}])[0]
            .get("transcript", "")
    )

# ---------------------------
# UI
# ---------------------------
st.title("🎙️ VoiceScribe — Upload · Transcribe · Analyze")

auth_tab, upload_tab = st.tabs(["Login / Signup", "Upload & Process"])

with auth_tab:
    st.subheader("Authentication")
    auth_mode = st.radio("Action", ["Sign in", "Sign up"])
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")
    if st.button("Go"):
        if not email or not password:
            st.error("Enter both email and password.")
        else:
            try:
                if auth_mode == "Sign up":
                    res = supabase_sign_up(email, password)
                    st.success("Sign-up request submitted.")
                    st.json(res.model_dump())
                else:
                    res = supabase_sign_in(email, password)
                    if res and res.user:
                        st.success("Signed in successfully.")
                        st.session_state["user"] = res.user.model_dump()
                        st.experimental_rerun()
                    else:
                        st.error("Sign-in failed.")
                        st.json(res.model_dump())
            except Exception as e:
                st.exception(e)

with upload_tab:
    user = st.session_state.get("user")
    if not user:
        st.warning("Please sign in first.")
    else:
        user_id = user["id"]
        st.success(f"Signed in as {user['email']}")

        uploaded_file = st.file_uploader("Upload audio", type=["mp3", "wav", "m4a"])
        if uploaded_file and st.button("Upload & Process"):
            filename = uploaded_file.name
            file_bytes = uploaded_file.read()
            file_size = len(file_bytes)
            file_type = uploaded_file.type or "audio/mpeg"

            progress_text = st.empty()
            progress_bar = st.progress(0)

            try:
                # Upload to Supabase
                progress_text.text("Uploading...")
                path = upload_to_supabase_storage(user_id, filename, file_bytes)
                inserted = insert_voice_recording_row(user_id, filename, path, file_size, file_type)
                recording_id = inserted.data[0]["id"]
                progress_bar.progress(20)

                # Save locally for Cloudflare
                with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(filename)[1]) as tmp:
                    tmp.write(file_bytes)
                    tmp.flush()
                    local_path = tmp.name

                # Transcribe
                progress_text.text("Transcribing...")
                start = time.time()
                cf_resp = call_cloudflare_transcribe(local_path)
                elapsed = int((time.time() - start) * 1000)
                cf_body = cf_resp["body"]

                transcription_text = extract_transcription_text(cf_body)

                t_ins = insert_transcription(user_id, recording_id, transcription_text, cf_body, elapsed)
                transcription_id = t_ins.data[0]["id"]
                progress_bar.progress(60)

                # Analyze
                progress_text.text("Analyzing...")
                ai_json = analyze_with_gemini(user_id, recording_id, transcription_id, transcription_text)
                progress_bar.progress(100)

                st.success("Complete!")
                st.subheader("Transcription")
                st.code(transcription_text[:4000])
                st.subheader("AI Compliance Analysis")
                st.json(ai_json)

            except Exception as e:
                st.exception(e)
                progress_text.text("Error.")
