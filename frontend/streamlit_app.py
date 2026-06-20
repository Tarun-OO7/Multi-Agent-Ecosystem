import streamlit as st
import os
import sys
import uuid
import pandas as pd
import plotly.express as px
from pathlib import Path

# Add the parent directory to sys.path to allow importing 'agents' and 'utils'
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from agents.coordinator import coordinator_agent
from utils.security import detect_prompt_injection, RateLimiter, validate_file_security

# Initialize global state and rate limiter
if 'rate_limiter' not in st.session_state:
    st.session_state.rate_limiter = RateLimiter(max_requests=5, time_window=60)

if 'session_id' not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

st.set_page_config(page_title="SME BI Dashboard", layout="wide")
st.title("Enterprise BI & Multi-Agent Dashboard")

# --- Sidebar: Upload & Quick Metrics ---
st.sidebar.header("Data Upload")
uploaded_file = st.sidebar.file_uploader("Upload Business Data", type=['csv', 'xlsx', 'xls'])

data_path = None

if uploaded_file is not None:
    # 1. Zero-overhead file security validation
    if not validate_file_security(uploaded_file):
        st.sidebar.error("🚨 Security Alert: Invalid file signature detected. Operation blocked.")
    else:
        # Save to a unique session folder inside data/
        session_dir = Path(f"./data/{st.session_state.session_id}")
        session_dir.mkdir(parents=True, exist_ok=True)
        file_path = session_dir / uploaded_file.name
        
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        st.sidebar.success("File uploaded and secured!")
        data_path = str(file_path)
        
        # 2. Read data and show quick local tool previews and Plotly charts
        try:
            if uploaded_file.name.endswith('.csv'):
                df = pd.read_csv(data_path)
            else:
                df = pd.read_excel(data_path)
                
            st.sidebar.subheader("Quick Data Overview")
            st.sidebar.dataframe(df.head(3))
            
            # Simple Plotly Chart (Zero LLM token cost)
            numeric_cols = df.select_dtypes(include=['number']).columns
            if len(numeric_cols) > 0 and 'Date' in df.columns:
                fig = px.line(df, x='Date', y=numeric_cols[0], title=f"Trend: {numeric_cols[0]}")
                st.sidebar.plotly_chart(fig, use_container_width=True)
            elif len(numeric_cols) >= 2:
                fig = px.scatter(df, x=numeric_cols[0], y=numeric_cols[1], title=f"{numeric_cols[0]} vs {numeric_cols[1]}")
                st.sidebar.plotly_chart(fig, use_container_width=True)
                
            st.sidebar.subheader("Local Tools Preview")
            # Run local tool pipelines based on detected context
            if 'sales' in uploaded_file.name.lower() or 'Revenue' in df.columns:
                from tools.sales_tools import process_sales_data
                st.sidebar.json(process_sales_data(data_path))
            elif 'inventory' in uploaded_file.name.lower() or 'Stock' in df.columns:
                from tools.inventory_tools import process_inventory_data
                st.sidebar.json(process_inventory_data(data_path))
            elif 'customer' in uploaded_file.name.lower() or 'Rating' in df.columns:
                from tools.customer_tools import process_customer_data
                st.sidebar.json(process_customer_data(data_path))
                
        except Exception as e:
            st.sidebar.error(f"Error parsing data: {e}")

# --- Main Chat Interface ---
st.header("Agentic Insights")

if 'messages' not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input("Ask your specialized agents (e.g., 'Why are we losing money?'):"):
    # Render user prompt
    st.chat_message("user").markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # Security: Prompt Injection Guard
    if detect_prompt_injection(prompt):
        warning = "🚨 Security Alert: Systemic jailbreak / prompt injection attempt detected. Request blocked."
        st.chat_message("assistant").error(warning)
        st.session_state.messages.append({"role": "assistant", "content": warning})
        
    # Security: Rate Limiting
    elif not st.session_state.rate_limiter.is_allowed(st.session_state.session_id):
        warning = "⏳ Rate Limit Exceeded: Maximum 5 requests per minute allowed. Please wait before asking again."
        st.chat_message("assistant").warning(warning)
        st.session_state.messages.append({"role": "assistant", "content": warning})
        
    else:
        # Proceed with Orchestration
        if not data_path:
            response = "Please upload a data file in the sidebar first so the agents have context."
            st.chat_message("assistant").info(response)
            st.session_state.messages.append({"role": "assistant", "content": response})
        else:
            with st.chat_message("assistant"):
                with st.spinner("Coordinator routing request to specialized agents..."):
                    try:
                        response = coordinator_agent.process_query(prompt, data_path)
                        st.markdown(response)
                        st.session_state.messages.append({"role": "assistant", "content": response})
                    except Exception as e:
                        error_msg = f"Agent Execution Error: {e}"
                        st.error(error_msg)
                        st.session_state.messages.append({"role": "assistant", "content": error_msg})
