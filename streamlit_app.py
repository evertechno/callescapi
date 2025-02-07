import streamlit as st
import requests
import json

# API URL of your FastAPI hosted on Render
API_URL = "https://escalaticsapi.onrender.com/analyze-email"

# Streamlit UI setup
st.title("Email Content Analyzer")
st.write("Enter the text of an email to get its sentiment analysis, summary, and more.")

# User input
email_text = st.text_area("Enter Email Text", height=200)

# Button to trigger the analysis
if st.button("Analyze Email"):
    if email_text:
        # Prepare the request payload
        email_data = {
            "email_text": email_text
        }
        
        # Send POST request to the FastAPI endpoint
        try:
            response = requests.post(API_URL, json=email_data)
            
            # Check for successful response
            if response.status_code == 200:
                data = response.json()
                
                # Display summary
                st.subheader("Summary")
                st.write(data.get("summary", "No summary available"))
                
                # Display sentiment analysis
                sentiment = data.get("sentiment", {})
                sentiment_label = sentiment.get("label", "Unknown")
                sentiment_score = sentiment.get("score", 0)
                st.subheader("Sentiment Analysis")
                st.write(f"Sentiment: {sentiment_label}")
                st.write(f"Sentiment Score: {sentiment_score}")
                
                # Display key phrases
                st.subheader("Key Phrases")
                st.write(data.get("key_phrases", "No key phrases available"))
                
                # Display actionable items
                st.subheader("Actionable Items")
                st.write(data.get("actionable_items", "No actionable items available"))
                
                # Display root cause detection
                st.subheader("Root Cause")
                st.write(data.get("root_cause", "No root cause detected"))
                
                # Display culprit identification
                st.subheader("Culprit")
                st.write(data.get("culprit", "No culprit identified"))
                
                # Display trend analysis
                st.subheader("Trend Analysis")
                st.write(data.get("trends", "No trends detected"))
                
                # Display risk assessment
                st.subheader("Risk Assessment")
                st.write(data.get("risk", "No risk assessment provided"))
                
                # Display severity detection
                st.subheader("Severity Detection")
                st.write(data.get("severity", "No severity detected"))
                
                # Display critical keyword identification
                st.subheader("Critical Keywords")
                st.write(data.get("critical_keywords", "No critical keywords detected"))
                
            else:
                st.error(f"Failed to analyze email. Status code: {response.status_code}")
                st.write(response.text)
        
        except Exception as e:
            st.error(f"An error occurred while calling the API: {str(e)}")
    else:
        st.warning("Please enter an email text to analyze.")
