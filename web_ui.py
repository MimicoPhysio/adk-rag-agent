import streamlit as st
import requests
import google.auth
from google.auth.transport.requests import Request
from google.oauth2 import id_token
import os

# --- Configuration ---
# We try to get the URL from environment, or user can input it
DEFAULT_SERVICE_URL = os.environ.get("SERVICE_URL", "")

st.set_page_config(page_title="ADK RAG Agent", page_icon="🤖")
st.title("🔐 Secure ADK Agent Interface")

# --- Sidebar for Settings ---
with st.sidebar:
    st.header("Connection Settings")
    service_url = st.text_input("Cloud Run URL", value=DEFAULT_SERVICE_URL, placeholder="https://adk-rag-agent-...")
    st.info("This UI uses your local Google Credentials to authenticate requests.")

# --- Authentication Helper ---
def get_id_token(target_audience):
    """
    Generates a Google ID Token to authenticate with Cloud Run.
    This mimics the 'gcloud auth print-identity-token' command securely.
    """
    try:
        creds, _ = google.auth.default()
        auth_req = Request()
        token = id_token.fetch_id_token(auth_req, target_audience)
        return token
    except Exception as e:
        st.error(f"Authentication failed: {e}")
        return None

# --- Chat Interface ---
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Handle new input
if prompt := st.chat_input("Ask your secure agent something..."):
    
    if not service_url:
        st.error("Please enter your Cloud Run Service URL in the sidebar.")
        st.stop()

    # 1. Display User Message
    st.chat_message("user").markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    # 2. Authenticate & Call Agent
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        message_placeholder.markdown("Thinking...")
        
        try:
            # Get the secure ID token
            token = get_id_token(service_url)
            
            if token:
                headers = {
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json"
                }
                
                # Send request to your FastAPI /chat endpoint
                response = requests.post(
                    f"{service_url}/chat",
                    json={"prompt": prompt},
                    headers=headers
                )
                
                if response.status_code == 200:
                    data = response.json()
                    # Assuming your API returns {"response": "..."}
                    answer = data.get("response", str(data))
                    message_placeholder.markdown(answer)
                    st.session_state.messages.append({"role": "assistant", "content": answer})
                else:
                    error_msg = f"Error {response.status_code}: {response.text}"
                    message_placeholder.error(error_msg)
            
        except Exception as e:
            message_placeholder.error(f"Connection failed: {str(e)}")
