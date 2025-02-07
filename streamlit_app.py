import streamlit as st
import requests
import json

# API URL of your Flask-based app hosted on Streamlit (replace this with the correct URL)
API_URL = "https://escapi.streamlit.app/"

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
            "email_content": email_text
        }
        
        # Initialize a dictionary to store the responses
        analysis_results = {}

        try:
            # 1. Sentiment Analysis
            sentiment_response = requests.post(f"{API_URL}/api/sentiment", json=email_data)
            if sentiment_response.status_code == 200:
                analysis_results["sentiment"] = sentiment_response.json()
            else:
                st.error(f"Sentiment analysis failed. Status code: {sentiment_response.status_code}")

            # 2. Summary
            summary_response = requests.post(f"{API_URL}/api/summary", json=email_data)
            if summary_response.status_code == 200:
                analysis_results["summary"] = summary_response.json()
            else:
                st.error(f"Summary generation failed. Status code: {summary_response.status_code}")

            # 3. Key Phrases
            key_phrases_response = requests.post(f"{API_URL}/api/key_phrases", json=email_data)
            if key_phrases_response.status_code == 200:
                analysis_results["key_phrases"] = key_phrases_response.json()
            else:
                st.error(f"Key phrases extraction failed. Status code: {key_phrases_response.status_code}")

            # 4. Actionable Items
            actionable_items_response = requests.post(f"{API_URL}/api/actionable_items", json=email_data)
            if actionable_items_response.status_code == 200:
                analysis_results["actionable_items"] = actionable_items_response.json()
            else:
                st.error(f"Actionable items extraction failed. Status code: {actionable_items_response.status_code}")

            # 5. Root Cause
            root_cause_response = requests.post(f"{API_URL}/api/root_cause", json=email_data)
            if root_cause_response.status_code == 200:
                analysis_results["root_cause"] = root_cause_response.json()
            else:
                st.error(f"Root cause detection failed. Status code: {root_cause_response.status_code}")

            # 6. Culprit Identification
            culprit_response = requests.post(f"{API_URL}/api/culprit", json=email_data)
            if culprit_response.status_code == 200:
                analysis_results["culprit"] = culprit_response.json()
            else:
                st.error(f"Culprit identification failed. Status code: {culprit_response.status_code}")

            # 7. Trend Analysis
            trend_analysis_response = requests.post(f"{API_URL}/api/trends", json=email_data)
            if trend_analysis_response.status_code == 200:
                analysis_results["trends"] = trend_analysis_response.json()
            else:
                st.error(f"Trend analysis failed. Status code: {trend_analysis_response.status_code}")

            # 8. Risk Assessment
            risk_assessment_response = requests.post(f"{API_URL}/api/risk", json=email_data)
            if risk_assessment_response.status_code == 200:
                analysis_results["risk"] = risk_assessment_response.json()
            else:
                st.error(f"Risk assessment failed. Status code: {risk_assessment_response.status_code}")

            # 9. Severity Detection
            severity_response = requests.post(f"{API_URL}/api/severity", json=email_data)
            if severity_response.status_code == 200:
                analysis_results["severity"] = severity_response.json()
            else:
                st.error(f"Severity detection failed. Status code: {severity_response.status_code}")

            # 10. Critical Keywords
            critical_keywords_response = requests.post(f"{API_URL}/api/critical_keywords", json=email_data)
            if critical_keywords_response.status_code == 200:
                analysis_results["critical_keywords"] = critical_keywords_response.json()
            else:
                st.error(f"Critical keyword identification failed. Status code: {critical_keywords_response.status_code}")

            # Now displaying results
            if "summary" in analysis_results:
                st.subheader("Summary")
                st.write(analysis_results["summary"].get("summary", "No summary available"))

            if "sentiment" in analysis_results:
                sentiment = analysis_results["sentiment"]
                st.subheader("Sentiment Analysis")
                st.write(f"Sentiment: {sentiment.get('sentiment', 'Unknown')}")
                st.write(f"Sentiment Score: {sentiment.get('score', 'N/A')}")

            if "key_phrases" in analysis_results:
                st.subheader("Key Phrases")
                st.write(analysis_results["key_phrases"].get("key_phrases", "No key phrases available"))

            if "actionable_items" in analysis_results:
                st.subheader("Actionable Items")
                st.write(analysis_results["actionable_items"].get("actionable_items", "No actionable items available"))

            if "root_cause" in analysis_results:
                st.subheader("Root Cause")
                st.write(analysis_results["root_cause"].get("root_cause", "No root cause detected"))

            if "culprit" in analysis_results:
                st.subheader("Culprit")
                st.write(analysis_results["culprit"].get("culprit", "No culprit identified"))

            if "trends" in analysis_results:
                st.subheader("Trend Analysis")
                st.write(analysis_results["trends"].get("trends", "No trends detected"))

            if "risk" in analysis_results:
                st.subheader("Risk Assessment")
                st.write(analysis_results["risk"].get("risk", "No risk assessment provided"))

            if "severity" in analysis_results:
                st.subheader("Severity Detection")
                st.write(analysis_results["severity"].get("severity", "No severity detected"))

            if "critical_keywords" in analysis_results:
                st.subheader("Critical Keywords")
                st.write(analysis_results["critical_keywords"].get("critical_keywords", "No critical keywords detected"))

        except Exception as e:
            st.error(f"An error occurred while calling the API: {str(e)}")
    else:
        st.warning("Please enter an email text to analyze.")
