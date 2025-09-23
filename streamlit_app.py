# app.py
import os
import io
import time
import uuid
import json
import requests
import threading
import tempfile
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

import streamlit as st
from supabase import create_client

# Optional: Google GenAI import
import base64
from google import genai
from google.genai import types

# ---------------------------
# Config & secrets
# ---------------------------
st.set_page_config(page_title="VoiceScribe", page_icon="🎙️", layout="wide")

SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
CLOUDFLARE_ACCOUNT_ID = st.secrets["CLOUDFLARE_ACCOUNT_ID"]
CLOUDFLARE_TOKEN = st.secrets["CLOUDFLARE_TOKEN"]
# GENIE/GEMINI API key can also be provided via env var (google.genai library expects env or direct)
GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY") or os.environ.get("GEMINI_API_KEY")

if GEMINI_API_KEY:
    os.environ["GEMINI_API_KEY"] = GEMINI_API_KEY

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Constants
BUCKET_NAME = "voice-recordings"

# ---------------------------
# Helpers
# ---------------------------
def supabase_sign_up(email: str, password: str):
    """Sign up a user (returns session or error)"""
    res = supabase.auth.sign_up({"email": email, "password": password})
    return res

def supabase_sign_in(email: str, password: str):
    """Sign in user (returns user session)"""
    res = supabase.auth.sign_in_with_password({"email": email, "password": password})
    return res

def get_current_user():
    return supabase.auth.get_user()

def upload_to_supabase_storage(user_id: str, filename: str, file_bytes: bytes):
    """Upload binary audio to storage path user_id/filename and return public object info (private bucket)"""
    path = f"{user_id}/{filename}"
    # supabase.storage.from_(BUCKET_NAME).upload expects a file-like object or path depending on SDK version.
    # We will write to a temp file and upload from disk (robust across SDK versions).
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp.write(file_bytes)
        tmp.flush()
        tmp_path = tmp.name

    # Upload
    storage = supabase.storage()
    # Remove existing if conflict
    try:
        storage.from_(BUCKET_NAME).upload(path, tmp_path, {"cacheControl": "3600"})
    except Exception as e:
        # If object exists, replace
        storage.from_(BUCKET_NAME).update(path, tmp_path)

    return path

def insert_voice_recording_row(user_id: str, filename: str, path: str, size: int, file_type: str, duration_seconds=None):
    row = {
        "user_id": user_id,
        "file_name": filename,
        "file_path": path,
        "file_size": size,
        "file_type": file_type,
        "duration_seconds": duration_seconds,
        "processing_status": "uploaded",
        "transcription_status": "pending",
        "analysis_status": "pending",
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat()
    }
    resp = supabase.table("voice_recordings").insert(row).execute()
    return resp

def call_cloudflare_transcribe(local_file_path: str):
    """
    Calls Cloudflare Deepgram nova-3 endpoint. Returns dict containing transcription & raw response.
    Equivalent to:
    curl -X POST 'https://api.cloudflare.com/client/v4/accounts/{ACCOUNT_ID}/ai/run/@cf/deepgram/nova-3?detect_language=true' \
        -H "Authorization: Bearer {TOKEN}" -H "Content-Type: audio/mpeg" --data-binary "@/path/to/file.mp3"
    """
    url = f"https://api.cloudflare.com/client/v4/accounts/{CLOUDFLARE_ACCOUNT_ID}/ai/run/@cf/deepgram/nova-3"
    params = {"detect_language": "true"}
    headers = {
        "Authorization": f"Bearer {CLOUDFLARE_TOKEN}",
        # Do not set Content-Length manually; requests will handle it
        "Content-Type": "application/octet-stream",  # audio/mpeg also acceptable
    }

    with open(local_file_path, "rb") as f:
        resp = requests.post(url, params=params, headers=headers, data=f, timeout=120)
    try:
        body = resp.json()
    except Exception:
        body = {"raw_text": resp.text, "status_code": resp.status_code}
    return {"status_code": resp.status_code, "body": body, "ok": resp.ok}

def insert_transcription(user_id: str, recording_id: str, transcription_text: str, confidence_score=None, detected_language=None, cloudflare_response=None, processing_time_ms=None):
    row = {
        "user_id": user_id,
        "recording_id": recording_id,
        "transcription_text": transcription_text,
        "confidence_score": confidence_score,
        "detected_language": detected_language,
        "processing_time_ms": processing_time_ms,
        "cloudflare_response": cloudflare_response,
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat()
    }
    resp = supabase.table("voice_transcriptions").insert(row).execute()
    return resp

def analyze_with_gemini(user_id: str, recording_id: str, transcription_id: str, transcription_text: str):
    """
    Run analysis via Google GenAI per your provided safety settings. Returns AI response object.
    """
    client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
    model = "gemini-2.5-pro"

    prompt = f"""
You are a compliance analysis assistant. Analyze the transcription below for compliance risk, breaches,
regulatory violations, and produce:
1) compliance_score (0-100),
2) risk_level (low, medium, high),
3) compliance_breaches (array of objects with {{"type","excerpt","explanation"}}),
4) recommendations (array of short strings),
5) short analysis_summary (2-4 sentences).

Transcription:
\"\"\"{transcription_text}\"\"\"
Be concise and return ONLY JSON in the final answer with keys:
compliance_score, risk_level, compliance_breaches, recommendations, analysis_summary.
"""

    contents = [
        types.Content(role="user", parts=[types.Part.from_text(prompt)])
    ]
    generate_content_config = types.GenerateContentConfig(
        thinking_config=types.ThinkingConfig(thinking_budget=-1),
        safety_settings=[
            types.SafetySetting(category="HARM_CATEGORY_HARASSMENT", threshold="BLOCK_LOW_AND_ABOVE"),
            types.SafetySetting(category="HARM_CATEGORY_HATE_SPEECH", threshold="BLOCK_LOW_AND_ABOVE"),
            types.SafetySetting(category="HARM_CATEGORY_SEXUALLY_EXPLICIT", threshold="BLOCK_LOW_AND_ABOVE"),
            types.SafetySetting(category="HARM_CATEGORY_DANGEROUS_CONTENT", threshold="BLOCK_LOW_AND_ABOVE"),
        ],
    )

    # We will stream and accumulate text
    result_text = ""
    for chunk in client.models.generate_content_stream(model=model, contents=contents, config=generate_content_config):
        # chunk may be partial text
        if hasattr(chunk, "text") and chunk.text:
            result_text += chunk.text

    # Try parse JSON from result_text (user prompt requested JSON)
    try:
        ai_json = json.loads(result_text)
    except Exception:
        # if not parseable, include as raw text
        ai_json = {"raw_text": result_text}

    # Insert into DB
    analysis_row = {
        "user_id": user_id,
        "recording_id": recording_id,
        "transcription_id": transcription_id,
        "compliance_score": ai_json.get("compliance_score") if isinstance(ai_json, dict) else None,
        "risk_level": ai_json.get("risk_level") if isinstance(ai_json, dict) else "unknown",
        "compliance_breaches": ai_json.get("compliance_breaches") if isinstance(ai_json, dict) else [],
        "regulatory_violations": ai_json.get("regulatory_violations") if isinstance(ai_json, dict) else [],
        "recommendations": ai_json.get("recommendations") if isinstance(ai_json, dict) else [],
        "analysis_summary": ai_json.get("analysis_summary") if isinstance(ai_json, dict) else result_text[:200],
        "flagged_content": [],
        "ai_analysis_response": ai_json,
        "processing_time_ms": None,
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
    }
    resp = supabase.table("voice_compliance_analysis").insert(analysis_row).execute()
    return ai_json, resp

# ---------------------------
# UI
# ---------------------------
st.title("🎙️ VoiceScribe — Upload · Transcribe · Analyze")
st.markdown("Login with email/password (Supabase Auth). Upload an audio file (mp3/wav). We will transcribe using Cloudflare Deepgram and analyze with Gemini.")

# Authentication
auth_tab, upload_tab = st.tabs(["Login / Signup", "Upload & Process"])
with auth_tab:
    st.subheader("Sign in or create account")
    auth_mode = st.radio("Action", ["Sign in", "Sign up"])
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")
    if st.button("Go"):
        if not email or not password:
            st.error("Enter email and password.")
        else:
            try:
                if auth_mode == "Sign up":
                    res = supabase_sign_up(email, password)
                    st.success("Sign-up request submitted. Check your email to confirm if required by Supabase.")
                    st.write(res)
                else:
                    res = supabase_sign_in(email, password)
                    if res and res.get("data", {}).get("user"):
                        st.success("Signed in successfully.")
                        st.experimental_rerun()
                    else:
                        st.error("Sign-in failed. Check credentials.")
                        st.write(res)
            except Exception as e:
                st.exception(e)

# Upload & Process (requires authenticated user)
with upload_tab:
    current_user = None
    try:
        # supabase.auth.get_user() returns dict with user if session present
        u = get_current_user()
        if u and u.get("data") and u["data"].get("user"):
            current_user = u["data"]["user"]
    except Exception:
        current_user = None

    if not current_user:
        st.warning("Please sign in using the 'Login / Signup' tab first.")
    else:
        user_id = current_user["id"]
        st.success(f"Signed in as: {current_user.get('email')}")
        uploaded_file = st.file_uploader("Upload audio (mp3/wav/m4a) — max 50MB", type=["mp3", "wav", "m4a"], accept_multiple_files=False)
        filename_override = st.text_input("Optional: save as filename (e.g. call_123.mp3)")
        if uploaded_file:
            filename = filename_override.strip() or uploaded_file.name
            file_bytes = uploaded_file.read()
            file_size = len(file_bytes)
            file_type = uploaded_file.type or "audio/mpeg"
            st.write(f"File: {filename} — {file_size} bytes — type: {file_type}")

            if st.button("Upload & Process"):
                progress_text = st.empty()
                progress_bar = st.progress(0)

                def worker_process():
                    try:
                        progress_text.text("Uploading to Supabase storage...")
                        progress_bar.progress(5)

                        # Upload to storage
                        path = upload_to_supabase_storage(user_id, filename, file_bytes)
                        progress_bar.progress(20)
                        progress_text.text("Saving metadata to DB...")
                        inserted = insert_voice_recording_row(user_id, filename, path, file_size, file_type)
                        progress_bar.progress(30)

                        # Get recording id (supabase returns inserted row)
                        recording_id = None
                        try:
                            recording_id = inserted.get("data")[0].get("id")
                        except Exception:
                            recording_id = str(uuid.uuid4())

                        progress_text.text("Downloading to a temp file for transcription...")
                        # create tmp file
                        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(filename)[1]) as tmp:
                            tmp.write(file_bytes)
                            tmp.flush()
                            local_path = tmp.name

                        progress_text.text("Calling Cloudflare transcription...")
                        start_ts = time.time()
                        cf_resp = call_cloudflare_transcribe(local_path)
                        elapsed_ms = int((time.time() - start_ts) * 1000)
                        progress_bar.progress(60)

                        # Extract transcription text (varies by provider). Try common locations:
                        transcription_text = ""
                        detected_language = None
                        confidence = None
                        cf_body = cf_resp["body"]
                        # heuristics to find text in Cloudflare/Deepgram result
                        if isinstance(cf_body, dict):
                            # multiple shapes are possible; try common keys
                            if "result" in cf_body and isinstance(cf_body["result"], dict):
                                transcription_text = cf_body["result"].get("transcript") or cf_body["result"].get("text") or ""
                            if not transcription_text:
                                # Deepgram like: {"results": {"channels": [{"alternatives":[{"transcript":"..."}]}]}}
                                results = cf_body.get("results")
                                if results:
                                    try:
                                        channels = results.get("channels") or []
                                        if channels:
                                            alts = channels[0].get("alternatives") or []
                                            if alts:
                                                transcription_text = alts[0].get("transcript", "")
                                    except Exception:
                                        pass
                            # fallback: top-level text fields
                            transcription_text = transcription_text or cf_body.get("transcript") or cf_body.get("text") or ""
                            detected_language = cf_body.get("detected_language") or cf_body.get("language")
                        else:
                            transcription_text = str(cf_body)

                        progress_text.text("Storing transcription in DB...")
                        t_ins = insert_transcription(user_id=user_id,
                                                     recording_id=recording_id,
                                                     transcription_text=transcription_text,
                                                     confidence_score=confidence,
                                                     detected_language=detected_language,
                                                     cloudflare_response=cf_body,
                                                     processing_time_ms=elapsed_ms)
                        progress_bar.progress(80)

                        # get transcription id
                        transcription_id = None
                        try:
                            transcription_id = t_ins.get("data")[0].get("id")
                        except Exception:
                            transcription_id = str(uuid.uuid4())

                        progress_text.text("Running AI compliance analysis (Gemini)...")
                        ai_json, ai_db_resp = analyze_with_gemini(user_id=user_id,
                                                                 recording_id=recording_id,
                                                                 transcription_id=transcription_id,
                                                                 transcription_text=transcription_text)
                        progress_bar.progress(95)
                        progress_text.text("Done. All records saved.")
                        progress_bar.progress(100)
                        st.success("Processing complete.")
                        st.write("Transcription:")
                        st.code(transcription_text[:4000])
                        st.write("AI Analysis (summary):")
                        if isinstance(ai_json, dict):
                            st.json(ai_json)
                        else:
                            st.write(ai_json)
                    except Exception as e:
                        st.exception(e)
                        progress_text.text("Error during processing.")

                # Run the worker in a separate thread so Streamlit UI doesn't freeze
                executor = ThreadPoolExecutor(max_workers=1)
                executor.submit(worker_process)
