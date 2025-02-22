import streamlit as st
import requests
from io import BytesIO

# API endpoint
API_URL = "https://escalyticsv4api.onrender.com/analyze_email"
API_KEY = "your_secure_api_key"  # Replace this with your actual API key

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

        headers = {
            "x-api-key": API_KEY
        }

        try:
            # Make API request
            if uploaded_file:
                files = {"attachment": uploaded_file.getvalue()}
                response = requests.post(API_URL, json=data, files=files, headers=headers)
            else:
                response = requests.post(API_URL, json=data, headers=headers)
                
            # Check if the API returned an error
            response.raise_for_status()  # Raise an exception for HTTP errors
            
            # Attempt to parse the JSON response
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

        except requests.exceptions.HTTPError as http_err:
            if response.status_code == 401:
                st.error("Unauthorized: Invalid API Key. Please check your API key.")
            else:
                st.error(f"HTTP error occurred: {http_err}")
        except requests.exceptions.RequestException as req_err:
            st.error(f"Request error occurred: {req_err}")
        except ValueError:
            st.error("Error parsing JSON response. Please check the API response format.")
    else:
        st.error("Please enter the email content.")
