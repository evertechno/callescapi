import streamlit as st
import requests
from io import BytesIO

# Define the API endpoint
API_URL = "https://escalyticsv4api.onrender.com/analyze_email"

# Function to send email content and attachment to the API
def analyze_email_content(email_content, selected_scenario, attachment):
    # Prepare data for the request
    data = {
        "email_content": email_content,
        "selected_scenario": selected_scenario
    }

    # Prepare files for the request (if any attachment is provided)
    files = {}
    if attachment:
        files = {
            'attachment': attachment
        }

    # Send the request to the API
    response = requests.post(API_URL, json=data, files=files)

    # Return the response data
    return response.json()

# Streamlit app
def main():
    st.title("Email Content Analyzer")

    # Create a form to input the email content
    with st.form(key='email_form'):
        email_content = st.text_area("Enter Email Content", height=200)
        selected_scenario = st.selectbox("Select Scenario", [
            "General Feedback", "Task Request", "Complaint", "Information Request"
        ])
        attachment = st.file_uploader("Upload an Attachment", type=["txt", "pdf", "docx"])

        submit_button = st.form_submit_button("Analyze")

    # When the form is submitted, analyze the email content
    if submit_button:
        if not email_content:
            st.error("Please provide the email content.")
        else:
            # Call the API to analyze the email content
            with st.spinner("Analyzing..."):
                result = analyze_email_content(email_content, selected_scenario, attachment)

            # Display the results
            if "error" in result:
                st.error(f"Error: {result['error']}")
            else:
                st.subheader("Analysis Results")
                st.write("**Summary:**", result.get("summary", "Not Available"))
                st.write("**Response:**", result.get("response", "Not Available"))
                st.write("**Highlights:**", result.get("highlights", "Not Available"))
                st.write("**Sentiment:**", result.get("sentiment", "Not Available"))
                st.write("**Tone:**", result.get("tone", "Not Available"))
                st.write("**Tasks:**", result.get("tasks", "Not Available"))
                st.write("**Subject Recommendation:**", result.get("subject_recommendation", "Not Available"))
                st.write("**Grammar Issues:**", result.get("grammar_issues", "Not Available"))
                st.write("**Clarity Score:**", result.get("clarity_score", "Not Available"))
                st.write("**Professionalism Score:**", result.get("professionalism_score", "Not Available"))
                st.write("**Complexity Reduction:**", result.get("complexity_reduction", "Not Available"))
                st.write("**Scenario Response:**", result.get("scenario_response", "Not Available"))
                st.write("**Attachment Analysis:**", result.get("attachment_analysis", "Not Available"))

# Run the Streamlit app
if __name__ == "__main__":
    main()
