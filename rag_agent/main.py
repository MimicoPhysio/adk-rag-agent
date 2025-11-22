import logging
import uuid
import os
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

# Import the robust Runner and Memory Services
from google.adk.runners import Runner
from google.adk.services.session import InMemorySessionService
from google.adk.services.memory import VertexAiMemoryBankService
from google.genai import types
from .agent import root_agent

# Initialize logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# --- CONFIGURATION ---
PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT")
LOCATION = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")

# --- MEMORY ARCHITECTURE SETUP ---

# 1. Short-Term Memory (Session)
# Stores the immediate conversation context in RAM. Fast, but transient.
session_service = InMemorySessionService()

# 2. Long-Term Memory (Vertex AI Memory Bank)
# Persists facts and user details indefinitely using Vertex AI.
# Note: This requires the Vertex AI Agent Engine API to be enabled.
try:
    logger.info(f"Initializing Long-Term Memory for project {PROJECT_ID}...")
    memory_service = VertexAiMemoryBankService(
        project=PROJECT_ID, 
        location=LOCATION
    )
except Exception as e:
    logger.error(f"Failed to initialize Long-Term Memory: {e}")
    # Fallback: If Memory Bank fails (e.g., API not enabled), runs without it
    memory_service = None

# 3. Initialize the Runner
# The Runner orchestrates the Agent, Short-Term Memory, and Long-Term Memory
runner = Runner(
    agent=root_agent,
    session_service=session_service,
    memory_service=memory_service
)

@app.get("/")
async def root():
    """Health check endpoint."""
    memory_status = "active" if memory_service else "disabled"
    return {
        "status": "running", 
        "service": "adk-rag-agent", 
        "memory_bank": memory_status
    }

@app.post("/chat")
async def chat(request: Request):
    """Endpoint to interact with the real ADK agent."""
    try:
        body = await request.json()
        user_input = body.get("prompt") or body.get("message")
        # Use provided session_id or generate a new one for this request
        session_id = body.get("session_id") or str(uuid.uuid4())
        
        if not user_input:
            return JSONResponse({"error": "No prompt provided"}, status_code=400)
        
        logger.info(f"Starting agent run for session {session_id}: {user_input}")
        
        # Create the user message payload for ADK
        user_msg = types.Content(role="user", parts=[types.Part.from_text(text=user_input)])
        
        final_response_text = ""
        
        # Execute the Agent Loop
        # The Runner now automatically checks Long-Term Memory for context 
        # AND updates Short-Term session history.
        async for event in runner.run_async(session_id=session_id, new_message=user_msg):
            if hasattr(event, 'content') and event.content and event.source == "model":
                 for part in event.content.parts:
                     if part.text:
                         final_response_text += part.text

        if not final_response_text:
            final_response_text = "The agent processed the request but returned no text content."

        return {
            "response": final_response_text, 
            "agent_name": root_agent.name,
            "session_id": session_id
        }

    except Exception as e:
        logger.error(f"Agent Execution Error: {str(e)}")
        return JSONResponse({"error": str(e)}, status_code=500)
