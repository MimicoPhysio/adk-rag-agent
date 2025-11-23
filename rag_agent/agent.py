from google.adk.agents import Agent
from google.genai import types
from .tools.add_data import add_data
from .tools.create_corpus import create_corpus
from .tools.delete_corpus import delete_corpus
from .tools.delete_document import delete_document
from .tools.get_corpus_info import get_corpus_info
from .tools.list_corpora import list_corpora
from .tools.rag_query import rag_query

# Define the Agent with Gemini 3 Pro and Thinking Config
root_agent = Agent(
    name="RagAgent",
    # UPGRADE: Using Gemini 3 Pro Preview for advanced reasoning
    model="gemini-3-pro-preview",
    description="Vertex AI RAG Agent with Gemini 3 reasoning capabilities",
    
    # CONFIG: Enable Thinking (High/Dynamic is default for Pro)
    # Use types.ThinkingLevel.LOW for faster, less complex tasks.
    generate_content_config=types.GenerateContentConfig(
        thinking_config=types.ThinkingConfig(
            thinking_level=types.ThinkingLevel.HIGH
        )
    ),
    
    tools=[
        rag_query,
        list_corpora,
        create_corpus,
        add_data,
        get_corpus_info,
        delete_corpus,
        delete_document,
    ],
    instruction="""
# 🧠 Vertex AI RAG Agent (Gemini 3 Powered)
You are a helpful RAG agent that interacts with Vertex AI's document corpora.
You use Gemini 3's advanced reasoning to plan complex information retrieval tasks.

## Your Capabilities
1. **Query Documents**: Retrieve relevant information from document corpora.
2. **List/Manage Corpora**: Create, list, and delete corpora.
3. **Add Data**: Ingest documents from Google Drive or Storage.

## Reasoning Strategy
- When asked a complex question, use your thinking capability to plan the retrieval steps.
- Always verify you have the correct corpus name before querying.
- If a corpus doesn't exist, offer to create it.
"""
)
