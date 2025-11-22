import logging
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from .agent import root_agent

# Initialize logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

@app.get("/")
async def root():
    """Health check endpoint for Cloud Run."""
    return {"status": "running", "service": "adk-rag-agent"}

@app.post("/chat")
async def chat(request: Request):
    """Endpoint to interact with the agent."""
    try:
        body = await request.json()
        user_input = body.get("prompt") or body.get("message")

        if not user_input:
            return JSONResponse({"error": "No prompt provided"}, status_code=400)

        logger.info(f"Received query: {user_input}")

        # TODO: Integrate actual agent execution here.
        # For now, we return a success message to prove the container works.
        return {"response": f"Agent received: {user_input}", "agent_name": root_agent.name}

    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return JSONResponse({"error": str(e)}, status_code=500)
