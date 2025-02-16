import streamlit as st
import requests

# URL of your Flask API hosted on Render
API_URL = "https://escalyticsv4api.onrender.com/analyze-email"

def analyze_email(email_content, uploaded_file):
    # Prepare data to send to the Flask API
    headers = {"Content-Type": "application/json"}
    files = {"attachment": uploaded_file} if uploaded_file else None

    data = {
        "email_content": email_content
    }

    try:
        # Send POST request to the API
        response = requests.post(API_URL, json=data, files=files, headers=headers)
        response.raise_for_status()

        # Parse the response
        result = response.json()

        return result
    except requests.exceptions.RequestException as e:
        st.error(f"Error: {e}")
        return None

# Streamlit interface
st.title("Email Analysis")

email_content = st.text_area("Enter the email content:")
uploaded_file = st.file_uploader("Upload an attachment (optional)", type=["txt", "pdf", "docx"])

if st.button("Analyze Email"):
    if email_content:
        result = analyze_email(email_content, uploaded_file)
        if result:
            st.subheader("AI Response")
            st.write(result.get("ai_response"))

            st.subheader("Analysis Results")
            analysis = result.get("analysis", {})
            for key, value in analysis.items():
                st.write(f"{key.capitalize()}: {value}")
        else:
            st.error("There was an error in the analysis.")
    else:
        st.error("Please provide the email content.")
