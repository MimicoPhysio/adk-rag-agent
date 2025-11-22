import logging
import uuid
import os
import importlib
from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.responses import JSONResponse

# --- ADK Imports ---
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

# --- Robust Import for Memory Service ---
try:
    from google.adk.memory import VertexAiRagMemoryService
except ImportError:
    try:
        from google.adk.memory.vertex_ai_memory_bank_service import VertexAiMemoryBankService as VertexAiRagMemoryService
    except ImportError:
        # Fallback to check generic module structure if specific imports fail
        try:
            from google.adk.memory.vertex_ai import VertexAiMemoryService as VertexAiRagMemoryService
        except ImportError as e:
            print(f"CRITICAL: Could not find VertexAiMemoryService. Check google-adk[vertexai] installation.")
            raise e

# --- Internal Imports ---
from .agent import root_agent
from .services.audit_ledger import AuditLedger

# --- Logging Setup ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# --- CONFIGURATION ---
PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT")
LOCATION = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")
KEY_RING = "cloud-run-signer-keyring"
KEY_NAME = "adk-rag-agent-signer"
APP_NAME = "adk-rag-agent"  # Required by ADK Runner for telemetry

# --- SERVICE INITIALIZATION ---

# 1. Initialize Secure Audit Ledger (Resilient)
try:
    ledger = AuditLedger(
        project_id=PROJECT_ID,
        location=LOCATION,
        key_ring=KEY_RING,
        key_name=KEY_NAME
    )
    logger.info("✅ Secure Audit Ledger initialized.")
except Exception as e:
    logger.error(f"❌ Failed to initialize Audit Ledger (Check Credentials): {e}")
    ledger = None

# 2. Initialize Short-Term Memory (Session)
session_service = InMemorySessionService()

# 3. Initialize Long-Term Memory (Vertex AI RAG)
# FIXED: Using 'project' instead of 'project_id' to match library spec
try:
    logger.info(f"Initializing Vertex AI RAG Memory for project {PROJECT_ID}...")
    memory_service = VertexAiRagMemoryService(
        project=PROJECT_ID, 
        location=LOCATION
    )
    logger.info("✅ Vertex AI RAG Memory initialized.")
except Exception as e:
    logger.error(f"⚠️ Failed to initialize Long-Term Memory: {e}")
    memory_service = None

# 4. Initialize the ADK Runner
# FIXED: Added required 'app_name' argument
runner = Runner(
    agent=root_agent,
    session_service=session_service,
    memory_service=memory_service,
    app_name=APP_NAME
)

# --- ENDPOINTS ---

@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "status": "running", 
        "service": APP_NAME, 
        "memory_bank": "active" if memory_service else "disabled",
        "audit_ledger": "active" if ledger else "disabled"
    }

@app.post("/chat")
async def chat(request: Request, background_tasks: BackgroundTasks):
    """Primary Agent Endpoint."""
    try:
        body = await request.json()
        user_input = body.get("prompt") or body.get("message")
        session_id = body.get("session_id") or str(uuid.uuid4())
        user_id = body.get("user_id") or "default_user"
        
        if not user_input:
            return JSONResponse({"error": "No prompt provided"}, status_code=400)
        
        logger.info(f"▶️ Run | User: {user_id} | Session: {session_id}")

        if ledger:
            ledger.log_action(
                action="user_query_received",
                payload={"prompt": user_input, "session_id": session_id},
                user_id=user_id
            )
        
        user_msg = types.Content(role="user", parts=[types.Part.from_text(text=user_input)])
        final_response_text = ""
        
        async for event in runner.run_async(
            session_id=session_id, 
            user_id=user_id, 
            new_message=user_msg
        ):
            if hasattr(event, 'content') and event.content and event.source == "model":
                 for part in event.content.parts:
                     if part.text:
                         final_response_text += part.text

        if not final_response_text:
            final_response_text = "The agent processed the request but returned no text content."

        if ledger:
            ledger.log_action(
                action="agent_response_generated",
                payload={"response_preview": final_response_text[:200], "session_id": session_id},
                user_id=user_id
            )

        return {
            "response": final_response_text, 
            "agent_name": root_agent.name,
            "session_id": session_id,
            "user_id": user_id
        }

    except Exception as e:
        logger.error(f"❌ Agent Execution Error: {str(e)}")
        if ledger:
            ledger.log_action(action="agent_error", payload={"error": str(e)}, user_id=user_id)
        return JSONResponse({"error": str(e)}, status_code=500)
