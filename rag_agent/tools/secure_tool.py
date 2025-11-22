from google.cloud import secretmanager
from google.api_core.exceptions import PermissionDenied
import logging

# Configure logging
logger = logging.getLogger(__name__)

def get_runtime_secret(secret_id: str, project_id: str = "agentspace-notebookllm-ent") -> str:
    """
    Retrieves a secret from Secret Manager at RUNTIME.
    The agent never sees this logic or the credentials used to fetch it.
    """
    client = secretmanager.SecretManagerServiceClient()
    name = f"projects/{project_id}/secrets/{secret_id}/versions/latest"

    try:
        # Runtime Retrieval: This is where the Tool SA identity is used
        response = client.access_secret_version(request={"name": name})
        return response.payload.data.decode("UTF-8")
    except PermissionDenied:
        logger.error(f"SECURITY ALERT: Tool Service Account denied access to {secret_id}")
        raise PermissionError("Secure Tool: Authentication failed during runtime retrieval.")
    except Exception as e:
        logger.error(f"Runtime retrieval failed: {str(e)}")
        raise

def secure_tool_execution(session_id: str) -> dict:
    """
    The main entry point for the Secure Intermediary Pattern.
    1. Validates Session
    2. Retrieves Credentials (Runtime)
    3. Executes Logic
    4. Sanitizes Output
    """
    logger.info(f"Secure Tool invoked for session: {session_id}")
    
    # --- STEP 1: Security / Session Validation ---
    # (Logic to validate session_id would go here)
    if not session_id:
        return {"error": "Invalid Session ID"}

    # --- STEP 2: Runtime Secret Retrieval ---
    # The secret is fetched ONLY now, kept in memory briefly, and never logged
    try:
        api_key = get_runtime_secret("backend-api-key")
    except Exception as e:
        return {"error": "Security Intermediary failed to authenticate backend."}

    # --- STEP 3: Execute Logic using the Secret ---
    # Example: Calling an external API using the retrieved key
    # response = requests.get("https://api.example.com/data", headers={"Authorization": api_key})
    # For this architectural demo, we simulate the secure action:
    
    simulation_success = True if api_key else False

    # --- STEP 4: Sanitize Response ---
    # Ensure no secrets or raw data leak back to the Agent [cite: 439]
    sanitized_result = {
        "status": "success" if simulation_success else "failed",
        "message": "Secure operation completed via Intermediary.",
        "session_verified": True
    }

    return sanitized_result
