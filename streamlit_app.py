import streamlit as st
import requests
import json

# API URL of your FastAPI hosted on Render
API_URL = "https://escalaticsapi.onrender.com/analyze-email"

# Streamlit UI setup
st.title("Email Content Analyzer")
st.write("Enter the text of an email to get its sentiment analysis, summary, and word cloud data.")

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
                sentiment_label = data.get("sentiment", {}).get("label", "Unknown")
                sentiment_score = data.get("sentiment", {}).get("score", 0)
                st.subheader("Sentiment Analysis")
                st.write(f"Sentiment: {sentiment_label}")
                st.write(f"Sentiment Score: {sentiment_score}")
                
                # Display word cloud data (in this case, it's just word frequency counts)
                wordcloud_data = data.get("wordcloud", {})
                st.subheader("Word Cloud Data")
                st.write(wordcloud_data)
                
            else:
                st.error(f"Failed to analyze email. Status code: {response.status_code}")
                st.write(response.text)
        
        except Exception as e:
            st.error(f"An error occurred while calling the API: {str(e)}")
    else:
        st.warning("Please enter an email text to analyze.")
