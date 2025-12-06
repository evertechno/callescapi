import streamlit as st
import requests
import json
import pandas as pd

# ============================================================
# LOAD SECRETS
# ============================================================
API_BASE_URL = st.secrets["API_BASE_URL"]
API_KEY = st.secrets["API_KEY"]

HEADERS = {"x-api-key": API_KEY}

# ============================================================
# ENDPOINT DEFINITIONS
# ============================================================
ENDPOINTS = [
    {
        "category": "Company Data",
        "endpoints": [
            {
                "method": "GET",
                "path": "/companies",
                "description": "Fetch company metadata from NSE or NASDAQ",
                "params": [
                    {"name": "market", "type": "string", "required": False},
                    {"name": "symbol", "type": "string", "required": False},
                    {"name": "sector", "type": "string", "required": False},
                    {"name": "limit", "type": "number", "required": False},
                ],
            }
        ],
    },
    {
        "category": "Financial Statements",
        "endpoints": [
            {
                "method": "GET",
                "path": "/financials",
                "description": "Fetch income/balance/cashflow statements",
                "params": [
                    {"name": "market", "type": "string", "required": False},
                    {"name": "symbol", "type": "string", "required": True},
                    {"name": "statement_type", "type": "string", "required": False},
                    {"name": "limit", "type": "number", "required": False},
                ],
            }
        ],
    },
    {
        "category": "Historical Prices",
        "endpoints": [
            {
                "method": "GET",
                "path": "/prices",
                "description": "Fetch historical OHLC price data",
                "params": [
                    {"name": "market", "type": "string", "required": False},
                    {"name": "symbol", "type": "string", "required": True},
                    {"name": "limit", "type": "number", "required": False},
                ],
            }
        ],
    },
    {
        "category": "Financial Ratios",
        "endpoints": [
            {
                "method": "GET",
                "path": "/ratios",
                "description": "Fetch 100+ financial ratios",
                "params": [
                    {"name": "market", "type": "string", "required": False},
                    {"name": "symbol", "type": "string", "required": True},
                    {"name": "limit", "type": "number", "required": False},
                ],
            }
        ],
    },
    {
        "category": "Compliance (SniffR)",
        "endpoints": [
            {
                "method": "GET",
                "path": "/compliance",
                "description": "Search compliance & penalty records",
                "params": [
                    {"name": "company_name", "type": "string", "required": True},
                    {"name": "limit", "type": "number", "required": False},
                ],
            }
        ],
    },
    {
        "category": "Portfolio",
        "endpoints": [
            {
                "method": "GET",
                "path": "/portfolio",
                "description": "Access your portfolios",
                "params": [
                    {"name": "action", "type": "string", "required": False},
                    {"name": "portfolio_id", "type": "string", "required": False},
                ],
            }
        ],
    },
    {
        "category": "K2 Agent (AI Query)",
        "endpoints": [
            {
                "method": "POST",
                "path": "/agent",
                "description": "Natural language to SQL using AI",
                "params": [
                    {"name": "query", "type": "string", "required": True},
                ],
            }
        ],
    },
    {
        "category": "Reports",
        "endpoints": [
            {
                "method": "GET",
                "path": "/valuation-reports",
                "description": "Get valuation reports",
                "params": [
                    {"name": "limit", "type": "number", "required": False},
                ],
            },
            {
                "method": "GET",
                "path": "/research-reports",
                "description": "Get research reports",
                "params": [
                    {"name": "limit", "type": "number", "required": False},
                ],
            },
        ],
    },
    {
        "category": "Custom SQL",
        "endpoints": [
            {
                "method": "POST",
                "path": "/sql",
                "description": "Execute custom SQL query",
                "params": [
                    {"name": "sql", "type": "string", "required": True},
                ],
            }
        ],
    },
]

# ============================================================
# API CALLER
# ============================================================
def call_api(method, path, params):
    url = f"{API_BASE_URL}{path}"

    if method == "GET":
        response = requests.get(url, headers=HEADERS, params=params)
    elif method == "POST":
        response = requests.post(url, headers={**HEADERS, "Content-Type": "application/json"}, json=params)
    else:
        return {"error": f"Unsupported method {method}"}

    try:
        return response.json()
    except Exception:
        return {"error": "Failed to parse JSON", "raw": response.text}


# ============================================================
# STREAMLIT UI
# ============================================================
st.title("🚀 K2 Hydro DB — API Explorer")
st.caption("A full-featured Streamlit client for your Supabase API Gateway")

tabs = st.tabs(["🔍 API Explorer", "📘 Documentation / User Guide"])

# ============================================================
# TAB 1 — API EXPLORER
# ============================================================
with tabs[0]:

    category = st.selectbox(
        "Select API Category",
        [c["category"] for c in ENDPOINTS]
    )

    selected_cat = next(c for c in ENDPOINTS if c["category"] == category)

    endpoint_name = st.selectbox(
        "Select Endpoint",
        [e["description"] for e in selected_cat["endpoints"]]
    )

    endpoint = next(e for e in selected_cat["endpoints"] if e["description"] == endpoint_name)

    st.subheader(endpoint["description"])
    st.code(f"{endpoint['method']} {endpoint['path']}")

    # Parameter form
    st.write("### Parameters")
    param_values = {}

    for p in endpoint["params"]:
        label = f"{p['name']} ({p['type']})"
        if p["type"] == "number":
            value = st.number_input(label, value=None, step=1, format="%d")
        else:
            value = st.text_input(label)

        if value not in ("", None):
            param_values[p["name"]] = value
        elif p["required"]:
            st.warning(f"⚠️ Required: {p['name']}")

    if st.button("Send Request"):
        with st.spinner("Calling API..."):
            result = call_api(endpoint["method"], endpoint["path"], param_values)

        st.write("### Response")
        st.json(result)

        # DataFrame view for list data
        if isinstance(result, dict) and result.get("success") and isinstance(result.get("data"), list):
            try:
                df = pd.DataFrame(result["data"])
                st.write("### Table View")
                st.dataframe(df)

                csv = df.to_csv(index=False)
                st.download_button("Download CSV", csv, "data.csv", "text/csv")
            except Exception:
                pass


# ============================================================
# TAB 2 — DOCUMENTATION / USER GUIDE
# ============================================================
with tabs[1]:

    st.header("📘 K2 Hydro DB — Complete User Guide")
    
    st.markdown("""
Welcome to **K2 Hydro DB**, a unified API system providing:

### ✅ NSE & NASDAQ Company Metadata  
### ✅ Financial Statements (Income, Balance Sheet, Cashflow)  
### ✅ Historical OHLC Prices  
### ✅ 100+ Financial Ratios  
### ✅ Compliance & Penalty History (SniffR)  
### ✅ Portfolio APIs  
### ✅ AI-powered NL → SQL Query Engine  
### ✅ Custom SQL Execution  
### ✅ Automated Valuation & Research Reports  

---

# 🔑 1. Authentication
All API calls require your API key:

