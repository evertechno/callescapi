import streamlit as st
import requests
from io import BytesIO

# API endpoint
API_URL = "https://escalyticsv4api.onrender.com/analyze_email"

# Streamlit UI
st.title("Email Content Analyzer")

# Text input for the email content
email_content = st.text_area("Enter Email Content", height=250)

# Dropdown for selecting a scenario
scenarios = ["General Feedback", "Request for Information", "Complaint", "Response to Complaint"]
selected_scenario = st.selectbox("Select Scenario", scenarios)

# File uploader for attachments
uploaded_file = st.file_uploader("Upload Attachment (PDF, DOCX, TXT)", type=["pdf", "docx", "txt"])

# Submit button to send data to the API
if st.button("Analyze Email"):
    if email_content:
        # Prepare data for the API
        files = {"attachment": uploaded_file.getvalue()} if uploaded_file else None
        data = {
            "email_content": email_content,
            "selected_scenario": selected_scenario
        }

        # Make API request
        response = requests.post(API_URL, json=data, files={"attachment": uploaded_file} if uploaded_file else None)

        if response.status_code == 200:
            result = response.json()

            # Display results
            st.subheader("Analysis Results")
            st.write("### Summary")
            st.write(result.get("summary"))
            st.write("### Response")
            st.write(result.get("response"))
            st.write("### Highlights")
            st.write(result.get("highlights"))
            st.write("### Sentiment")
            st.write(f"Polarity: {result.get('sentiment')}")
            st.write("### Tone")
            st.write(result.get("tone"))
            st.write("### Tasks")
            st.write(result.get("tasks"))
            st.write("### Grammar Issues")
            st.write(result.get("grammar_issues"))
            st.write("### Professionalism Score")
            st.write(result.get("professionalism_score"))
            st.write("### Complexity Reduction")
            st.write(result.get("complexity_reduction"))
            st.write("### Attachment Analysis")
            st.write(result.get("attachment_analysis"))

        else:
            st.error("Error in API call: " + response.json().get("error", "Unknown error"))
    else:
        st.error("Please enter the email content.")
