import streamlit as st
import json
from datetime import datetime
import uuid
import asyncio
import websockets
from typing import Optional
import requests
import os
from dotenv import load_dotenv
from urllib.parse import urlencode, urlparse, parse_qsl, urlunparse
load_dotenv()



# Page configuration
st.set_page_config(
    page_title="AI Project Manager Agent",
    page_icon="🗂️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())


# WebSocket communication function
def send_websocket_message(websocket_url: str, message_payload: dict, timeout: int = 30, headers: dict | None = None) -> Optional[str]:
    """Send message via WebSocket and return response"""
    async def _send_message():
        try:
            # For maximum compatibility with different websockets versions we avoid
            # passing `extra_headers` to `connect` (some versions forward unexpected
            # kwargs to the event loop). If an API key is provided in headers, add it
            # as a query parameter instead.
            connect_url = websocket_url
            if headers and headers.get("x-api-key"):
                parsed = urlparse(websocket_url)
                qs = dict(parse_qsl(parsed.query))
                qs["api_key"] = headers.get("x-api-key")
                new_query = urlencode(qs)
                parsed = parsed._replace(query=new_query)
                connect_url = urlunparse(parsed)

            async with websockets.connect(connect_url) as websocket:
                # Send message
                await websocket.send(json.dumps(message_payload))
                
                # Wait for response with timeout
                response = await asyncio.wait_for(
                    websocket.recv(),
                    timeout=timeout
                )
                return response
        except Exception as e:
            raise e
    
    # Run the async function in a new event loop
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(_send_message())
    except Exception as e:
        raise e
    finally:
        loop.close()

# Configuration
WEBSOCKET_URL = st.sidebar.text_input(
    "WebSocket URL",
    value="ws://localhost:8000/ws/chat",
    help="Enter the WebSocket URL of your AI agent"
)

# API Key input (read from .env by default)
DEFAULT_API_KEY = os.getenv("API_KEY", "")
API_KEY = st.sidebar.text_input("API Key (x-api-key)", value=DEFAULT_API_KEY, help="Optional API key to send on websocket connections")

REQUEST_TIMEOUT = st.sidebar.slider(
    "Request Timeout (seconds)",
    min_value=5,
    max_value=120,
    value=30,
    help="How long to wait for agent response"
)

st.sidebar.markdown("---")
st.sidebar.markdown(f"**Session ID:** `{st.session_state.session_id[:8]}...`")
st.sidebar.markdown(f"**Messages:** {len(st.session_state.messages)}")

if st.sidebar.button("Clear Chat", type="secondary"):
    st.session_state.messages = []
    # Also clear the backend conversation
    clear_payload = {
        "session_id": st.session_state.session_id,
        "message": "/clear",
        "timestamp": datetime.now().isoformat(),
        "user_id": "streamlit_user",
        "message_type": "clear"
    }
    try:
        # Send clear command via WebSocket
        clear_headers = None
        if API_KEY:
            clear_headers = {"x-api-key": API_KEY}
        clear_response = send_websocket_message(WEBSOCKET_URL, clear_payload, REQUEST_TIMEOUT, headers=clear_headers)
        if clear_response:
            response_data = json.loads(clear_response)
            st.sidebar.success("Chat cleared on backend")
    except Exception as e:
        st.sidebar.warning(f"Failed to clear backend: {str(e)}")
    st.rerun()

# Main chat interface
st.title("🗂️ AI Project Manager Agent")
st.markdown("Manage your projects efficiently with your AI assistant!")
st.markdown("""
You can ask me to create, update, delete, or organize your projects and project tasks. Just tell me what you need!

**Examples:**
- "Create a new project for the website redesign"
- "List all milestones for my current projects"
- "Add a task to the marketing project: Prepare launch email"
- "Show me a summary of all ongoing projects"
- "Update the deadline for the client onboarding project"
""")

# Display chat messages
chat_container = st.container()
with chat_container:
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if "timestamp" in message:
                st.caption(f"_{message['timestamp']}_")

# Chat input
if prompt := st.chat_input("Type your message here..."):
    # Add user message to chat
    timestamp = datetime.now().strftime("%H:%M:%S")
    user_message = {
        "role": "user",
        "content": prompt,
        "timestamp": timestamp
    }
    st.session_state.messages.append(user_message)
    
    # Display user message immediately
    with st.chat_message("user"):
        st.markdown(prompt)
        st.caption(f"_{timestamp}_")
    
    # Prepare WebSocket message payload
    message_payload = {
        "session_id": st.session_state.session_id,
        "message": prompt,
        "timestamp": datetime.now().isoformat(),
        "user_id": "streamlit_user",
        "message_type": "chat"
    }
    
    # Show loading spinner and send WebSocket message
    with st.chat_message("assistant"):
        with st.spinner("Agent is thinking..."):
            try:
                # Send message via WebSocket
                extra_headers = None
                if API_KEY:
                    extra_headers = {"x-api-key": API_KEY}
                agent_response = send_websocket_message(WEBSOCKET_URL, message_payload, REQUEST_TIMEOUT, headers=extra_headers)
                
                if agent_response:
                    # Parse response
                    response_data = json.loads(agent_response)
                    agent_message = response_data.get("message", "No response from agent")
                    
                    # Display agent response
                    st.markdown(agent_message)
                    response_timestamp = datetime.now().strftime("%H:%M:%S")
                    st.caption(f"_{response_timestamp}_")
                    
                    # Add agent message to session state
                    assistant_message = {
                        "role": "assistant",
                        "content": agent_message,
                        "timestamp": response_timestamp
                    }
                    st.session_state.messages.append(assistant_message)
                    
                else:
                    error_msg = "No response received from agent"
                    st.error(error_msg)
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": error_msg,
                        "timestamp": datetime.now().strftime("%H:%M:%S")
                    })
                    
            except Exception as e:
                error_msg = f"WebSocket error: {str(e)}"
                st.error(error_msg)
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": error_msg,
                    "timestamp": datetime.now().strftime("%H:%M:%S")
                })
    
    # Rerun to update the chat display
    st.rerun()

# Footer
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: #666; font-size: 0.8em;'>
        AI Project Manager Agent | Built by <a href='https://tomshaw.dev' target='_blank' style='color: lightblue; text-decoration: underline;'>Tom Shaw</a>
    </div>
    """,
    unsafe_allow_html=True
)
